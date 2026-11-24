"""App web d'un tiers pour les tests : ni --port ni /health. Écoute le port de FAUSSE_PORT, sinon un port
choisi par le système (comme une app qui prend un port au hasard), et répond « bonjour » partout."""
import http.server
import os
import socketserver


class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"bonjour")

    def log_message(self, *args):
        pass


port = int(os.environ.get("FAUSSE_PORT") or 0)
with socketserver.TCPServer(("127.0.0.1", port), Page) as serveur:
    serveur.serve_forever()
