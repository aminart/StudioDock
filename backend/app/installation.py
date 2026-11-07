"""Installation de Studio Dock sur le poste (Windows) : dans le dossier choisi par chaque membre de l'équipe.

Le dossier partagé sert seulement de dépôt ; Studio Dock et les apps sont copiés et lancés depuis le dossier
d'installation de la personne (contrainte de l'entreprise : un programme lancé ailleurs est refusé).

Premier lancement (exe ouvert depuis le partage ou les Téléchargements) : la personne choisit son dossier,
Studio Dock s'y copie, crée un raccourci dans le menu Démarrer et redémarre depuis ce dossier.
Changement de dossier : Studio Dock et les apps installées sont copiés dans le nouveau dossier, Studio Dock
redémarre depuis celui-ci, puis l'ancien dossier est vidé de ce que Studio Dock y avait mis.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

from app import reglages, winapi
from app.info import EMPAQUETE, dossier_installation_choisi, exe_dir

EXE = "StudioDock.exe"
# Ce que Studio Dock range dans son dossier d'installation : seul ceci est déplacé puis effacé
CONTENU = ["apps", "installateurs", "cache", "catalogue.cache.json", "apps.json", "studiodock.config.json"]
EXES = [EXE, "StudioDock.old.exe", "StudioDock.new.exe"]
RACCOURCI = "Studio Dock.lnk"


class ErreurInstallation(Exception):
    pass


def disponible() -> bool:
    """Le choix du dossier d'installation concerne l'exe Windows (le Mac range l'app dans Applications),
    sauf avec --home, qui impose le dossier (tests, usage portable)."""
    return EMPAQUETE and winapi.IS_WIN and not os.environ.get("STUDIODOCK_HOME", "").strip()


def dossier_propose() -> Path:
    """Dossier proposé : celui préparé par l'administratrice (install_folder), sinon un dossier personnel."""
    if propose := reglages.developper(reglages.preset().get("install_folder")):
        return propose
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "Programs" / "StudioDock"


def est_installe() -> bool:
    """Studio Dock tourne depuis le dossier d'installation choisi."""
    choisi = dossier_installation_choisi()
    actuel = exe_dir()
    return choisi is not None and actuel is not None and meme(choisi, actuel)


def a_installer() -> bool:
    """Exe Windows lancé hors de son dossier d'installation : il faut d'abord l'installer."""
    return disponible() and not est_installe()


def copie_installee() -> Path | None:
    """Exe installé dans le dossier choisi, s'il existe."""
    choisi = dossier_installation_choisi()
    if choisi is None:
        return None
    exe = choisi / EXE
    return exe if exe.is_file() else None


def meme(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return os.path.normcase(str(a)) == os.path.normcase(str(b))


def dedans(enfant: Path, parent: Path) -> bool:
    try:
        enfant, parent = enfant.resolve(), parent.resolve()
    except OSError:
        return False
    return enfant == parent or parent in enfant.parents


def verifier(dossier: Path, partage: Path | None) -> None:
    """Refuse un dossier réseau ou situé dans le dossier partagé de l'équipe."""
    texte = str(dossier)
    if not dossier.is_absolute():
        raise ErreurInstallation("Indiquez un chemin complet, par exemple C:\\Users\\vous\\Apps\\StudioDock.")
    if texte.startswith(("\\\\", "//")):
        raise ErreurInstallation("Choisissez un dossier de ce poste, pas un dossier réseau : "
                                 "les applications doivent être installées et lancées en local.")
    if partage is not None and dedans(dossier, partage):
        raise ErreurInstallation("Ce dossier est dans le dossier partagé de l'équipe : choisissez un dossier "
                                 "de ce poste, où vous seul installez vos applications.")
    if dossier.exists() and not dossier.is_dir():
        raise ErreurInstallation("Ce chemin désigne un fichier, pas un dossier.")


def installer(dossier: Path, exe: Path, ancien: Path | None) -> Path:
    """Copie Studio Dock (et, depuis un ancien dossier d'installation, ses apps) dans `dossier`.

    Retourne le chemin du nouvel exe. Ne supprime rien : l'ancien dossier est vidé après le redémarrage.
    """
    try:
        dossier.mkdir(parents=True, exist_ok=True)
        cible = dossier / EXE
        if not meme(exe, cible):
            temporaire = dossier / "StudioDock.new.exe"
            shutil.copyfile(exe, temporaire)
            os.replace(temporaire, cible)
        if ancien is not None and ancien.is_dir() and not meme(ancien, dossier):
            for nom in CONTENU:
                source = ancien / nom
                if source.is_dir():
                    shutil.copytree(source, dossier / nom, dirs_exist_ok=True)
                elif source.is_file():
                    shutil.copyfile(source, dossier / nom)
    except OSError as e:
        raise ErreurInstallation(f"Copie impossible dans {dossier} : {e.strerror or e}") from e
    return cible


def nettoyer(ancien: Path, nouveau: Path) -> None:
    """Après un changement de dossier : efface de l'ancien dossier ce que Studio Dock y avait mis,
    puis le dossier lui-même s'il est vide. Jamais le dossier d'installation en cours."""
    if meme(ancien, nouveau) or dedans(nouveau, ancien):
        return
    for nom in CONTENU + EXES:
        chemin = ancien / nom
        try:
            if chemin.is_dir():
                shutil.rmtree(chemin)
            else:
                chemin.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        ancien.rmdir()  # seulement s'il est vide
    except OSError:
        pass


def creer_raccourci(exe: Path) -> bool:
    """Raccourci « Studio Dock » dans le menu Démarrer (Windows) ; False si impossible (non bloquant)."""
    if not winapi.IS_WIN:
        return False
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    lien = Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / RACCOURCI

    def _ps(texte: str) -> str:
        return "'" + texte.replace("'", "''") + "'"

    script = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({_ps(str(lien))});"
              f"$s.TargetPath={_ps(str(exe))};$s.WorkingDirectory={_ps(str(exe.parent))};"
              f"$s.IconLocation={_ps(str(exe) + ',0')};$s.Description='Studio Dock';$s.Save()")
    try:
        lien.parent.mkdir(parents=True, exist_ok=True)
        resultat = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                                  capture_output=True, timeout=20, **winapi.options_processus())
        return resultat.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def redemarrer(exe: Path, ancien: Path | None, avant: Callable[[], None]) -> None:
    """Relance Studio Dock depuis `exe` (avec le nettoyage de l'ancien dossier), puis quitte celui-ci."""

    def _relancer() -> None:
        avant()
        arguments = [a for a in sys.argv[1:] if a not in ("--after-update",)]
        if "--cleanup" in arguments:
            i = arguments.index("--cleanup")
            del arguments[i:i + 2]
        commande = [str(exe), "--after-update", *arguments]
        if ancien is not None:
            commande += ["--cleanup", str(ancien)]
        winapi.lancer_detache(commande, cwd=exe.parent, stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os._exit(0)

    # Laisse la réponse partir vers l'interface avant de quitter
    threading.Timer(1.0, _relancer).start()

