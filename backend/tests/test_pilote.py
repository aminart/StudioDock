import socket
import subprocess
import sys
import time

from conftest import deposer, ecrire_catalogue, port_libre


def _attendre(client, app_id, etats, delai=20):
    fin = time.monotonic() + delai
    while time.monotonic() < fin:
        app = next(a for a in client.get("/api/apps").json()["apps"] if a["id"] == app_id)
        if app["state"] in etats:
            return app
        time.sleep(0.2)
    raise AssertionError(f"{app_id} : état {app['state']} au lieu de {etats}")


def _catalogue(maison, port, **champs):
    ecrire_catalogue(maison, [{"id": "demo", "name": "Démo", "exe": "Demo", "port": port, **champs}])


def test_health(client):
    r = client.get("/health").json()
    assert r["app"] == "studiodock" and r["status"] == "ok"


def test_cycle_complet_d_une_app_web(client, maison):
    port = port_libre()
    _catalogue(maison, port)
    app = client.get("/api/apps").json()["apps"][0]
    assert app["state"] == "missing" and app["folder"].endswith("demo")

    r = client.post("/api/apps/demo/launch")
    assert r.status_code == 409 and r.json()["code"] == "missing"

    deposer(maison, "demo", "Demo-1.0.0.py")
    assert client.get("/api/apps").json()["apps"][0]["state"] == "off"

    r = client.post("/api/apps/demo/launch")
    assert r.status_code == 200 and r.json()["state"] in ("starting", "on")
    app = _attendre(client, "demo", {"on"})
    assert app["version"] == "9.9.9" and app["url"] == f"http://127.0.0.1:{port}" and not app["external"]

    assert client.post("/api/apps/demo/open").json()["ok"]
    assert client.ouverts == [f"http://127.0.0.1:{port}"]

    assert client.post("/api/apps/demo/stop").json()["state"] == "off"


def test_port_pris_par_une_autre_application(client, maison):
    with socket.socket() as occupant:
        occupant.bind(("127.0.0.1", 0))
        occupant.listen()
        port = occupant.getsockname()[1]
        _catalogue(maison, port)
        deposer(maison, "demo", "Demo.py")
        r = client.post("/api/apps/demo/launch")
        assert r.status_code == 409 and r.json()["code"] == "port_busy"
        app = client.get("/api/apps").json()["apps"][0]
        assert app["state"] == "error" and app["error"]["code"] == "port_busy"
    assert client.post("/api/apps/demo/dismiss").json()["state"] == "off"


def test_arret_inattendu_avec_fin_du_journal(client, maison):
    _catalogue(maison, port_libre())
    deposer(maison, "demo", "Demo.py")
    (maison / "apps" / "demo" / "plante").write_text("")
    client.post("/api/apps/demo/launch")
    app = _attendre(client, "demo", {"error"})
    assert app["error"]["code"] == "crashed"
    assert "Erreur de démarrage simulée" in app["error"]["message"]
    # Noté dans le journal de Studio Dock, et le journal de l'app survit à la relance
    from app.info import logs_dir

    session = (logs_dir() / "studiodock.log").read_text(encoding="utf-8")
    assert "s'est arrêtée seule" in session and "Erreur de démarrage simulée" in session
    client.post("/api/apps/demo/dismiss")
    client.post("/api/apps/demo/launch")
    _attendre(client, "demo", {"error"})
    assert "Erreur de démarrage simulée" in (logs_dir() / "demo.precedent.log").read_text(encoding="utf-8")


def test_app_deja_lancee_hors_de_studio_dock(client, maison):
    port = port_libre()
    _catalogue(maison, port)
    exe = deposer(maison, "demo", "Demo.py")
    externe = subprocess.Popen([sys.executable, str(exe), "--port", str(port), "--no-browser"])
    try:
        app = _attendre(client, "demo", {"on"})
        assert app["external"]
        assert client.post("/api/apps/demo/launch").json()["state"] == "on"  # rien de relancé
        client.post("/api/apps/demo/stop")
        externe.wait(timeout=10)  # arrêtée par Studio Dock (si le système autorise la lecture des ports)
    except subprocess.TimeoutExpired:
        pass
    finally:
        externe.kill()


def test_fermeture_arrete_les_apps_lancees(client, maison):
    from app import main

    _catalogue(maison, port_libre())
    deposer(maison, "demo", "Demo.py")
    client.post("/api/apps/demo/launch")
    _attendre(client, "demo", {"on"})
    process = main.pilote._lancements["demo"].process
    main.pilote.tout_arreter()
    assert process.wait(timeout=10) is not None


def test_app_native_introuvable_et_icone(client, maison):
    ecrire_catalogue(maison, [{"id": "mapline", "name": "Mapline", "kind": "native", "exe": "Mapline",
                               "icon": {"file": "icons/mapline.svg", "style": "logo"}}])
    app = client.get("/api/apps").json()["apps"][0]
    assert app["state"] == "missing" and app["url"] is None
    assert app["iconUrl"] == "/api/apps/mapline/icon"
    r = client.get(app["iconUrl"])
    assert r.status_code == 200 and b"<svg" in r.content
    assert client.post("/api/apps/mapline/stop").json()["code"] == "unsupported"
    assert client.post("/api/apps/inconnue/launch").status_code == 404


def test_app_occupee_jamais_arretee(client, maison, monkeypatch):
    """Une app démarrée qui tarde à répondre à /health (longue génération) n'est pas arrêtée, même après le délai
    de démarrage : avant, Studio Dock la coupait (« ne répond pas après 120 secondes »)."""
    from app import pilote as module

    _catalogue(maison, port_libre())
    deposer(maison, "demo", "Demo.py")
    client.post("/api/apps/demo/launch")
    _attendre(client, "demo", {"on"})
    monkeypatch.setattr(module, "DELAI_DEMARRAGE", 0)
    vraie_sante = module.Pilote._sante

    async def muette(self, client_, port):
        return None  # /health ne répond plus à temps

    monkeypatch.setattr(module.Pilote, "_sante", muette)
    for _ in range(3):
        app = client.get("/api/apps").json()["apps"][0]
        assert app["state"] == "on" and app.get("busy") is True
    from app.main import pilote

    assert pilote._lancements["demo"].process.poll() is None  # toujours en vie
    monkeypatch.setattr(module.Pilote, "_sante", vraie_sante)
    assert client.post("/api/apps/demo/stop").json()["state"] == "off"


def test_demarrage_sans_reponse_arrete(client, maison, monkeypatch):
    from app import pilote as module

    _catalogue(maison, port_libre())
    deposer(maison, "demo", "Demo.py")

    async def muette(self, client_, port):
        return None

    monkeypatch.setattr(module.Pilote, "_sante", muette)
    client.post("/api/apps/demo/launch")
    monkeypatch.setattr(module, "DELAI_DEMARRAGE", 0)
    app = _attendre(client, "demo", {"error"})
    assert app["error"]["code"] == "timeout"


def test_tutoriel_premiere_connexion(client, maison):
    _catalogue(maison, port_libre())
    assert client.get("/api/apps").json()["welcome"] is True
    client.put("/api/settings", json={"welcome_done": True})
    assert client.get("/api/apps").json()["welcome"] is False
    client.put("/api/settings", json={"welcome_done": False})
    deposer(maison, "demo", "Demo.py")  # une app déjà installée : pas de tutoriel
    assert client.get("/api/apps").json()["welcome"] is False


def test_onglet_preparer_pour_qui_tient_le_catalogue(client, maison, tmp_path):
    _catalogue(maison, port_libre())
    assert client.get("/api/apps").json()["catalogueAdmin"] is False
    assert client.put("/api/settings", json={"catalogue_admin": True}).json()["catalogue_admin"] is True
    assert client.get("/api/apps").json()["catalogueAdmin"] is True
    client.put("/api/settings", json={"catalogue_admin": False})
    assert client.get("/api/apps").json()["catalogueAdmin"] is False


def test_onglet_preparer_decoche_par_defaut(client, maison, tmp_path):
    from app import reglages

    # Même si un dossier de préparation a déjà servi : la case reste à cocher soi-même
    reglages.modifier(prepare_folder=str(tmp_path))
    assert client.get("/api/settings").json()["catalogue_admin"] is False
    client.put("/api/settings", json={"catalogue_admin": True})
    assert client.get("/api/settings").json()["catalogue_admin"] is True


def test_fermeture_de_la_fenetre_demande_si_des_apps_sont_ouvertes(client, maison, monkeypatch):
    from app import main

    # Sans fenêtre (navigateur, tests) : rien à réduire ni à fermer
    assert client.post("/api/window/minimize").status_code == 409
    assert client.post("/api/window/close").status_code == 409

    _catalogue(maison, port_libre())
    deposer(maison, "demo", "Demo.py")
    assert main.pilote.apps_ouvertes() == []
    client.post("/api/apps/demo/launch")
    _attendre(client, "demo", {"on"})
    assert main.pilote.apps_ouvertes() == ["demo"]

    appels = []
    monkeypatch.setattr(main, "reduire_fenetre", lambda: appels.append("réduite"))
    monkeypatch.setattr(main, "fermer_fenetre", lambda: appels.append("fermée"))
    assert client.post("/api/window/minimize").json()["ok"]
    assert client.post("/api/window/close").json()["ok"]
    assert appels == ["réduite", "fermée"]

    client.post("/api/apps/demo/stop")
    assert main.pilote.apps_ouvertes() == []
