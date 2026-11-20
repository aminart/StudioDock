"""Journal de session de Studio Dock (logs/studiodock.log) : démarrages, arrêts et apps arrêtées sans qu'on le
demande, pour comprendre après coup pourquoi une app est devenue injoignable."""
from __future__ import annotations

import time

from app.info import logs_dir

FICHIER = "studiodock.log"
TAILLE_MAX = 2_000_000  # au-delà, l'ancien journal devient studiodock.precedent.log


def noter(message: str) -> None:
    try:
        dossier = logs_dir()
        dossier.mkdir(parents=True, exist_ok=True)
        chemin = dossier / FICHIER
        if chemin.is_file() and chemin.stat().st_size > TAILLE_MAX:
            chemin.replace(dossier / "studiodock.precedent.log")
        with open(chemin, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message.rstrip()}\n")
    except OSError:
        pass  # le journal ne doit jamais empêcher Studio Dock de tourner
