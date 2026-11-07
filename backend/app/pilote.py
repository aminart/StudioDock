"""Lancer, suivre et arrêter les apps.

App web (contrat commun) : « <exe> --port N --no-browser », prête quand GET /health répond avec son identifiant ;
code de sortie 2 = port pris par une autre application. Arrêtée avec Studio Dock (groupe Windows + arrêt explicite).
App native : lancée hors du groupe, elle vit sa vie ; Studio Dock la détecte, la lance et l'affiche au premier plan.

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

from app import winapi
from app.catalogue import AppEntry
from app.info import logs_dir
from app.recherche import dossier_web, trouver_native, trouver_web

HOTE = "127.0.0.1"
DELAI_DEMARRAGE = 120  # secondes : premier lancement d'un exe empaqueté parfois lent (antivirus)
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

    # --- Suivi ---------------------------------------------------------------------------------------

    async def _sante(self, client: httpx.AsyncClient, port: int) -> dict[str, Any] | None:
        try:
            r = await client.get(f"http://{HOTE}:{port}/health")
            return r.json() if r.status_code == 200 else {}
        except (httpx.HTTPError, ValueError):
            return None

    async def etats(self, apps: list[AppEntry]) -> dict[str, dict[str, Any]]:
        async with httpx.AsyncClient(timeout=0.6) as client:
            sante = await asyncio.gather(*[
                self._sante(client, a.port) if a.kind == "web" else asyncio.sleep(0, None) for a in apps])
        processus = None
        if any(a.kind == "native" for a in apps):
            processus = await asyncio.to_thread(_processus_par_exe)
        return {a.id: await asyncio.to_thread(self._etat, a, s, processus) for a, s in zip(apps, sante)}

    def _etat(self, app: AppEntry, sante: dict | None, processus: dict | None) -> dict[str, Any]:
        if app.kind == "native":
            return self._etat_native(app, processus or {})
        return self._etat_web(app, sante)

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
                        self._erreurs[app.id] = ErreurAction(
                            "crashed", f"{app.name} s'est arrêtée (code {code})." + (f"\n{detail}" if detail else ""))
                lancement = None
            erreur = self._erreurs.get(app.id)

        if reconnue:
            self._erreurs.pop(app.id, None)
            version = sante.get("version") or base["version"]
            return {**base, "state": "on", "version": version, "external": lancement is None}
        if lancement:
            if time.monotonic() - lancement.debut < DELAI_DEMARRAGE:
                return {**base, "state": "starting"}
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
        else:
            self._lancer_web(app)

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
        journal = logs_dir() / f"{app.id}.log"
        journal.parent.mkdir(parents=True, exist_ok=True)
        with open(journal, "w", encoding="utf-8") as sortie:
            process = subprocess.Popen(
                _commande(trouvee.chemin) + ["--port", str(app.port), "--no-browser"],
                cwd=trouvee.chemin.parent, stdout=sortie, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                **winapi.options_processus())
        with self._verrou:
            self._lancements[app.id] = Lancement(process, journal=journal)

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
        trouvee = trouver_native(app)
        pids = _processus_par_exe().get(_nom_processus(app, trouvee), set())
        if not pids:
            raise ErreurAction("off", f"{app.name} n'est pas lancée.")
        if trouvee and trouvee.chemin.suffix == ".app":
            subprocess.Popen(["open", "-a", str(trouvee.chemin)])  # Mac : met l'app au premier plan
        else:
            winapi.premier_plan(pids)

    def effacer_erreur(self, app: AppEntry) -> None:
        self._erreurs.pop(app.id, None)

    def tout_arreter(self) -> None:
        """À la fermeture de Studio Dock : arrêt des apps web qu'il a lancées."""
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


def _pid_sur_port(port: int) -> int | None:
    try:
        for c in psutil.net_connections(kind="tcp"):
            if c.laddr and c.laddr.port == port and c.status == psutil.CONN_LISTEN and c.pid:
                return c.pid
    except (psutil.AccessDenied, PermissionError):
        return None
    return None
