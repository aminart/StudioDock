"""Lancer, suivre et arrêter les apps.

App web (contrat commun) : « <exe> --port N --no-browser », prête quand GET /health répond avec son identifiant ;
code de sortie 2 = port pris par une autre application. Arrêtée avec Studio Dock (groupe Windows + arrêt explicite).
App native : lancée hors du groupe, elle vit sa vie ; Studio Dock la détecte, la lance et l'affiche au premier plan.
App web externe (exe d'un tiers qui s'ouvre sur localhost, sans le contrat) : lancée telle quelle dans le groupe,
comme une app web ; son adresse est fixée dans le catalogue ou, à défaut, détectée sur le port qu'écoute son
processus. Prête dès que l'adresse répond, quelle que soit la réponse (pas de /health).

États renvoyés à l'interface : missing (introuvable), off, starting, on, error (avec un code et un message).
"""
from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import psutil

from app import journal as journal_dock, winapi
from app.catalogue import AppEntry
from app.info import logs_dir
from app.recherche import dossier_web, trouver_native, trouver_web

HOTE = "127.0.0.1"
DELAI_DEMARRAGE = 120  # secondes : premier lancement d'un exe empaqueté parfois lent (antivirus)
DELAI_SANTE = 2.0  # secondes : une app occupée (génération, analyse) peut répondre lentement à /health
DELAI_NATIVE = 15


class ErreurAction(Exception):
    """Action impossible : message lisible renvoyé à l'interface."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Lancement:
    process: subprocess.Popen
    debut: float = field(default_factory=time.monotonic)
    journal: Path | None = None
    arret_demande: bool = False
    prete: bool = False  # a répondu au moins une fois : le délai de démarrage ne la concerne plus
    port: int | None = None  # app web externe sans adresse fixe : port détecté sur son processus


def port_occupe(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((HOTE, port)) == 0


def _commande(chemin: Path) -> list[str]:
    if chemin.suffix.lower() == ".py":
        return [sys.executable, str(chemin)]
    return [str(chemin)]


def _arreter_arbre(pid: int) -> None:
    """Arrête un processus et ses enfants (un exe PyInstaller est un lanceur plus un processus enfant)."""
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    processus = parent.children(recursive=True) + [parent]
    for p in processus:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            pass
    _, vivants = psutil.wait_procs(processus, timeout=5)
    for p in vivants:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass


def _duree(secondes: float) -> str:
    minutes = int(secondes // 60)
    return f"{minutes // 60} h {minutes % 60:02d}" if minutes >= 60 else f"{minutes} min"


def _fin_du_journal(chemin: Path | None, lignes: int = 6) -> str:
    if not chemin:
        return ""
    try:
        texte = chemin.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    except OSError:
        return ""
    return "\n".join(texte[-lignes:])


class Pilote:
    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._lancements: dict[str, Lancement] = {}
        self._erreurs: dict[str, ErreurAction] = {}
        self._natives_demarrees: dict[str, float] = {}
        self._ports_detectes: dict[str, int] = {}  # app web externe : dernier port détecté (Ouvrir, arrêt)

    # --- Suivi ---------------------------------------------------------------------------------------

    async def _sante(self, client: httpx.AsyncClient, port: int) -> dict[str, Any] | None:
        try:
            r = await client.get(f"http://{HOTE}:{port}/health")
            return r.json() if r.status_code == 200 else {}
        except (httpx.HTTPError, ValueError):
            return None

    async def etats(self, apps: list[AppEntry]) -> dict[str, dict[str, Any]]:
        async with httpx.AsyncClient(timeout=DELAI_SANTE) as client:
            sante = await asyncio.gather(*[
                self._sante(client, a.port) if a.kind == "web" else asyncio.sleep(0, None) for a in apps])
        processus = None
        if any(a.kind == "native" for a in apps):
            processus = await asyncio.to_thread(_processus_par_exe)
        return {a.id: await asyncio.to_thread(self._etat, a, s, processus) for a, s in zip(apps, sante)}

    def _etat(self, app: AppEntry, sante: dict | None, processus: dict | None) -> dict[str, Any]:
        if app.kind == "native":
            return self._etat_native(app, processus or {})
        if app.kind == "external":
            return self._etat_externe(app)
        return self._etat_web(app, sante)

    # --- App web externe -----------------------------------------------------------------------------

    def _adresse(self, app: AppEntry, lancement: Lancement | None = None) -> str | None:
        """Adresse de l'app web externe : celle du catalogue, sinon celle du port détecté."""
        if app.address:
            return app.address
        if lancement is None:
            with self._verrou:
                lancement = self._lancements.get(app.id)
        port = (lancement.port if lancement else None) or self._ports_detectes.get(app.id)
        return f"http://localhost:{port}/" if port else None

    def _detecter_port(self, lancement: Lancement) -> int | None:
        """Premier port de ce poste qui répond en HTTP parmi ceux qu'écoutent le processus et ses enfants."""
        for port in _ports_ecoutes(lancement.process.pid):
            if _repond(f"http://{HOTE}:{port}/"):
                return port
        return None

    def _etat_externe(self, app: AppEntry) -> dict[str, Any]:
        trouvee = trouver_web(app)
        with self._verrou:
            lancement = self._lancements.get(app.id)
            if lancement and lancement.process.poll() is not None:
                code = lancement.process.returncode
                del self._lancements[app.id]
                if not lancement.arret_demande and code not in (0, None):
                    detail = _fin_du_journal(lancement.journal)
                    journal_dock.noter(f"{app.name} s'est arrêtée seule (code {code}) après "
                                       f"{_duree(time.monotonic() - lancement.debut)}. Fin de son journal :\n{detail}")
                    self._erreurs[app.id] = ErreurAction(
                        "crashed", f"{app.name} s'est arrêtée (code {code})." + (f"\n{detail}" if detail else ""))
                lancement = None
            erreur = self._erreurs.get(app.id)
        if lancement and not app.address and not lancement.port:
            lancement.port = self._detecter_port(lancement)
            if lancement.port:
                self._ports_detectes[app.id] = lancement.port
                journal_dock.noter(f"{app.name} : port {lancement.port} détecté.")
        adresse = self._adresse(app, lancement)
        base = {"location": str(trouvee.chemin) if trouvee else None, "folder": str(dossier_web(app)),
                "version": trouvee.version if trouvee else None, "url": adresse, "external": False, "error": None}
        repond = bool(adresse) and _repond(adresse)
        if repond and (lancement or app.address):
            # Lancée par Studio Dock, ou à côté quand l'adresse est fixée (un port détecté peut avoir été repris)
            self._erreurs.pop(app.id, None)
            if lancement:
                lancement.prete = True
            return {**base, "state": "on", "external": lancement is None}
        if lancement:
            if lancement.prete:
                return {**base, "state": "on", "busy": True}
            if time.monotonic() - lancement.debut < DELAI_DEMARRAGE:
                return {**base, "state": "starting"}
            journal_dock.noter(f"{app.name} n'a ouvert aucune adresse dans les {DELAI_DEMARRAGE} s après son lancement : arrêtée.")
            self._erreurs[app.id] = ErreurAction(
                "timeout", f"{app.name} ne répond sur aucune adresse après {DELAI_DEMARRAGE} secondes. "
                           "Si elle s'ouvre sur une adresse précise, indiquez-la dans sa fiche du catalogue.")
            self._arreter_lancement(app.id)
            erreur = self._erreurs[app.id]
        if erreur:
            return {**base, "state": "error", "error": {"code": erreur.code, "message": erreur.message}}
        if not trouvee:
            return {**base, "state": "missing"}
        return {**base, "state": "off"}

    def _etat_web(self, app: AppEntry, sante: dict | None) -> dict[str, Any]:
        trouvee = trouver_web(app)
        base = {"location": str(trouvee.chemin) if trouvee else None, "folder": str(dossier_web(app)),
                "version": trouvee.version if trouvee else None, "url": f"http://{HOTE}:{app.port}",
                "external": False, "error": None}
        reconnue = bool(sante) and sante.get("app") in (None, app.id) and "status" in sante
        with self._verrou:
            lancement = self._lancements.get(app.id)
            if lancement and lancement.process.poll() is not None:
                code = lancement.process.returncode
                del self._lancements[app.id]
                if not lancement.arret_demande and code not in (0, None):
                    if code == 2:
                        self._erreurs[app.id] = ErreurAction(
                            "port_busy", f"Le port {app.port} est utilisé par une autre application.")
                    else:
                        detail = _fin_du_journal(lancement.journal)
                        journal_dock.noter(f"{app.name} s'est arrêtée seule (code {code}) après "
                                           f"{_duree(time.monotonic() - lancement.debut)}. Fin de son journal :\n{detail}")
                        self._erreurs[app.id] = ErreurAction(
                            "crashed", f"{app.name} s'est arrêtée (code {code})." + (f"\n{detail}" if detail else ""))
                lancement = None
            erreur = self._erreurs.get(app.id)

        if reconnue:
            self._erreurs.pop(app.id, None)
            if lancement:
                lancement.prete = True
            version = sante.get("version") or base["version"]
            return {**base, "state": "on", "version": version, "external": lancement is None}
        if lancement:
            if lancement.prete:
                # Démarrée et toujours en vie, mais trop occupée pour répondre à /health (longue génération,
                # gros document) : elle tourne, on ne l'arrête surtout pas
                return {**base, "state": "on", "busy": True}
            if time.monotonic() - lancement.debut < DELAI_DEMARRAGE:
                return {**base, "state": "starting"}
            journal_dock.noter(f"{app.name} n'a jamais répondu dans les {DELAI_DEMARRAGE} s après son lancement : arrêtée.")
            self._erreurs[app.id] = ErreurAction(
                "timeout", f"{app.name} ne répond pas après {DELAI_DEMARRAGE} secondes.")
            self._arreter_lancement(app.id)
            erreur = self._erreurs[app.id]
        if erreur:
            return {**base, "state": "error", "error": {"code": erreur.code, "message": erreur.message}}
        if not trouvee:
            return {**base, "state": "missing"}
        return {**base, "state": "off"}

    def _etat_native(self, app: AppEntry, processus: dict[str, set[int]]) -> dict[str, Any]:
        trouvee = trouver_native(app)
        pids = processus.get(_nom_processus(app, trouvee), set())
        base = {"location": str(trouvee.chemin) if trouvee else None,
                "folder": str(trouvee.chemin.parent) if trouvee else None,
                "version": trouvee.version if trouvee else None, "url": None, "external": False, "error": None}
        if pids:
            self._natives_demarrees.pop(app.id, None)
            return {**base, "state": "on"}
        debut = self._natives_demarrees.get(app.id)
        if debut and time.monotonic() - debut < DELAI_NATIVE:
            return {**base, "state": "starting"}
        self._natives_demarrees.pop(app.id, None)
        if not trouvee:
            return {**base, "state": "missing"}
        return {**base, "state": "off"}

    # --- Actions -------------------------------------------------------------------------------------

    def lancer(self, app: AppEntry) -> None:
        if app.kind == "native":
            self._lancer_native(app)
        elif app.kind == "external":
            self._lancer_externe(app)
        else:
            self._lancer_web(app)

    def _ouvrir_journal(self, app: AppEntry) -> Path:
        journal = logs_dir() / f"{app.id}.log"
        journal.parent.mkdir(parents=True, exist_ok=True)
        # Le journal du lancement précédent est gardé : il explique un arrêt imprévu après la relance
        try:
            if journal.is_file() and journal.stat().st_size:
                journal.replace(journal.with_name(f"{app.id}.precedent.log"))
        except OSError:
            pass
        return journal

    def _lancer_externe(self, app: AppEntry) -> None:
        """Exe lancé tel quel (il ouvre souvent lui-même le navigateur), dans le groupe : il s'arrête avec Studio Dock."""
        with self._verrou:
            lancement = self._lancements.get(app.id)
            if lancement and lancement.process.poll() is None:
                return
        trouvee = trouver_web(app)
        if not trouvee:
            raise ErreurAction("missing", f"{app.exe}.exe introuvable : déposez-le dans {dossier_web(app)}.")
        if app.port and port_occupe(app.port):
            if _repond(app.address):
                return  # déjà ouverte, lancée à côté de Studio Dock
            erreur = ErreurAction("port_busy", f"Le port {app.port} est utilisé par une autre application.")
            self._erreurs[app.id] = erreur
            raise erreur
        self._erreurs.pop(app.id, None)
        winapi.autoriser_programme(trouvee.chemin)
        journal = self._ouvrir_journal(app)
        with open(journal, "w", encoding="utf-8") as sortie:
            process = subprocess.Popen(
                _commande(trouvee.chemin), cwd=trouvee.chemin.parent, stdout=sortie, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, **winapi.options_processus())
        with self._verrou:
            self._lancements[app.id] = Lancement(process, journal=journal)
        self._ports_detectes.pop(app.id, None)
        journal_dock.noter(f"{app.name} {trouvee.version or ''} lancée (app web externe, "
                           f"{app.address or 'adresse à détecter'}, processus {process.pid}).")

    def _lancer_web(self, app: AppEntry) -> None:
        with self._verrou:
            lancement = self._lancements.get(app.id)
            if lancement and lancement.process.poll() is None:
                return  # déjà en cours de démarrage ou lancée
        trouvee = trouver_web(app)
        if not trouvee:
            raise ErreurAction("missing", f"{app.exe}.exe introuvable : déposez-le dans {dossier_web(app)}.")
        if port_occupe(app.port):
            # Déjà lancée hors de Studio Dock ? Sinon, une autre application tient le port.
            try:
                sante = httpx.get(f"http://{HOTE}:{app.port}/health", timeout=1).json()
                if sante.get("app") in (None, app.id) and "status" in sante:
                    return
            except (httpx.HTTPError, ValueError):
                pass
            erreur = ErreurAction("port_busy", f"Le port {app.port} est utilisé par une autre application.")
            self._erreurs[app.id] = erreur
            raise erreur
        self._erreurs.pop(app.id, None)
        winapi.autoriser_programme(trouvee.chemin)
        journal = self._ouvrir_journal(app)
        with open(journal, "w", encoding="utf-8") as sortie:
            process = subprocess.Popen(
                _commande(trouvee.chemin) + ["--port", str(app.port), "--no-browser"],
                cwd=trouvee.chemin.parent, stdout=sortie, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                **winapi.options_processus())
        with self._verrou:
            self._lancements[app.id] = Lancement(process, journal=journal)
        journal_dock.noter(f"{app.name} {trouvee.version or ''} lancée (port {app.port}, processus {process.pid}).")

    def _lancer_native(self, app: AppEntry) -> None:
        trouvee = trouver_native(app)
        if not trouvee:
            raise ErreurAction("missing", f"{app.name} n'est pas installée sur ce poste.")
        if trouvee.chemin.suffix == ".app":  # Mac : ouverture comme depuis le Finder
            subprocess.Popen(["open", "-a", str(trouvee.chemin)])
        else:
            winapi.lancer_detache(_commande(trouvee.chemin), cwd=trouvee.chemin.parent,
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._natives_demarrees[app.id] = time.monotonic()

    def _arreter_lancement(self, app_id: str) -> bool:
        with self._verrou:
            lancement = self._lancements.pop(app_id, None)
        if not lancement:
            return False
        lancement.arret_demande = True
        _arreter_arbre(lancement.process.pid)
        return True

    def arreter(self, app: AppEntry) -> None:
        if app.kind == "native":
            raise ErreurAction("unsupported", f"Fermez {app.name} depuis sa propre fenêtre.")
        self._erreurs.pop(app.id, None)
        if self._arreter_lancement(app.id):
            return
        if app.kind == "external":
            # Lancée à côté de Studio Dock : seulement si le programme qui tient l'adresse est bien le sien
            pid = _pid_sur_port(app.port) if app.port else None
            if pid and _nom_du_processus(pid) == _nom_processus(app, trouver_web(app)):
                _arreter_arbre(pid)
            return
        # Lancée hors de Studio Dock : processus qui écoute sur le port, après vérification de /health
        try:
            sante = httpx.get(f"http://{HOTE}:{app.port}/health", timeout=1).json()
        except (httpx.HTTPError, ValueError):
            return
        if sante.get("app") not in (None, app.id):
            raise ErreurAction("port_busy", f"Le port {app.port} est tenu par une autre application.")
        if pid := _pid_sur_port(app.port):
            _arreter_arbre(pid)

    def ouvrir(self, app: AppEntry) -> None:
        if app.kind == "web":
            winapi.ouvrir(f"http://{HOTE}:{app.port}")
            return
        if app.kind == "external":
            adresse = self._adresse(app)
            if not adresse:
                raise ErreurAction("off", f"{app.name} n'a pas encore ouvert son adresse : patientez quelques secondes.")
            winapi.ouvrir(adresse)
            return
        trouvee = trouver_native(app)
        pids = _processus_par_exe().get(_nom_processus(app, trouvee), set())
        if not pids:
            raise ErreurAction("off", f"{app.name} n'est pas lancée.")
        if trouvee and trouvee.chemin.suffix == ".app":
            subprocess.Popen(["open", "-a", str(trouvee.chemin)])  # Mac : met l'app au premier plan
        else:
            winapi.premier_plan(pids)

    def est_lancee(self, app: AppEntry) -> bool:
        """App web lancée (par Studio Dock ou à côté) ; app native en cours d'exécution."""
        if app.kind == "native":
            trouvee = trouver_native(app)
            return bool(_processus_par_exe().get(_nom_processus(app, trouvee)))
        if app.kind == "external":
            lancement = self._lancements.get(app.id)
            if lancement and lancement.process.poll() is None:
                return True
            return bool(app.address) and _repond(app.address)
        lancement = self._lancements.get(app.id)
        if lancement and lancement.process.poll() is None:
            return True
        try:
            sante = httpx.get(f"http://{HOTE}:{app.port}/health", timeout=0.6).json()
            return sante.get("app") in (None, app.id) and "status" in sante
        except (httpx.HTTPError, ValueError):
            return False

    def effacer_erreur(self, app: AppEntry) -> None:
        self._erreurs.pop(app.id, None)

    def apps_ouvertes(self) -> list[str]:
        """Apps web (de la suite ou externes) lancées par Studio Dock et toujours en route : elles s'arrêtent avec lui."""
        return [app_id for app_id, l in list(self._lancements.items()) if l.process.poll() is None]

    def tout_arreter(self) -> None:
        """À la fermeture de Studio Dock : arrêt des apps web qu'il a lancées."""
        if self._lancements:
            journal_dock.noter(f"Arrêtées avec Studio Dock : {', '.join(self._lancements)}.")
        for app_id in list(self._lancements):
            self._arreter_lancement(app_id)


def _nom_processus(app: AppEntry, trouvee) -> str:
    if trouvee and trouvee.processus:
        return trouvee.processus.lower()
    return (app.exe + (".exe" if winapi.IS_WIN else "")).lower()


def _processus_par_exe() -> dict[str, set[int]]:
    resultat: dict[str, set[int]] = {}
    for p in psutil.process_iter(["name", "pid"]):
        nom = (p.info.get("name") or "").lower()
        if nom:
            resultat.setdefault(nom, set()).add(p.info["pid"])
    return resultat


def _repond(adresse: str | None) -> bool:
    """Une adresse répond en HTTP, quelle que soit la réponse (une app externe n'a pas de /health)."""
    if not adresse:
        return False
    try:
        httpx.get(adresse, timeout=DELAI_SANTE, follow_redirects=False)
        return True
    except httpx.HTTPError:
        return False


def _ports_ecoutes(pid: int) -> list[int]:
    """Ports TCP qu'écoutent un processus et ses enfants, sur ce poste."""
    try:
        parent = psutil.Process(pid)
        processus = [parent] + parent.children(recursive=True)
    except psutil.Error:
        return []
    ports: set[int] = set()
    for p in processus:
        try:
            connexions = p.net_connections(kind="tcp") if hasattr(p, "net_connections") else p.connections(kind="tcp")
        except psutil.Error:
            continue
        for c in connexions:
            if c.status == psutil.CONN_LISTEN and c.laddr and c.laddr.ip in ("127.0.0.1", "0.0.0.0", "::", "::1"):
                ports.add(c.laddr.port)
    return sorted(ports)


def _nom_du_processus(pid: int) -> str:
    try:
        return psutil.Process(pid).name().lower()
    except psutil.Error:
        return ""


def _pid_sur_port(port: int) -> int | None:
    try:
        for c in psutil.net_connections(kind="tcp"):
            if c.laddr and c.laddr.port == port and c.status == psutil.CONN_LISTEN and c.pid:
                return c.pid
    except (psutil.AccessDenied, PermissionError):
        return None
    return None
