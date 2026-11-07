"""Réglages de Studio Dock sur ce poste : dossier partagé de l'équipe et dossier d'installation (Windows).

Ordre de lecture (le dernier gagne) :
1. studiodock.config.json à côté de l'exe lancé, puis dans le dossier d'installation (réglages préparés par
   l'administratrice : shared_folder, install_folder proposé par défaut) ;
2. config.json des réglages du poste (choix faits dans Studio Dock), dans %LOCALAPPDATA%\\StudioDock sous
   Windows, pour ne pas dépendre du dossier d'installation.

Le chemin peut contenir des variables (%USERNAME%, $HOME…), développées à la lecture.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from app.info import config_dir, exe_dir, home_dir

PRESET = "studiodock.config.json"
LOCAL = "config.json"
_verrou = threading.Lock()


def _lire(chemin: Path) -> dict[str, Any]:
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        return donnees if isinstance(donnees, dict) else {}
    except (OSError, ValueError):
        return {}


def _migrer() -> None:
    """Versions 0.1.x : config.json était à côté de l'exe ; il rejoint les réglages du poste."""
    nouveau = config_dir() / LOCAL
    ancien_dossier = exe_dir()
    if nouveau.exists() or ancien_dossier is None or ancien_dossier == config_dir():
        return
    ancien = _lire(ancien_dossier / LOCAL)
    if ancien:
        nouveau.parent.mkdir(parents=True, exist_ok=True)
        nouveau.write_text(json.dumps(ancien, ensure_ascii=False, indent=2), encoding="utf-8")


def preset() -> dict[str, Any]:
    """Réglages préparés par l'administratrice (studiodock.config.json)."""
    dossiers = [d for d in (exe_dir(), home_dir()) if d is not None]
    valeurs: dict[str, Any] = {}
    for dossier in dict.fromkeys(dossiers):
        valeurs.update(_lire(dossier / PRESET))
    return valeurs


def locaux() -> dict[str, Any]:
    """Choix faits sur ce poste, sans les réglages préparés."""
    _migrer()
    return _lire(config_dir() / LOCAL)


def lire() -> dict[str, Any]:
    return {**preset(), **locaux()}


def modifier(**valeurs: Any) -> dict[str, Any]:
    with _verrou:
        _migrer()
        chemin = config_dir() / LOCAL
        donnees = _lire(chemin)
        for cle, valeur in valeurs.items():
            if valeur is None:
                donnees.pop(cle, None)
            else:
                donnees[cle] = valeur
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    return lire()


def developper(brut: str | None) -> Path | None:
    """Chemin saisi, avec ses variables (%USERNAME%, $HOME…) développées."""
    brut = str(brut or "").strip()
    return Path(os.path.expanduser(os.path.expandvars(brut))) if brut else None


def dossier_partage() -> Path | None:
    return developper(lire().get("shared_folder"))


def deja_vues() -> set[str]:
    return set(lire().get("seen") or [])


def marquer_vues(ids: list[str]) -> None:
    vues = deja_vues() | set(ids)
    modifier(seen=sorted(vues))
