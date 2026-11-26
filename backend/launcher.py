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

from app import journal  # noqa: E402
from app.info import APP_ID, APP_NAME, DEFAULT_PORT, VERSION, logs_dir  # noqa: E402

HOTE = "127.0.0.1"


def _sorties_sans_console() -> None:
    """Exe sans console (fenêtre seule) : sys.stdout vaut None ; les messages vont dans le journal."""
    if sys.stdout is None or sys.stderr is None:
        logs_dir().mkdir(parents=True, exist_ok=True)
        sortie = open(logs_dir() / "studiodock.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or sortie
        sys.stderr = sys.stderr or sortie


def _deja_lance(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{HOTE}:{port}/health", timeout=1) as r:
            return json.loads(r.read()).get("app") == APP_ID
    except (OSError, ValueError):
        return False


def _ramener_la_fenetre(port: int) -> bool:
    """Demande au Studio Dock qui tourne de remettre sa fenêtre au premier plan. False s'il n'en a pas."""
    if os.name == "nt":
        try:
            # Ce lancement vient d'un clic de l'utilisateur : il cède le premier plan à l'autre processus
            import ctypes

            ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
        except (AttributeError, OSError):
            pass
    requete = urllib.request.Request(f"http://{HOTE}:{port}/api/window/show", data=b"", method="POST")
    try:
        with urllib.request.urlopen(requete, timeout=5) as r:
            return bool(json.loads(r.read()).get("ok"))
    except (OSError, ValueError):  # 409 (pas de fenêtre), ancienne version sans cette route, délai dépassé
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
    parser.add_argument("--cleanup", help=argparse.SUPPRESS)  # ancien dossier d'installation à vider
    args = parser.parse_args(argv)
    if args.home:
        os.environ["STUDIODOCK_HOME"] = str(Path(args.home).resolve())

    from app import installation, miseajour, winapi

    if installation.a_installer() and not args.after_update and not args.no_window:
        # Exe ouvert hors du dossier d'installation (partage, Téléchargements) alors que Studio Dock est
        # installé : c'est la copie installée qui démarre
        installe = installation.copie_installee()
        if installe is not None:
            winapi.lancer_detache([str(installe), *(argv if argv is not None else sys.argv[1:])], cwd=installe.parent)
            return

    if args.after_update:
        # Redémarrage après mise à jour : l'ancienne version libère le port en quittant
        for _ in range(100):
            if not _deja_lance(args.port):
                break
            time.sleep(0.2)
    miseajour.nettoyer_ancienne_version()
    if args.cleanup:
        threading.Thread(target=_vider_ancien_dossier, args=(Path(args.cleanup),), daemon=True).start()

    if _deja_lance(args.port) and not args.no_window:
        # Un seul Studio Dock à la fois : sa fenêtre revient au premier plan (même réduite) ; le navigateur
        # ne s'ouvre que si celui qui tourne n'a pas de fenêtre (lancé avec --browser, ou repli)
        if args.browser or not _ramener_la_fenetre(args.port):
            winapi.ouvrir(f"http://{HOTE}:{args.port}")
        return
    port = _port_disponible(args.port)
    url = f"http://{HOTE}:{port}"
    winapi.rattacher_au_groupe()
    _journaliser_les_plantages()
    journal.noter(f"Démarrage de {APP_NAME} {VERSION} (port {port}).")

    import uvicorn

    from app.main import app, pilote

    serveur = uvicorn.Server(uvicorn.Config(app, host=HOTE, port=port, log_level="warning", log_config=None))
    print(f"{APP_NAME} {VERSION} sur {url}")

    def _arreter(raison: str = "fenêtre fermée") -> None:
        journal.noter(f"Arrêt de {APP_NAME} : {raison}.")
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
            journal.noter(f"Arrêt de {APP_NAME} (sans fenêtre).")
            pilote.tout_arreter()
        return

    import app.main as module_api

    # Relancé pendant que la fenêtre s'ouvre (double-clic) : rien à faire, elle arrive, pas de navigateur
    module_api.afficher_fenetre = lambda: None
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

    def _afficher() -> None:
        # Réduite ou cachée derrière d'autres fenêtres : elle revient devant
        for etape in (window.restore, window.show):
            try:
                etape()
            except Exception:  # noqa: BLE001 : méthode absente de cette version de pywebview
                pass
        try:
            window.on_top = True
            window.on_top = False
        except Exception:  # noqa: BLE001
            pass

    module_api.choisir_dossier = _choisir_dossier
    module_api.afficher_fenetre = _afficher

    # Fermer la fenêtre arrête les apps web lancées : s'il y en a, l'interface demande d'abord
    # (réduire Studio Dock ou tout fermer). Sans réponse de l'interface, la fenêtre se ferme comme avant.
    fermeture = {"confirmee": False}

    def _fermer() -> None:
        fermeture["confirmee"] = True
        window.destroy()

    def _a_la_fermeture() -> bool:
        if fermeture["confirmee"] or args.check_window or not pilote.apps_ouvertes():
            return True

        def _demander() -> None:
            try:
                prise = window.evaluate_js("window.__studioDockFermeture ? window.__studioDockFermeture() : false")
            except Exception:  # noqa: BLE001 : page pas chargée, moteur occupé
                prise = False
            if not prise:
                _fermer()

        threading.Thread(target=_demander, daemon=True).start()
        return False  # fermeture annulée : la réponse viendra de l'interface

    window.events.closing += _a_la_fermeture
    module_api.reduire_fenetre = window.minimize
    module_api.fermer_fenetre = _fermer
    if args.check_window:
        # Vérification du workflow : la fenêtre s'ouvre, charge l'interface, puis se ferme
        window.events.loaded += lambda: threading.Timer(2, window.destroy).start()
    try:
        webview.start()
    except Exception as e:  # noqa: BLE001 : WebView2 absent ou bloqué
        print(f"Fenêtre impossible : {e}")
        if args.check_window:
            _arreter("vérification de la fenêtre")
            sys.exit(3)
        # Repli : l'interface s'ouvre dans le navigateur ; fermer le message arrête Studio Dock
        winapi.ouvrir(url)
        winapi.message(APP_NAME, "La fenêtre de Studio Dock n'a pas pu s'ouvrir : l'interface est affichée dans "
                                 "votre navigateur.\n\nGardez ce message ouvert pendant l'utilisation ; "
                                 "fermez-le pour arrêter Studio Dock et les applications lancées.")
    finally:
        _arreter()
        fil.join(timeout=5)


_plantages = None  # fichier gardé ouvert : faulthandler y écrit si Studio Dock plante brutalement


def _journaliser_les_plantages() -> None:
    """Erreurs non rattrapées (fil principal ou autre) dans studiodock.log ; plantage brutal (erreur fatale de
    Python) dans plantages.log."""
    global _plantages
    import faulthandler
    import traceback

    def _noter(type_, valeur, trace) -> None:
        journal.noter("Erreur non rattrapée :\n" + "".join(traceback.format_exception(type_, valeur, trace)))

    sys.excepthook = _noter
    threading.excepthook = lambda a: _noter(a.exc_type, a.exc_value, a.exc_traceback)
    try:
        logs_dir().mkdir(parents=True, exist_ok=True)
        _plantages = open(logs_dir() / "plantages.log", "a", encoding="utf-8")  # noqa: SIM115
        faulthandler.enable(_plantages)
    except OSError:
        pass


def _vider_ancien_dossier(ancien: Path) -> None:
    """Après un changement de dossier d'installation : l'ancien exe se libère quand l'ancien Studio Dock quitte."""
    from app import installation
    from app.info import home_dir

    for _ in range(30):
        installation.nettoyer(ancien, home_dir())
        if not (ancien / installation.EXE).exists():
            return
        time.sleep(1)


def _ouvrir_quand_pret(url: str, port: int) -> None:
    from app import winapi

    for _ in range(100):
        if _deja_lance(port):
            winapi.ouvrir(url)
            return
        time.sleep(0.2)


if __name__ == "__main__":
    main()
