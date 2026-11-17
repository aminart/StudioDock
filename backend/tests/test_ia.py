"""Modèles d'IA communs : connexions de Studio Dock, lues par les apps avec contrat/studiodock_ia.py."""
import importlib.util
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from tests.conftest import ecrire_catalogue

CONTRAT = Path(__file__).resolve().parents[2] / "contrat" / "studiodock_ia.py"


def lecteur():
    """Le module que chaque app embarque, chargé tel quel."""
    spec = importlib.util.spec_from_file_location("studiodock_ia", CONTRAT)
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules["studiodock_ia"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def dossier_ia(maison, monkeypatch):
    """Comme une app lancée par Studio Dock : STUDIODOCK_IA désigne le dossier des modèles."""
    monkeypatch.setenv("STUDIODOCK_IA", str(maison / "ia"))


@pytest.fixture
def faux_serveur():
    """Faux service : compatible OpenAI (/v1/models, /v1/chat/completions) et Ollama (/api/…)."""
    etat = {"cle": "sk-secrete-1234", "modeles": ["mistral-small:latest", "llama3.2:3b"], "tires": []}

    class Gestion(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _json(self, code, donnees):
            corps = json.dumps(donnees).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            if self.path == "/v1/models":
                if self.headers.get("Authorization") != f"Bearer {etat['cle']}":
                    return self._json(401, {"error": {"message": "bad key"}})
                return self._json(200, {"data": [{"id": m} for m in etat["modeles"]]})
            if self.path == "/api/version":
                return self._json(200, {"version": "0.13.0"})
            if self.path == "/api/tags":
                return self._json(200, {"models": [{"name": m, "size": 4_000_000_000,
                                                    "details": {"parameter_size": "7B"}} for m in etat["modeles"]]})
            self._json(404, {})

        def do_POST(self):
            longueur = int(self.headers.get("Content-Length") or 0)
            corps = json.loads(self.rfile.read(longueur) or b"{}")
            if self.path == "/api/pull":
                etat["tires"].append(corps["model"])
                self.send_response(200)
                self.end_headers()
                for ligne in ({"status": "pulling manifest"}, {"status": "pulling abc", "total": 10, "completed": 10},
                              {"status": "success"}):
                    self.wfile.write((json.dumps(ligne) + "\n").encode())
                etat["modeles"].append(corps["model"] + ":latest")
                return
            self._json(404, {})

    serveur = ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    etat["adresse"] = f"http://127.0.0.1:{serveur.server_address[1]}"
    yield etat
    serveur.shutdown()


def test_connexion_enregistree_lue_par_les_apps(client, maison, faux_serveur):
    ecrire_catalogue(maison, [
        {"id": "specgen", "name": "SpecGen", "exe": "SpecGenerator", "port": 18010, "ai": True},
        {"id": "outil", "name": "Outil", "exe": "Outil", "port": 18011},
    ])
    base = faux_serveur["adresse"] + "/v1"
    test = client.post("/api/ia/test", json={"api_base": base, "api_key": "sk-secrete-1234", "models": ["mistral-small"]})
    assert test.json()["ok"], test.json()
    refus = client.post("/api/ia/test", json={"api_base": base, "api_key": "mauvaise", "models": ["mistral-small"]})
    assert refus.json()["field"] == "api_key"

    r = client.post("/api/ia/connections", json={"name": "Passerelle", "api_base": base, "api_key": "sk-secrete-1234",
                                                  "models": ["mistral-small", "llama3.2"], "last_test": test.json()})
    donnees = r.json()
    connexion = donnees["connections"][0]
    assert "sk-secrete" not in json.dumps(donnees)  # jamais la clé dans l'interface
    assert connexion["has_api_key"] and connexion["api_key_hint"] == "1234"
    assert donnees["default"] == {"connection": connexion["id"], "model": "mistral-small"}  # premier modèle
    assert [a["id"] for a in donnees["apps"]] == ["specgen"]  # seules les apps avec IA

    sd = lecteur()
    assert sd.dossier() == maison / "ia"
    choix = sd.pour_app("specgen")
    assert (choix.model, choix.connexion.api_key, choix.connexion.api_base) == ("mistral-small", "sk-secrete-1234", base)

    # Un modèle pour SpecGen, puis sa configuration propre
    client.put("/api/ia/choices", json={"default": donnees["default"],
                                        "apps": {"specgen": {"connection": connexion["id"], "model": "llama3.2"}}})
    assert sd.pour_app("specgen").model == "llama3.2"
    client.put("/api/ia/choices", json={"default": donnees["default"], "apps": {"specgen": {"own": True}}})
    assert sd.pour_app("specgen") is None and sd.garde_sa_configuration("specgen")

    # Modifier sans renvoyer la clé la garde ; changer d'adresse refuse de l'envoyer ailleurs au test
    client.put(f"/api/ia/connections/{connexion['id']}", json={"name": "Passerelle", "api_base": base,
                                                                "models": ["llama3.2"]})
    assert sd.connexions()[0].api_key == "sk-secrete-1234"
    ailleurs = client.post("/api/ia/test", json={"id": connexion["id"], "api_base": "http://127.0.0.1:9/v1",
                                                  "models": ["llama3.2"]})
    assert ailleurs.json()["field"] == "api_key"

    # Le modèle par défaut retiré de la connexion : remplacé par un modèle existant
    assert sd.pour_app("outil").model == "llama3.2"

    client.delete(f"/api/ia/connections/{connexion['id']}")
    assert sd.connexions() == [] and sd.pour_app("specgen") is None


def test_format_plus_recent_ignore(maison):
    (maison / "ia").mkdir()
    (maison / "ia" / "connexions.json").write_text(json.dumps({"format": 99, "connections": [
        {"id": "x", "name": "x", "api_base": "http://x/v1", "models": ["m"]}]}), encoding="utf-8")
    assert lecteur().connexions() == []


def test_certificat(client, maison, faux_serveur):
    import ssl

    r = client.post("/api/ia/connections", json={"api_base": faux_serveur["adresse"] + "/v1", "models": ["m"]})
    id_ = r.json()["created"]
    refus = client.post(f"/api/ia/connections/{id_}/certificate", json={"name": "x.crt", "data": "bm9u"})
    assert refus.status_code == 422
    # Un certificat d'autorité du système, au format PEM
    certificats = ssl.create_default_context().get_ca_certs(binary_form=True)
    if not certificats:
        pytest.skip("aucun certificat système disponible")
    import base64

    r = client.post(f"/api/ia/connections/{id_}/certificate",
                    json={"name": "entreprise.crt", "data": base64.b64encode(certificats[0]).decode()})
    assert r.status_code == 200, r.text
    assert r.json()["connections"][0]["certificate"]["name"] == "entreprise.crt"
    assert Path(lecteur().connexions()[0].ca_bundle).is_file()


def test_ollama(client, maison, faux_serveur):
    adresse = faux_serveur["adresse"]
    etat = client.get("/api/ia/ollama", params={"address": adresse}).json()
    assert etat["running"] and etat["version"] == "0.13.0"
    assert [m["name"] for m in etat["models"]] == ["llama3.2:3b", "mistral-small:latest"]
    assert client.get("/api/ia/ollama", params={"address": "http://127.0.0.1:9"}).json()["running"] is False

    client.post("/api/ia/ollama/pull", json={"model": "qwen3", "address": adresse})
    for _ in range(50):
        pulls = client.get("/api/ia/ollama", params={"address": adresse}).json()["pulls"]
        if pulls and pulls[0]["finished"]:
            break
        time.sleep(0.05)
    assert pulls[0]["status"] == "Installé" and faux_serveur["tires"] == ["qwen3"]

    r = client.put("/api/ia/ollama", json={"address": adresse, "models": ["qwen3:latest", "llama3.2:3b"]}).json()
    c = r["connections"][0]
    assert (c["provider"], c["api_base"], c["context_tokens"]) == ("ollama", adresse + "/v1", 4096)
    sd = lecteur()
    assert sd.connexions()[0].local and sd.pour_app("specgen").model == "qwen3:latest"
    # Plus aucun modèle proposé : la connexion Ollama disparaît
    client.put("/api/ia/ollama", json={"address": adresse, "models": []})
    assert sd.connexions() == []


def test_apps_lancees_recoivent_le_dossier(maison):
    from app import ia, winapi

    assert winapi.environnement_propre()["STUDIODOCK_IA"] == str(ia.dossier())
