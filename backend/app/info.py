"""Identité de Studio Dock et emplacements de ses fichiers.

Le numéro de version vit à UN seul endroit : le fichier VERSION à la racine du dépôt (embarqué dans l'exe).
Pour publier une version : python scripts/bump_version.py patch|minor|major (voir README, « Versions »).
"""
from __future__ import annotations

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


def home_dir() -> Path:
    """Dossier de Studio Dock : apps.json, apps\\<id>\\ et icônes personnalisées.

    Windows : à côté de StudioDock.exe (dossier portable) ; Mac : ~/Library/Application Support/StudioDock ;
    STUDIODOCK_HOME pour un autre dossier ;
    en développement, le dossier « local » du dépôt (ignoré par git).
    """
    if autre := os.environ.get("STUDIODOCK_HOME", "").strip():
        return Path(autre).expanduser().resolve()
    if EMPAQUETE and sys.platform == "darwin":
        # Mac : l'app est rangée dans Applications, ses réglages et les programmes des apps vont ici
        return Path.home() / "Library" / "Application Support" / "StudioDock"
    if EMPAQUETE:
        return Path(sys.executable).resolve().parent
    return REPO_DIR / "local"


def logs_dir() -> Path:
    """Journaux de Studio Dock et des apps qu'il lance."""
    if EMPAQUETE and sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "StudioDock" / "logs"
    if EMPAQUETE and sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "StudioDock"
    return home_dir() / "logs"


def _lire_version() -> str:
    try:
        return (resources_dir() / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


VERSION = _lire_version()
