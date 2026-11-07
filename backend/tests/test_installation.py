"""Dossier d'installation choisi par chaque membre (Windows) : copie, déplacement, garde-fous, réglages."""
import json
from pathlib import Path

import pytest

from app import installation, reglages


def _exe(dossier: Path) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    exe = dossier / "StudioDock.exe"
    exe.write_bytes(b"MZ studio dock")
    return exe


def test_premiere_installation_copie_l_exe(tmp_path):
    exe = _exe(tmp_path / "partage" / "StudioDock")
    cible = installation.installer(tmp_path / "poste" / "StudioDock", exe, None)
    assert cible == tmp_path / "poste" / "StudioDock" / "StudioDock.exe"
    assert cible.read_bytes() == exe.read_bytes()
    assert exe.is_file()  # l'original reste dans le partage


def test_deplacement_emporte_les_apps_puis_vide_l_ancien_dossier(tmp_path):
    ancien = tmp_path / "ancien"
    exe = _exe(ancien)
    (ancien / "apps" / "specgen").mkdir(parents=True)
    (ancien / "apps" / "specgen" / "SpecGenerator-1.1.0.exe").write_bytes(b"MZ")
    (ancien / "catalogue.cache.json").write_text("{}")
    (ancien / "notes perso.txt").write_text("à garder")

    nouveau = tmp_path / "nouveau"
    installation.installer(nouveau, exe, ancien)
    assert (nouveau / "StudioDock.exe").is_file()
    assert (nouveau / "apps" / "specgen" / "SpecGenerator-1.1.0.exe").is_file()
    assert (nouveau / "catalogue.cache.json").is_file()
    assert not (nouveau / "notes perso.txt").exists()

    installation.nettoyer(ancien, nouveau)
    assert not (ancien / "StudioDock.exe").exists()
    assert not (ancien / "apps").exists()
    assert (ancien / "notes perso.txt").is_file()  # rien d'autre n'est effacé


def test_nettoyage_ne_touche_jamais_le_dossier_en_cours(tmp_path):
    dossier = tmp_path / "poste"
    _exe(dossier)
    installation.nettoyer(dossier, dossier)
    installation.nettoyer(tmp_path, dossier)  # dossier parent du dossier en cours
    assert (dossier / "StudioDock.exe").is_file()


@pytest.mark.parametrize("chemin", ["\\\\serveur\\Equipe UX\\Apps", "//serveur/equipe"])
def test_dossier_reseau_refuse(chemin, tmp_path):
    with pytest.raises(installation.ErreurInstallation, match="réseau|chemin complet"):
        installation.verifier(Path(chemin), None)


def test_dossier_dans_le_partage_refuse(tmp_path):
    partage = tmp_path / "Equipe UX"
    (partage / "StudioDock").mkdir(parents=True)
    with pytest.raises(installation.ErreurInstallation, match="partagé"):
        installation.verifier(partage / "StudioDock", partage)
    installation.verifier(tmp_path / "Apps" / "StudioDock", partage)  # un dossier du poste est accepté


def test_dossier_choisi_et_partage_sont_deux_reglages(maison):
    reglages.modifier(shared_folder="Z:\\Equipe UX", install_folder="C:\\Apps\\StudioDock")
    valeurs = json.loads((maison / "config.json").read_text(encoding="utf-8"))
    assert valeurs["shared_folder"] == "Z:\\Equipe UX"
    assert valeurs["install_folder"] == "C:\\Apps\\StudioDock"


def test_dossier_propose_par_l_administratrice(maison, monkeypatch):
    monkeypatch.setenv("UTILISATEUR_TEST", "albane")
    (maison / "studiodock.config.json").write_text(
        json.dumps({"install_folder": "D:\\Apps\\$UTILISATEUR_TEST\\StudioDock"}), encoding="utf-8")
    assert "albane" in str(installation.dossier_propose())
    # un choix proposé n'est pas un choix fait : Studio Dock reste « à installer »
    from app.info import dossier_installation_choisi
    assert dossier_installation_choisi() is None


def test_api_reglages_installation(client):
    etat = client.get("/api/settings").json()["install"]
    assert etat["available"] is False  # hors exe Windows
    assert client.get("/api/apps").json()["needsInstall"] is False
    r = client.put("/api/settings/install", json={"folder": "C:\\Apps"})
    assert r.status_code == 409


def test_api_installation_windows(client, maison, tmp_path, monkeypatch):
    """Exe Windows simulé, lancé depuis le partage : installation dans le dossier choisi, partage retenu."""
    from app import main

    partage = tmp_path / "Equipe UX"
    exe = _exe(partage / "StudioDock")
    (partage / "catalogue.json").write_text(json.dumps({"apps": []}), encoding="utf-8")
    monkeypatch.setattr(installation, "disponible", lambda: True)
    monkeypatch.setattr(main, "exe_dir", lambda: exe.parent)
    monkeypatch.setattr(installation, "exe_dir", lambda: exe.parent)
    monkeypatch.setattr(main.sys, "executable", str(exe))
    monkeypatch.setattr(installation, "creer_raccourci", lambda _exe: True)
    relances = []
    monkeypatch.setattr(installation, "redemarrer", lambda *a: relances.append(a))

    assert client.get("/api/apps").json()["needsInstall"] is True
    assert client.post("/api/apps/specgen/install").status_code in (404, 409)

    r = client.put("/api/settings/install", json={"folder": str(partage / "perso")})
    assert r.status_code == 409 and "partagé" in r.json()["detail"]

    poste = tmp_path / "poste" / "StudioDock"
    r = client.put("/api/settings/install", json={"folder": str(poste)})
    assert r.status_code == 200, r.text
    assert (poste / "StudioDock.exe").is_file()
    assert relances and relances[0][0] == poste / "StudioDock.exe" and relances[0][1] is None
    valeurs = reglages.locaux()
    assert Path(valeurs["install_folder"]) == poste
    assert Path(valeurs["shared_folder"]) == partage
