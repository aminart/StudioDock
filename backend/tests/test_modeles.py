"""Modèle de transcription de l'équipe : déclaré dans le catalogue, installé d'office, lu par les apps."""
import hashlib
import importlib.util
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import pytest
from test_en_ligne import _catalogue, _zip

from app import modeles

CONTRAT = Path(__file__).resolve().parents[2] / "contrat" / "studiodock_ia.py"


@pytest.fixture(autouse=True)
def sans_installation_en_cours(monkeypatch):
    monkeypatch.setattr(modeles, "_suivi", None)


def contrat():
    spec = importlib.util.spec_from_file_location("studiodock_ia_test", CONTRAT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # les dataclasses du contrat cherchent leur module dans sys.modules
    spec.loader.exec_module(module)
    return module


def archive_modele(chemin: Path, dossier: str = "faster-whisper-small/", taille: int = 1000, valide: bool = True) -> Path:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(chemin, "w") as z:
        z.writestr(dossier + "config.json", "{}")
        if valide:
            z.writestr(dossier + "model.bin", os.urandom(taille))
        z.writestr(dossier + "tokenizer.json", "{}")
    return chemin


def partage_avec_modele(tmp_path, archives=("faster-whisper-small-1.0.0.zip",)) -> Path:
    partage = tmp_path / "partage"
    (partage / "Modeles").mkdir(parents=True)
    for nom in archives:
        archive_modele(partage / "Modeles" / nom)
    (partage / "catalogue.json").write_text(json.dumps({
        "apps": [], "transcription": {"name": "Whisper small", "source": "Modeles"}}), encoding="utf-8")
    return partage


def attendre(client, condition, delai=15.0):
    fin = time.monotonic() + delai
    while time.monotonic() < fin:
        client.get("/api/apps")  # comme l'interface, qui rafraîchit la liste
        etat = client.get("/api/transcription").json()
        if condition(etat):
            return etat
        time.sleep(0.1)
    raise AssertionError(f"délai dépassé : {etat}")


def test_installe_d_office_depuis_le_partage_et_publie_pour_les_apps(client, maison, tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIODOCK_IA", str(maison / "ia"))
    partage = partage_avec_modele(tmp_path)
    client.put("/api/settings", json={"shared_folder": str(partage)})
    etat = attendre(client, lambda e: e["installed"])
    assert etat["name"] == "Whisper small" and etat["version"] == "1.0.0" and etat["offered"]
    assert (Path(etat["path"]) / "model.bin").is_file()
    assert Path(etat["path"]).is_relative_to(maison)  # sur le poste, jamais sur le partage

    modele = contrat().transcription()
    assert modele is not None and modele.name == "Whisper small" and modele.version == "1.0.0"
    assert Path(modele.path) == Path(etat["path"])


def test_nouvelle_archive_remplace_l_ancienne(client, maison, tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIODOCK_IA", str(maison / "ia"))
    partage = partage_avec_modele(tmp_path)
    client.put("/api/settings", json={"shared_folder": str(partage)})
    attendre(client, lambda e: e["version"] == "1.0.0")
    archive_modele(partage / "Modeles" / "faster-whisper-small-1.1.0.zip", dossier="")  # modèle à la racine du zip
    etat = attendre(client, lambda e: e["version"] == "1.1.0")
    assert (Path(etat["path"]) / "model.bin").is_file()
    assert contrat().transcription().version == "1.1.0"
    assert not (modeles.dossier_local().with_name("transcription.old")).exists()


def test_archive_sans_modele_refusee_sans_boucle(client, maison, tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIODOCK_IA", str(maison / "ia"))
    partage = partage_avec_modele(tmp_path, archives=())
    archive_modele(partage / "Modeles" / "mauvais.zip", valide=False)
    client.put("/api/settings", json={"shared_folder": str(partage)})
    etat = attendre(client, lambda e: e["error"])
    assert "model.bin" in etat["error"] and not etat["installed"]
    debut = modeles.en_cours()
    client.get("/api/apps")
    assert modeles.en_cours() is debut  # la même archive n'est pas retentée à chaque rafraîchissement
    assert contrat().transcription() is None


def test_archive_avec_chemin_dangereux_refusee(client, maison, tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIODOCK_IA", str(maison / "ia"))
    partage = partage_avec_modele(tmp_path, archives=())
    piege = partage / "Modeles" / "piege-1.0.0.zip"
    with zipfile.ZipFile(piege, "w") as z:
        z.writestr("config.json", "{}")
        z.writestr("model.bin", "x")
        z.writestr("../../evasion.txt", "non")
    client.put("/api/settings", json={"shared_folder": str(partage)})
    etat = attendre(client, lambda e: e["error"])
    assert "interdit" in etat["error"] and not (maison / "evasion.txt").exists()


def test_sans_modele_au_catalogue(client, maison, tmp_path):
    partage = tmp_path / "partage"
    partage.mkdir()
    (partage / "catalogue.json").write_text(json.dumps({"apps": []}), encoding="utf-8")
    client.put("/api/settings", json={"shared_folder": str(partage)})
    etat = client.get("/api/transcription").json()
    assert etat["offered"] is False and etat["installed"] is False
    assert client.post("/api/transcription/install").status_code == 409


def test_catalogue_en_ligne_telechargement_par_le_navigateur(client, maison, monkeypatch):
    monkeypatch.setenv("STUDIODOCK_IA", str(maison / "ia"))
    source = archive_modele(maison / "source" / "faster-whisper-small-2.0.0.zip")
    donnees = _catalogue(9999)
    donnees["transcription"] = {"name": "Whisper small", "source": "Modeles", "file": "faster-whisper-small",
                                "version": "2.0.0", "link": "https://entreprise.sharepoint.com/Modeles",
                                "size": source.stat().st_size, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    _zip(maison / "Telechargements", donnees)
    client.get("/api/apps")  # import du catalogue en ligne

    etat = client.get("/api/transcription").json()
    assert etat["online"] and etat["canDownload"] and not etat["installed"]
    etat = client.post("/api/transcription/install").json()
    assert etat["waiting"] and client.ouverts[-1] == "https://entreprise.sharepoint.com/Modeles"

    arrivee = maison / "Telechargements" / "faster-whisper-small-2.0.0 (1).zip"
    arrivee.write_bytes(source.read_bytes())
    ancien = time.time() - 10
    os.utime(arrivee, (ancien, ancien))
    etat = attendre(client, lambda e: e["installed"])
    assert etat["version"] == "2.0.0" and not arrivee.exists()


def test_telechargement_incomplet_refuse(client, maison, monkeypatch):
    monkeypatch.setenv("STUDIODOCK_IA", str(maison / "ia"))
    donnees = _catalogue(9999)
    donnees["transcription"] = {"name": "Whisper", "file": "faster-whisper-small", "version": "2.0.0",
                                "link": "https://x.sharepoint.com/M", "size": 999_999, "sha256": "0" * 64}
    _zip(maison / "Telechargements", donnees)
    client.get("/api/apps")
    client.post("/api/transcription/install")
    arrivee = archive_modele(maison / "Telechargements" / "faster-whisper-small-2.0.0.zip")
    ancien = time.time() - 10
    os.utime(arrivee, (ancien, ancien))
    etat = attendre(client, lambda e: e["error"])
    assert not etat["installed"]


def test_declarer_le_modele_dans_le_catalogue(client, tmp_path):
    dossier = tmp_path / "equipe"
    dossier.mkdir()
    client.post("/api/admin/catalogue/create", json={"folder": str(dossier)})
    r = client.put("/api/admin/catalogue/transcription",
                   json={"folder": str(dossier), "transcription": {"name": "Whisper small", "source": "Modèles IA"}}).json()
    assert r["transcription"]["name"] == "Whisper small" and r["transcription"]["sourceFound"]
    assert (dossier / "Modèles IA").is_dir()
    archive_modele(dossier / "Modèles IA" / "fw-small-1.2.0.zip")
    r = client.post("/api/admin/catalogue/apps", json={"folder": str(dossier)}).json()
    assert r["transcription"]["found"] == "fw-small-1.2.0.zip" and r["transcription"]["version"] == "1.2.0"
    assert client.put("/api/admin/catalogue/transcription",
                      json={"folder": str(dossier), "transcription": {"name": "x", "source": "../ailleurs"}}).status_code == 422
    r = client.put("/api/admin/catalogue/transcription", json={"folder": str(dossier), "transcription": None}).json()
    assert r["transcription"] is None
    assert "transcription" not in json.loads((dossier / "catalogue.json").read_text(encoding="utf-8"))


def test_fabriquer_le_catalogue_en_ligne_avec_le_modele(client, tmp_path):
    dossier = tmp_path / "equipe"
    dossier.mkdir()
    client.post("/api/admin/catalogue/create", json={"folder": str(dossier)})
    client.put("/api/admin/catalogue/transcription",
               json={"folder": str(dossier), "transcription": {"name": "Whisper small", "source": "Modeles"}})
    archive = archive_modele(dossier / "Modeles" / "faster-whisper-small-1.3.0.zip")
    etat = client.post("/api/admin/catalogue", json={"folder": str(dossier)}).json()
    assert etat["transcription"]["found"] == archive.name and "_chemin" not in etat["transcription"]
    client.post("/api/admin/catalogue/build", json={"folder": str(dossier), "transcriptionLink": "https://sp/Modeles"})
    modele = json.loads((dossier / "catalogue.json").read_text(encoding="utf-8"))["transcription"]
    assert modele["version"] == "1.3.0" and modele["file"] == "faster-whisper-small" and modele["link"] == "https://sp/Modeles"
    assert modele["size"] == archive.stat().st_size and modele["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    # les champs en ligne survivent à une modification du nom par formulaire
    client.put("/api/admin/catalogue/transcription",
               json={"folder": str(dossier), "transcription": {"name": "Whisper (équipe)", "source": "Modeles"}})
    modele = json.loads((dossier / "catalogue.json").read_text(encoding="utf-8"))["transcription"]
    assert modele["name"] == "Whisper (équipe)" and modele["sha256"] and modele["file"] == "faster-whisper-small"


def test_contrat_ignore_un_chemin_disparu(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIODOCK_IA", str(tmp_path))
    (tmp_path / "transcription.json").write_text(json.dumps({"format": 1, "name": "W", "path": str(tmp_path / "absent")}))
    assert contrat().transcription() is None
    (tmp_path / "transcription.json").write_text(json.dumps({"format": 9, "path": str(tmp_path)}))
    assert contrat().transcription() is None
