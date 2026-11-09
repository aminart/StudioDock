import json
import shutil
import time

from conftest import ICI, port_libre


def _partage(tmp_path):
    partage = tmp_path / "partage"
    for dossier, noms in {"Demo": ["Demo-1.0.0.py", "Demo-1.1.0.py"], "Projet B": ["Bis-2.0.0.py"],
                          "Cache": ["Masquee-1.0.0.py"]}.items():
        (partage / dossier).mkdir(parents=True)
        for nom in noms:
            shutil.copyfile(ICI / "fausse_app.py", partage / dossier / nom)
    (partage / "icons").mkdir()
    (partage / "icons" / "bis.svg").write_text("<svg/>")
    catalogue = {"apps": [
        {"id": "demo", "name": "Démo", "exe": "Demo", "port": port_libre(), "source": "Demo", "mode": "auto"},
        {"id": "bis", "name": "Bis", "exe": "Bis", "port": port_libre(), "source": "Projet B",
         "icon": {"file": "icons/bis.svg"}},
        {"id": "masquee", "name": "Masquée", "exe": "Masquee", "port": port_libre(), "source": "Cache", "mode": "masque"},
    ]}
    (partage / "catalogue.json").write_text(json.dumps(catalogue), encoding="utf-8")
    return partage


def _apps(client):
    return {a["id"]: a for a in client.get("/api/apps").json()["apps"]}


def _attendre(client, condition, delai=20):
    fin = time.monotonic() + delai
    while time.monotonic() < fin:
        apps = _apps(client)
        if condition(apps):
            return apps
        time.sleep(0.2)
    raise AssertionError(f"délai dépassé : {apps}")


def test_installation_depuis_le_partage(client, maison, tmp_path):
    from app import main

    partage = _partage(tmp_path)
    reglage = client.put("/api/settings", json={"shared_folder": str(partage)}).json()
    assert reglage["reachable"] and reglage["hasCatalogue"]

    etat = client.get("/api/apps").json()
    assert etat["source"] == "shared" and etat["sharedOk"]
    apps = {a["id"]: a for a in etat["apps"]}
    assert set(apps) == {"demo", "bis"}  # app masquée absente
    assert not apps["bis"]["installed"] and not apps["bis"]["isNew"] and apps["bis"]["availableVersion"] == "2.0.0"
    assert apps["bis"]["iconUrl"]  # icône lue dans le partage

    # App « auto » : installée d'office, dernière version, copie locale
    apps = _attendre(client, lambda a: a["demo"]["installed"] and a["demo"]["progress"] is None)
    assert apps["demo"]["version"] == "1.1.0"
    assert (maison / "apps" / "demo" / "Demo-1.1.0.py").is_file()

    # App optionnelle : installée à la demande, lancée depuis la copie locale
    assert client.post("/api/apps/bis/install").status_code == 200
    _attendre(client, lambda a: a["bis"]["installed"])
    client.post("/api/apps/bis/launch")
    apps = _attendre(client, lambda a: a["bis"]["state"] == "on")
    assert apps["bis"]["location"].startswith(str(maison))

    # Nouvelle version déposée sur le partage : signalée, puis installée (l'app lancée est arrêtée avant)
    shutil.copyfile(ICI / "fausse_app.py", partage / "Projet B" / "Bis-2.1.0.py")
    main._cache_partage.clear()
    apps = _apps(client)
    assert apps["bis"]["update"] and apps["bis"]["availableVersion"] == "2.1.0"
    client.post("/api/apps/bis/install")
    _attendre(client, lambda a: a["bis"]["installed"] and not a["bis"]["update"] and a["bis"]["progress"] is None)
    assert sorted(f.name for f in (maison / "apps" / "bis").iterdir()) == ["Bis-2.1.0.py"]

    # Retrait : possible pour une app optionnelle, refusé pour une app imposée
    assert client.post("/api/apps/demo/uninstall").status_code == 409
    assert not client.post("/api/apps/bis/uninstall").json()["installed"]

    # App ajoutée au catalogue après le premier passage : « Nouveau » jusqu'à ce qu'elle soit vue
    catalogue = json.loads((partage / "catalogue.json").read_text(encoding="utf-8"))
    catalogue["apps"].append({"id": "tierce", "name": "Tierce", "exe": "Tierce", "port": port_libre(), "source": "Tierce"})
    (partage / "catalogue.json").write_text(json.dumps(catalogue), encoding="utf-8")
    assert _apps(client)["tierce"]["isNew"]
    client.post("/api/seen", json={"ids": ["tierce"]})
    assert not _apps(client)["tierce"]["isNew"]


def test_partage_inaccessible_copie_locale(client, maison, tmp_path):
    partage = _partage(tmp_path)
    client.put("/api/settings", json={"shared_folder": str(partage)})
    client.get("/api/apps")
    shutil.move(partage, tmp_path / "debranche")
    etat = client.get("/api/apps").json()
    assert etat["source"] == "cache" and not etat["sharedOk"]
    assert {a["id"] for a in etat["apps"]} == {"demo", "bis"}
    assert client.post("/api/apps/bis/install").status_code == 409


def test_reglage_prepare_par_l_administratrice(client, maison, tmp_path):
    partage = _partage(tmp_path)
    (maison / "studiodock.config.json").write_text(json.dumps({"shared_folder": str(partage)}), encoding="utf-8")
    assert client.get("/api/settings").json()["resolved"] == str(partage)
    assert client.get("/api/apps").json()["source"] == "shared"
    # Sans dossier partagé : liste locale (apps.json), comme à l'étape 1
    client.put("/api/settings", json={"shared_folder": ""})
    (maison / "studiodock.config.json").unlink()
    assert client.get("/api/apps").json()["source"] == "local"


def test_nouvelle_version_de_studio_dock(client, maison, tmp_path):
    partage = _partage(tmp_path)
    (partage / "StudioDock").mkdir()
    (partage / "StudioDock" / "StudioDock-0.0.1.py").write_text("")
    client.put("/api/settings", json={"shared_folder": str(partage)})
    assert client.get("/api/apps").json()["dock"]["update"] is None  # plus ancienne : ignorée
    (partage / "StudioDock" / "StudioDock-9.0.0.py").write_text("")
    dock = client.get("/api/apps").json()["dock"]
    assert dock == {"update": "9.0.0", "canUpdate": False, "waiting": False}
