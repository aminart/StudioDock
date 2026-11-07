"""Identité de Studio Dock et emplacements de ses fichiers.

Le numéro de version vit à UN seul endroit : le fichier VERSION à la racine du dépôt (embarqué dans l'exe).
Pour publier une version : python scripts/bump_version.py patch|minor|major (voir README, « Versions »).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_ID = "studiodock"
PLATEFORME = "mac" if sys.platform == "darwin" else "windows" if sys.platform == "win32" else "linux"
APP_NAME = "Studio Dock"
DEFAULT_PORT = 8040

EMPAQUETE = bool(getattr(sys, "frozen", False))
REPO_DIR = Path(__file__).resolve().parent.parent.parent


def resources_dir() -> Path:
    """Fichiers livrés avec Studio Dock (catalogue par défaut, icônes, interface compilée)."""
    # PyInstaller : dossier temporaire de l'exe (Windows) ou Contents/Frameworks de l'app (Mac)
    if EMPAQUETE:
        return Path(getattr(sys, "_MEIPASS"))
    return REPO_DIR


def exe_dir() -> Path | None:
    """Dossier d'où l'exe a été lancé (exe empaqueté), sinon None."""
    return Path(sys.executable).resolve().parent if EMPAQUETE else None


def config_dir() -> Path:
    """Réglages de ce poste (config.json), indépendants du dossier d'installation.

    Windows : %LOCALAPPDATA%\\StudioDock ; Mac : ~/Library/Application Support/StudioDock ;
    STUDIODOCK_HOME (tests) ou, en développement, le dossier « local » du dépôt.
    """
    if autre := os.environ.get("STUDIODOCK_HOME", "").strip():
        return Path(autre).expanduser().resolve()
    if EMPAQUETE and sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "StudioDock"
    if EMPAQUETE and sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "StudioDock"
    return REPO_DIR / "local"


def dossier_installation_choisi() -> Path | None:
    """Windows : dossier d'installation choisi par la personne (réglage install_folder), sinon None."""
    try:
        donnees = json.loads((config_dir() / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    brut = str(donnees.get("install_folder") or "").strip() if isinstance(donnees, dict) else ""
    return Path(os.path.expanduser(os.path.expandvars(brut))) if brut else None


def home_dir() -> Path:
    """Dossier d'installation : StudioDock.exe, apps\\<id>\\ (programmes des apps), copies du catalogue.

    Windows : le dossier choisi par la personne ; tant qu'il n'est pas choisi, le dossier des réglages
    (jamais celui de l'exe, qui peut être le dossier partagé) ;
    Mac : ~/Library/Application Support/StudioDock ; STUDIODOCK_HOME pour un autre dossier ;
    en développement, le dossier « local » du dépôt (ignoré par git).
    """
    if os.environ.get("STUDIODOCK_HOME", "").strip() or not EMPAQUETE or sys.platform == "darwin":
        return config_dir()
    return dossier_installation_choisi() or config_dir()


def logs_dir() -> Path:
    """Journaux de Studio Dock et des apps qu'il lance."""
    if EMPAQUETE and sys.platform == "win32":
        return config_dir() / "logs"
    if EMPAQUETE and sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "StudioDock"
    return home_dir() / "logs"


def _lire_version() -> str:
    try:
        return (resources_dir() / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


VERSION = _lire_version()
