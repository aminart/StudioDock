"""Lance Studio Dock : python backend/launcher.py [--port 8040] [--browser] [--home DOSSIER] [--version]

Ouvre une fenêtre Windows (pywebview, moteur Edge WebView2) qui affiche l'interface servie en local.
Fermer la fenêtre arrête Studio Dock et les apps web qu'il a lancées.
--browser (ou pywebview indisponible) : l'interface s'ouvre dans le navigateur ; Ctrl+C pour arrêter.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.info import APP_ID, APP_NAME, DEFAULT_PORT, VERSION, logs_dir  # noqa: E402

HOTE = "127.0.0.1"


def _sorties_sans_console() -> None:
    """Exe sans console (fenêtre seule) : sys.stdout vaut None ; les messages vont dans le journal."""
    if sys.stdout is None or sys.stderr is None:
        logs_dir().mkdir(parents=True, exist_ok=True)
        journal = open(logs_dir() / "studiodock.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or journal
        sys.stderr = sys.stderr or journal


def _deja_lance(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{HOTE}:{port}/health", timeout=1) as r:
            return json.loads(r.read()).get("app") == APP_ID
    except (OSError, ValueError):
        return False


def _port_libre(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOTE, port)) != 0


def _port_disponible(souhaite: int) -> int:
    if _port_libre(souhaite):
        return souhaite
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOTE, 0))
        return s.getsockname()[1]


def main(argv: list[str] | None = None) -> None:
    _sorties_sans_console()
    parser = argparse.ArgumentParser(prog="StudioDock", description=APP_NAME)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port de l'interface (défaut {DEFAULT_PORT})")
    parser.add_argument("--browser", action="store_true", help="interface dans le navigateur au lieu d'une fenêtre")
    parser.add_argument("--no-window", action="store_true", help="serveur seul, sans fenêtre ni navigateur (tests)")
    parser.add_argument("--home", help="dossier de Studio Dock (apps.json, apps\\) ; défaut : celui de l'exe")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    parser.add_argument("--check-window", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--after-update", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.home:
        os.environ["STUDIODOCK_HOME"] = str(Path(args.home).resolve())

    from app import miseajour, winapi

    if args.after_update:
        # Redémarrage après mise à jour : l'ancienne version libère le port en quittant
        for _ in range(100):
            if not _deja_lance(args.port):
                break
            time.sleep(0.2)
    miseajour.nettoyer_ancienne_version()

    if _deja_lance(args.port) and not args.no_window:
        # Un seul Studio Dock à la fois : on rouvre l'interface de celui qui tourne
        winapi.ouvrir(f"http://{HOTE}:{args.port}")
        return
    port = _port_disponible(args.port)
    url = f"http://{HOTE}:{port}"
    winapi.rattacher_au_groupe()

    import uvicorn

    from app.main import app, pilote

    serveur = uvicorn.Server(uvicorn.Config(app, host=HOTE, port=port, log_level="warning", log_config=None))
    print(f"{APP_NAME} {VERSION} sur {url}")

    def _arreter() -> None:
        pilote.tout_arreter()
        serveur.should_exit = True

    fenetre = not (args.browser or args.no_window)
    webview = None
    if fenetre:
        try:
            import webview  # pywebview
        except Exception as e:  # noqa: BLE001 : pas de fenêtre possible, repli sur le navigateur
            print(f"Fenêtre indisponible ({e}) : ouverture dans le navigateur.")
            fenetre = False

    if not fenetre:
        if args.browser or webview is None and not args.no_window:
            threading.Thread(target=_ouvrir_quand_pret, args=(url, port), daemon=True).start()
        # uvicorn relance le signal reçu après s'être arrêté : SIGTERM doit alors passer par « finally »
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
        try:
            serveur.run()
        finally:
            pilote.tout_arreter()
        return

    fil = threading.Thread(target=serveur.run, daemon=True)
    fil.start()
    for _ in range(100):
        if serveur.started:
            break
        time.sleep(0.1)
    window = webview.create_window(APP_NAME, url, width=1240, height=860, min_size=(760, 560))

    def _choisir_dossier() -> str | None:
        dossier = getattr(getattr(webview, "FileDialog", None), "FOLDER", None) or webview.FOLDER_DIALOG
        choix = window.create_file_dialog(dossier)
        return str(choix[0]) if choix else None

    import app.main as module_api

    module_api.choisir_dossier = _choisir_dossier
    if args.check_window:
        # Vérification du workflow : la fenêtre s'ouvre, charge l'interface, puis se ferme
        window.events.loaded += lambda: threading.Timer(2, window.destroy).start()
    try:
        webview.start()
    except Exception as e:  # noqa: BLE001 : WebView2 absent ou bloqué
        print(f"Fenêtre impossible : {e}")
        if args.check_window:
            _arreter()
            sys.exit(3)
        # Repli : l'interface s'ouvre dans le navigateur ; fermer le message arrête Studio Dock
        winapi.ouvrir(url)
        winapi.message(APP_NAME, "La fenêtre de Studio Dock n'a pas pu s'ouvrir : l'interface est affichée dans "
                                 "votre navigateur.\n\nGardez ce message ouvert pendant l'utilisation ; "
                                 "fermez-le pour arrêter Studio Dock et les applications lancées.")
    finally:
        _arreter()
        fil.join(timeout=5)


def _ouvrir_quand_pret(url: str, port: int) -> None:
    from app import winapi

    for _ in range(100):
        if _deja_lance(port):
            winapi.ouvrir(url)
            return
        time.sleep(0.2)


if __name__ == "__main__":
    main()
