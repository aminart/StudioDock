"""Modèles locaux avec Ollama : détection, modèles installés, téléchargement d'un modèle.

Ollama tourne sur le poste (http://localhost:11434) et expose aussi une API compatible OpenAI (…/v1) : les apps
s'en servent comme de n'importe quelle autre connexion, sans clé ni certificat.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

import httpx

ADRESSE = "http://localhost:11434"
_VERROU = threading.Lock()
_telechargements: dict[str, dict[str, Any]] = {}  # modèle -> {status, completed, total, error, done}


def racine(adresse: str | None) -> str:
    """Adresse du serveur Ollama sans « /v1 » ni barre finale."""
    base = (adresse or ADRESSE).strip().rstrip("/")
    return base[:-3] if base.endswith("/v1") else base


def base_openai(adresse: str | None) -> str:
    return racine(adresse) + "/v1"


def _taille(octets: int | None) -> str:
    if not octets:
        return ""
    return f"{octets / 1e9:.1f} Go" if octets >= 1e9 else f"{octets / 1e6:.0f} Mo"


def etat(adresse: str | None = None) -> dict[str, Any]:
    """Ollama démarré ? Sa version et ses modèles installés, avec les téléchargements en cours."""
    base = racine(adresse)
    sortie: dict[str, Any] = {"address": base, "running": False, "version": None, "models": [],
                              "pulls": _suivi()}
    try:
        with httpx.Client(timeout=httpx.Timeout(3.0, connect=1.5), trust_env=False) as client:
            version = client.get(base + "/api/version")
            version.raise_for_status()
            sortie["running"] = True
            sortie["version"] = version.json().get("version")
            tags = client.get(base + "/api/tags")
            tags.raise_for_status()
            modeles = tags.json().get("models", []) or []
    except (httpx.HTTPError, ValueError):
        return sortie
    for m in modeles:
        details = m.get("details") or {}
        sortie["models"].append({
            "name": m.get("name") or m.get("model"),
            "size": _taille(m.get("size")),
            "parameters": details.get("parameter_size") or "",
            "quantization": details.get("quantization_level") or "",
            "family": details.get("family") or "",
        })
    sortie["models"].sort(key=lambda m: m["name"] or "")
    return sortie


def contexte_max(modele: str, adresse: str | None = None) -> int | None:
    """Fenêtre de contexte maximale du modèle (indicative : Ollama en utilise une plus courte par défaut)."""
    try:
        with httpx.Client(timeout=5.0, trust_env=False) as client:
            r = client.post(racine(adresse) + "/api/show", json={"model": modele})
            r.raise_for_status()
            infos = r.json().get("model_info") or {}
    except (httpx.HTTPError, ValueError):
        return None
    valeurs = [v for k, v in infos.items() if k.endswith(".context_length") and isinstance(v, int)]
    return max(valeurs) if valeurs else None


def _suivi() -> list[dict[str, Any]]:
    with _VERROU:
        # Les téléchargements finis restent affichés une minute
        maintenant = time.monotonic()
        for nom in [n for n, t in _telechargements.items() if t.get("done") and maintenant - t["done"] > 60]:
            del _telechargements[nom]
        return [{"model": nom, **{k: v for k, v in t.items() if k != "done"}, "finished": bool(t.get("done"))}
                for nom, t in _telechargements.items()]


def telecharger(modele: str, adresse: str | None = None) -> None:
    """Lance `ollama pull <modele>` en arrière-plan ; l'avancement est renvoyé par etat()."""
    modele = modele.strip()
    if not modele:
        raise ValueError("Indiquez le nom du modèle, par exemple mistral-small ou llama3.2.")
    with _VERROU:
        en_cours = _telechargements.get(modele)
        if en_cours and not en_cours.get("done"):
            return
        _telechargements[modele] = {"status": "Démarrage…", "completed": 0, "total": 0, "error": None}
    threading.Thread(target=_tirer, args=(modele, racine(adresse)), daemon=True).start()


def _maj(modele: str, **valeurs: Any) -> None:
    with _VERROU:
        if modele in _telechargements:
            _telechargements[modele].update(valeurs)


def _tirer(modele: str, base: str) -> None:
    try:
        with httpx.Client(timeout=httpx.Timeout(None, connect=5.0), trust_env=False) as client:
            with client.stream("POST", base + "/api/pull", json={"model": modele, "stream": True}) as reponse:
                if reponse.status_code >= 400:
                    reponse.read()
                    raise RuntimeError(_message(reponse.text) or f"erreur {reponse.status_code}")
                for ligne in reponse.iter_lines():
                    if not ligne.strip():
                        continue
                    try:
                        evenement = json.loads(ligne)
                    except ValueError:
                        continue
                    if evenement.get("error"):
                        raise RuntimeError(evenement["error"])
                    _maj(modele, status=_statut(evenement.get("status", "")),
                         completed=evenement.get("completed") or 0, total=evenement.get("total") or 0)
        _maj(modele, status="Installé", done=time.monotonic())
    except (httpx.HTTPError, RuntimeError) as e:
        texte = str(e)
        if "file does not exist" in texte or "not found" in texte:
            texte = f"Modèle « {modele} » introuvable dans la bibliothèque d'Ollama (ollama.com/library)."
        elif isinstance(e, httpx.ConnectError):
            texte = "Ollama ne répond pas : vérifiez qu'il est démarré."
        _maj(modele, status="Échec", error=texte, done=time.monotonic())


def _message(texte: str) -> str:
    try:
        return str(json.loads(texte).get("error") or "")
    except (ValueError, AttributeError):
        return texte[:300]


def _statut(brut: str) -> str:
    if brut.startswith("pulling manifest"):
        return "Préparation…"
    if brut.startswith("pulling") or brut.startswith("downloading"):
        return "Téléchargement…"
    if brut.startswith("verifying"):
        return "Vérification…"
    if brut.startswith("writing") or brut.startswith("removing"):
        return "Installation…"
    if brut == "success":
        return "Installé"
    return brut or "En cours…"
