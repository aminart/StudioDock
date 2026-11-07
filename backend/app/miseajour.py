"""Mise à jour de Studio Dock lui-même, depuis le sous-dossier « StudioDock » du dossier partagé.

Windows : la nouvelle version est copiée à côté de l'exe ; l'exe en cours est renommé (Windows l'autorise),
la copie prend son nom, puis Studio Dock redémarre. L'ancien exe est supprimé au démarrage suivant.
Mac : la nouvelle version est signalée ; on l'installe en ouvrant le dossier partagé (glisser dans Applications).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from app import winapi
from app.catalogue import Catalogue
from app.info import EMPAQUETE, VERSION
from app.recherche import Trouvee, _cle_version, _est_installateur, _est_programme, _nom_sans_extension, _plus_recent

NOM = "StudioDock"


def version_disponible(catalogue: Catalogue, partage: Path | None) -> Trouvee | None:
    """Version de Studio Dock plus récente que celle-ci dans le partage, sinon None."""
    if partage is None:
        return None
    dossier = partage / catalogue.studiodock.source
    try:
        if not dossier.is_dir():
            return None
        fichiers = [f for f in dossier.iterdir()
                    if _nom_sans_extension(f).lower().replace(" ", "").startswith(NOM.lower())
                    and (_est_programme(f) or _est_installateur(f))]
    except OSError:
        return None
    trouvee = _plus_recent(fichiers)
    if trouvee and _cle_version(trouvee.version) > _cle_version(VERSION):
        return trouvee
    return None


def remplacement_possible() -> bool:
    return EMPAQUETE and winapi.IS_WIN


def nettoyer_ancienne_version() -> None:
    """Au démarrage : supprime l'exe remplacé lors de la dernière mise à jour."""
    if not remplacement_possible():
        return
    ancien = Path(sys.executable).with_name(f"{NOM}.old.exe")
    try:
        ancien.unlink(missing_ok=True)
    except OSError:
        pass


def appliquer(nouvelle: Trouvee, avant_redemarrage) -> None:
    """Remplace l'exe en cours par la nouvelle version et redémarre Studio Dock (Windows, exe empaqueté)."""
    if not remplacement_possible():
        raise RuntimeError("Mise à jour automatique disponible seulement pour StudioDock.exe sous Windows.")
    actuel = Path(sys.executable)
    copie = actuel.with_name(f"{NOM}.new.exe")
    ancien = actuel.with_name(f"{NOM}.old.exe")
    shutil.copyfile(nouvelle.chemin, copie)
    ancien.unlink(missing_ok=True)
    actuel.rename(ancien)
    try:
        copie.rename(actuel)
    except OSError:
        ancien.rename(actuel)  # retour à la version en cours
        raise

    def _redemarrer() -> None:
        avant_redemarrage()
        arguments = [a for a in sys.argv[1:] if a != "--after-update"]
        winapi.lancer_detache([str(actuel), "--after-update", *arguments], cwd=actuel.parent,
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os._exit(0)

    # Laisse la réponse partir vers l'interface avant de quitter
    threading.Timer(1.0, _redemarrer).start()
