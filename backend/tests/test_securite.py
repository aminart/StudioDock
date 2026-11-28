"""Garde-fous de l'API locale : une page web ne peut ni commander Studio Dock ni lire ses réponses."""


def test_hote_inconnu_refuse_dns_rebinding(client):
    assert client.get("/api/apps", headers={"host": "piege.example.com"}).status_code == 403
    assert client.get("/health", headers={"host": "piege.example.com:8000"}).status_code == 403
    assert client.get("/health", headers={"host": "localhost:8000"}).status_code == 200


def test_commande_depuis_un_autre_site_refusee(client):
    for chemin in ("/api/apps/docanalyser/install", "/api/catalogue/check", "/api/admin/catalogue",
                   "/api/apps/docanalyser/start", "/api/transcription/install"):
        r = client.post(chemin, json={}, headers={"origin": "https://piege.example.com"})
        assert r.status_code == 403, chemin
    assert client.put("/api/settings", json={}, headers={"origin": "http://127.0.0.1:8110"}).status_code == 403
    assert client.post("/api/catalogue/check", headers={"sec-fetch-site": "cross-site"}).status_code == 403
    # l'interface elle-même, ou le lanceur (sans navigateur) : acceptés
    assert client.post("/api/catalogue/check", headers={"origin": "http://127.0.0.1"}).status_code != 403
    assert client.post("/api/catalogue/check").status_code != 403


def test_entetes_de_protection(client):
    r = client.get("/health")
    assert r.headers["x-frame-options"] == "DENY" and r.headers["cross-origin-resource-policy"] == "same-origin"
