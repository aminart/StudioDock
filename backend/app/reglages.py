"""Réglages de Studio Dock sur ce poste : pour l'instant, le dossier partagé de l'équipe.

Ordre de lecture (le dernier gagne) :
1. studiodock.config.json à côté de Studio Dock (préparé par l'administratrice, livré avec l'exe) ;
2. config.json du dossier de Studio Dock (choix fait dans l'écran Réglages).

Le chemin peut contenir des variables (%USERNAME%, $HOME…), développées à la lecture.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from app.info import home_dir

PRESET = "studiodock.config.json"
LOCAL = "config.json"
_verrou = threading.Lock()


def _lire(chemin: Path) -> dict[str, Any]:
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        return donnees if isinstance(donnees, dict) else {}
    except (OSError, ValueError):
        return {}


def lire() -> dict[str, Any]:
    return {**_lire(home_dir() / PRESET), **_lire(home_dir() / LOCAL)}


def modifier(**valeurs: Any) -> dict[str, Any]:
    with _verrou:
        chemin = home_dir() / LOCAL
        donnees = _lire(chemin)
        for cle, valeur in valeurs.items():
            if valeur is None:
                donnees.pop(cle, None)
            else:
                donnees[cle] = valeur
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    return lire()


def dossier_partage() -> Path | None:
    brut = str(lire().get("shared_folder") or "").strip()
    if not brut:
        return None
    return Path(os.path.expanduser(os.path.expandvars(brut)))


def deja_vues() -> set[str]:
    return set(lire().get("seen") or [])


def marquer_vues(ids: list[str]) -> None:
    vues = deja_vues() | set(ids)
    modifier(seen=sorted(vues))
