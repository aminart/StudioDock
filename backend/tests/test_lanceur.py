import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from conftest import port_libre

LANCEUR = Path(__file__).resolve().parent.parent / "launcher.py"


def test_version():
    sortie = subprocess.run([sys.executable, str(LANCEUR), "--version"], capture_output=True, text=True, timeout=30)
    assert sortie.stdout.startswith("Studio Dock ")


def test_serveur_seul_repond_sur_health(maison):
    port = port_libre()
    process = subprocess.Popen([sys.executable, str(LANCEUR), "--no-window", "--port", str(port), "--home", str(maison)])
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                    assert json.loads(r.read())["app"] == "studiodock"
                    break
            except OSError:
                time.sleep(0.2)
        else:
            raise AssertionError("Studio Dock ne répond pas")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/apps", timeout=5) as r:
            assert len(json.loads(r.read())["apps"]) == 4
        assert (maison / "apps.json").is_file()
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_arret_de_studio_dock_arrete_les_apps(maison):
    from conftest import deposer, ecrire_catalogue

    port, port_app = port_libre(), port_libre()
    ecrire_catalogue(maison, [{"id": "demo", "name": "Démo", "exe": "Demo", "port": port_app}])
    deposer(maison, "demo", "Demo.py")
    process = subprocess.Popen([sys.executable, str(LANCEUR), "--no-window", "--port", str(port), "--home", str(maison)])
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/api/apps/demo/launch", method="POST"), timeout=2)
                break
            except OSError:
                time.sleep(0.2)
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port_app}/health", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise AssertionError("l'app ne démarre pas")
    finally:
        process.terminate()
        process.wait(timeout=15)
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port_app}/health", timeout=0.5)
            time.sleep(0.2)
        except OSError:
            return
    raise AssertionError("l'app tourne encore après l'arrêt de Studio Dock")
