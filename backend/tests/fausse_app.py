"""Fausse app web pour les tests : respecte le contrat commun (--port, --no-browser, /health, code 2).

Son identifiant est le nom de son dossier (apps/<id>/...). FAUSSE_APP_PLANTE=1 : s'arrête en erreur.
"""
import json
import os
import socket
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

APP_ID = Path(__file__).resolve().parent.name
port = int(sys.argv[sys.argv.index("--port") + 1])

if (Path(__file__).resolve().parent / "plante").exists():
    print("Erreur de démarrage simulée")
    sys.exit(1)

with socket.socket() as s:
    if s.connect_ex(("127.0.0.1", port)) == 0:
        print(f"port {port} pris")
        sys.exit(2)


class Sante(BaseHTTPRequestHandler):
    def do_GET(self):
        corps = json.dumps({"status": "ok", "app": APP_ID, "name": APP_ID, "version": "9.9.9"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *args):
        pass


HTTPServer(("127.0.0.1", port), Sante).serve_forever()
