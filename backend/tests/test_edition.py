"""Préparer pour l'équipe : catalogue.json édité par formulaire, sans écrire de JSON."""
import base64
import json


def test_creer_puis_editer(client, tmp_path):
    dossier = tmp_path / "Q" / "Studio Dock"
    dossier.mkdir(parents=True)
    vide = client.post("/api/admin/catalogue/apps", json={"folder": str(dossier)}).json()
    assert vide["exists"] is False

    cree = client.post("/api/admin/catalogue/create", json={"folder": str(dossier)}).json()
    assert [a["id"] for a in cree["apps"]] == ["specgen", "audit-ergo", "docanalyser", "mapline"]
    assert all(a["iconFound"] and a["sourceFound"] for a in cree["apps"])
    assert (dossier / "StudioDock").is_dir()
    # Le catalogue créé est lu tel quel par « Préparer » (catalogue en ligne)
    assert client.post("/api/admin/catalogue", json={"folder": str(dossier)}).status_code == 200
    assert client.post("/api/admin/catalogue/create", json={"folder": str(dossier)}).status_code == 422

    # Nouvelle app : identifiant, programme, sous-dossier et port déduits du nom
    r = client.put("/api/admin/catalogue/apps", json={"folder": str(dossier), "app": {
        "name": "Trace Line", "kind": "web", "ai": True, "tagline": "Retrouver une décision",
        "points": ["Recherche", " "], "tutorial": [{"title": "Importer", "text": "Glissez vos mails."}, {"title": ""}],
        "links": [{"label": "Aide", "url": "https://exemple.fr"}, {"label": "", "url": ""}]}})
    assert r.status_code == 200, r.text
    app = next(a for a in r.json()["apps"] if a["id"] == "trace-line")
    assert (app["exe"], app["source"], app["port"], app["points"]) == ("TraceLine", "TraceLine", 8030, ["Recherche"])
    assert len(app["tutorial"]) == 1 and len(app["links"]) == 1
    assert (dossier / "TraceLine").is_dir()

    # Icône importée, puis servie
    svg = base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg"/>').decode()
    fichier = client.post("/api/admin/catalogue/icon", json={"folder": str(dossier), "id": "trace-line",
                                                             "name": "logo.svg", "data": svg}).json()["file"]
    assert fichier == "icons/trace-line.svg"
    assert client.get("/api/admin/catalogue/icon", params={"folder": str(dossier), "file": fichier}).status_code == 200
    assert client.get("/api/admin/catalogue/icon", params={"folder": str(dossier), "file": "../x.svg"}).status_code == 404
    refus = client.post("/api/admin/catalogue/icon", json={"folder": str(dossier), "id": "x", "name": "a.exe", "data": svg})
    assert refus.status_code == 422

    # Modifier : les champs du catalogue en ligne (version, lien…) sont gardés
    brut = json.loads((dossier / "catalogue.json").read_text(encoding="utf-8"))
    brut["apps"][0]["link"] = "https://sharepoint/specgen"
    (dossier / "catalogue.json").write_text(json.dumps(brut), encoding="utf-8")
    specgen = next(a for a in cree["apps"] if a["id"] == "specgen")
    r = client.put("/api/admin/catalogue/apps", json={"folder": str(dossier), "id": "specgen",
                                                       "app": {**specgen, "tagline": "Nouvelle accroche", "mode": "auto"}})
    assert r.status_code == 200, r.text
    brut = json.loads((dossier / "catalogue.json").read_text(encoding="utf-8"))
    assert brut["apps"][0]["tagline"] == "Nouvelle accroche" and brut["apps"][0]["link"] == "https://sharepoint/specgen"
    assert (dossier / "catalogue.json.bak").is_file()

    # Un port en double est refusé, sans toucher au fichier
    avant = (dossier / "catalogue.json").read_text(encoding="utf-8")
    r = client.put("/api/admin/catalogue/apps", json={"folder": str(dossier), "id": "trace-line",
                                                       "app": {**app, "port": 8010}})
    assert r.status_code == 422 and "port 8010" in r.json()["detail"]
    assert (dossier / "catalogue.json").read_text(encoding="utf-8") == avant

    # Ordre et suppression
    r = client.post("/api/admin/catalogue/apps/move", json={"folder": str(dossier), "id": "trace-line", "direction": -1})
    assert [a["id"] for a in r.json()["apps"]][-2:] == ["trace-line", "mapline"]
    r = client.post("/api/admin/catalogue/apps/delete", json={"folder": str(dossier), "id": "trace-line"})
    assert "trace-line" not in [a["id"] for a in r.json()["apps"]]


def test_dossier_partage_signale(client, tmp_path):
    dossier = tmp_path / "partage"
    dossier.mkdir()
    client.put("/api/settings", json={"shared_folder": str(dossier)})
    r = client.post("/api/admin/catalogue/create", json={"folder": str(dossier)}).json()
    assert r["isShared"] is True


def test_app_web_externe_dans_le_catalogue(client, tmp_path):
    dossier = tmp_path / "Q"
    dossier.mkdir()
    client.post("/api/admin/catalogue/create", json={"folder": str(dossier)})

    # Sans adresse : port vide, détecté au lancement
    r = client.put("/api/admin/catalogue/apps", json={"folder": str(dossier), "app": {
        "name": "Snappy Transcript", "kind": "external", "address": " "}})
    assert r.status_code == 200, r.text
    app = next(a for a in r.json()["apps"] if a["id"] == "snappy-transcript")
    assert (app["exe"], app["port"], app.get("address")) == ("SnappyTranscript", None, None)

    # Adresse fixe : gardée, son port compte pour les doublons
    r = client.put("/api/admin/catalogue/apps", json={"folder": str(dossier), "app": {
        **app, "address": "localhost:5000"}, "id": "snappy-transcript"})
    assert r.status_code == 200, r.text
    app = next(a for a in r.json()["apps"] if a["id"] == "snappy-transcript")
    assert app["address"] == "http://localhost:5000"

    # Adresse hors de ce poste : refusée avec un message clair
    r = client.put("/api/admin/catalogue/apps", json={"folder": str(dossier), "app": {
        **app, "address": "http://serveur.fr:5000"}, "id": "snappy-transcript"})
    assert r.status_code == 422 and "sur ce poste" in r.text
