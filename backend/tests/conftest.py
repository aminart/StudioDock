import json
import shutil
import socket
from pathlib import Path

import pytest

ICI = Path(__file__).resolve().parent


def port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def maison(tmp_path, monkeypatch):
    """Dossier de Studio Dock isolé pour chaque test."""
    monkeypatch.setenv("STUDIODOCK_HOME", str(tmp_path))
    return tmp_path


def ecrire_catalogue(maison: Path, apps: list[dict]) -> None:
    (maison / "apps.json").write_text(json.dumps({"apps": apps}), encoding="utf-8")


def deposer(maison: Path, app_id: str, nom: str) -> Path:
    dossier = maison / "apps" / app_id
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / nom
    shutil.copyfile(ICI / "fausse_app.py", cible)
    return cible


@pytest.fixture
def client(maison, monkeypatch):
    from fastapi.testclient import TestClient

    from app import main
    from app.catalogue import Source
    from app.pilote import Pilote

    pilote = Pilote()
    monkeypatch.setattr(main, "source", Source())
    monkeypatch.setattr(main, "pilote", pilote)
    from app.installeur import Installeur

    monkeypatch.setattr(main, "installeur", Installeur(pilote))
    main._cache_partage.clear()
    # Pas de navigateur ni d'Explorateur pendant les tests
    ouverts = []
    monkeypatch.setattr(main.winapi, "ouvrir", ouverts.append)
    with TestClient(main.app) as c:
        c.ouverts = ouverts
        yield c
    pilote.tout_arreter()
