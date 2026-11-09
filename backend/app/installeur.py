"""Installer, mettre à jour et retirer les apps à partir du dossier partagé de l'équipe (ou, avec un catalogue
en ligne, à partir du fichier téléchargé par le navigateur).

Les apps ne sont jamais lancées depuis le partage : leur programme est copié dans le dossier de Studio Dock
(apps/<id>/), sur le poste de chacun. Une mise à jour arrête l'app si elle tourne, copie la nouvelle version,
puis supprime l'ancienne. Les apps natives sont installées par leur propre installateur, copié puis lancé.
"""
from __future__ import annotations

import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app import winapi
from app.catalogue import AppEntry
from app.info import home_dir
from app.pilote import Pilote
from app.recherche import _candidats, plus_recente, trouver_dans_partage, trouver_native, trouver_web

BLOC = 1024 * 1024


@dataclass
class Copie:
    progres: int = 0  # pourcentage
    erreur: str | None = None
    fini: bool = False


def _copier(source: Path, cible: Path, suivi: Copie) -> None:
    """Copie par blocs (progression visible), sous un nom temporaire, puis renommage : jamais de fichier à moitié copié."""
    cible.parent.mkdir(parents=True, exist_ok=True)
    temporaire = cible.with_name(cible.name + ".part")
    total = max(source.stat().st_size, 1)
    fait = 0
    with open(source, "rb") as entree, open(temporaire, "wb") as sortie:
        while bloc := entree.read(BLOC):
            sortie.write(bloc)
            fait += len(bloc)
            suivi.progres = min(99, int(fait * 100 / total))
    if fait != source.stat().st_size:  # fichier encore en cours d'écriture pendant la copie
        temporaire.unlink(missing_ok=True)
        raise OSError("le fichier a changé pendant la copie (encore en cours de téléchargement ?). Réessayez.")
    shutil.copystat(source, temporaire)
    temporaire.replace(cible)


class Installeur:
    def __init__(self, pilote: Pilote) -> None:
        self.pilote = pilote
        self._verrou = threading.Lock()
        self.copies: dict[str, Copie] = {}

    def en_cours(self, app_id: str) -> Copie | None:
        copie = self.copies.get(app_id)
        if copie and copie.fini and not copie.erreur:
            self.copies.pop(app_id, None)
            return None
        return copie

    def oublier_erreur(self, app_id: str) -> None:
        copie = self.copies.get(app_id)
        if copie and copie.erreur:
            self.copies.pop(app_id, None)

    def installer(self, app: AppEntry, partage: Path | None) -> None:
        """Installe ou met à jour (même opération : copie de la dernière version du partage)."""
        disponible = trouver_dans_partage(app, partage)
        if disponible is None:
            raise FileNotFoundError(f"Aucune version de {app.name} dans le dossier partagé.")
        with self._verrou:
            actuelle = self.copies.get(app.id)
            if actuelle and not actuelle.fini:
                return
            suivi = self.copies[app.id] = Copie()
        threading.Thread(target=self._travail, args=(app, disponible.chemin, suivi), daemon=True).start()

    def signaler(self, app: AppEntry, erreur: str) -> None:
        """Erreur affichée sur la carte de l'app (par exemple : téléchargement incomplet)."""
        with self._verrou:
            self.copies[app.id] = Copie(erreur=erreur, fini=True)

    def installer_fichier(self, app: AppEntry, source: Path, nom: str, apres: Callable[[], None]) -> bool:
        """Catalogue en ligne : installe le fichier arrivé dans Téléchargements, sous le nom `nom`, puis appelle
        `apres` (qui le retire des Téléchargements). False si une copie de cette app est déjà en cours."""
        with self._verrou:
            actuelle = self.copies.get(app.id)
            if actuelle and not actuelle.fini:
                return False
            suivi = self.copies[app.id] = Copie()
        threading.Thread(target=self._travail, args=(app, source, suivi, nom, apres, "Téléchargements"),
                         daemon=True).start()
        return True

    def _travail(self, app: AppEntry, source: Path, suivi: Copie, nom: str | None = None,
                 apres: Callable[[], None] | None = None, origine: str = "le dossier partagé") -> None:
        try:
            if app.kind == "web":
                self._installer_web(app, source, suivi, nom)
            else:
                self._installer_native(app, source, suivi, nom)
            suivi.progres = 100
            if apres:
                apres()
        except OSError as e:
            suivi.erreur = f"Copie depuis {origine} impossible : {e}"
        finally:
            suivi.fini = True

    def _installer_web(self, app: AppEntry, source: Path, suivi: Copie, nom: str | None = None) -> None:
        dossier = home_dir() / "apps" / app.id
        cible = dossier / (nom or source.name)
        # Une app lancée verrouille son programme (Windows) : on l'arrête avant de la remplacer
        if self.pilote.est_lancee(app):
            self.pilote.arreter(app)
        _copier(source, cible, suivi)
        winapi.autoriser_programme(cible)
        for ancien in _candidats(dossier, app.exe):
            if ancien != cible:
                try:
                    ancien.unlink()
                except OSError:
                    pass  # encore utilisé : sera retenté à la prochaine mise à jour

    def _installer_native(self, app: AppEntry, source: Path, suivi: Copie, nom: str | None = None) -> None:
        cible = home_dir() / "installateurs" / (nom or source.name)
        _copier(source, cible, suivi)
        if cible.suffix.lower() == ".msi":
            winapi.lancer_detache(["msiexec", "/i", str(cible)])
        elif cible.suffix.lower() in (".dmg", ".pkg", ".zip"):
            subprocess.Popen(["open", str(cible)])  # Mac : l'utilisateur glisse l'app dans Applications
        else:
            winapi.lancer_detache([str(cible)], cwd=cible.parent)

    def retirer(self, app: AppEntry) -> None:
        if app.kind != "web":
            raise ValueError(f"{app.name} se désinstalle depuis les réglages du système.")
        if self.pilote.est_lancee(app):
            self.pilote.arreter(app)
        shutil.rmtree(home_dir() / "apps" / app.id, ignore_errors=True)

    def installer_les_apps_imposees(self, apps: list[AppEntry], partage: Path | None) -> None:
        """Apps « auto » du catalogue : installées d'office dès que le partage est accessible, et mises à jour
        d'office quand elles ne sont pas lancées (sinon le bandeau « Mettre à jour » s'affiche)."""
        for app in apps:
            if app.mode != "auto" or app.kind != "web" or self.copies.get(app.id):
                continue
            disponible = trouver_dans_partage(app, partage)
            if disponible is None:
                continue
            locale = trouver_web(app)
            a_jour = locale is not None and not plus_recente(disponible.version, locale.version)
            if a_jour or (locale is not None and self.pilote.est_lancee(app)):
                continue
            try:
                self.installer(app, partage)
            except FileNotFoundError:
                pass


def installee(app: AppEntry) -> tuple[bool, str | None]:
    trouvee = trouver_web(app) if app.kind == "web" else trouver_native(app)
    return trouvee is not None, trouvee.version if trouvee else None
