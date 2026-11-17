"""Réglages › Modèles d'IA : connexions communes aux apps, modèles locaux (Ollama), modèle de chaque app.

GET    /api/ia                          connexions (jamais la clé), choix par défaut et par app, apps avec IA
POST   /api/ia/connections              ajouter une connexion ; PUT /api/ia/connections/{id} pour la modifier
DELETE /api/ia/connections/{id}         supprimer
POST   /api/ia/connections/{id}/certificate   importer le certificat (.crt, en base64) ; DELETE pour le retirer
POST   /api/ia/test                     tester les valeurs saisies, avant d'enregistrer
PUT    /api/ia/choices                  modèle par défaut et modèle de chaque app
GET    /api/ia/ollama                   Ollama démarré ? modèles installés, téléchargements en cours
POST   /api/ia/ollama/pull              télécharger un modèle ; PUT /api/ia/ollama pour proposer des modèles aux apps
"""
from __future__ import annotations

import asyncio
import base64
import ssl
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import ia, ollama

router = APIRouter(prefix="/api/ia")
DELAI_TEST = 30.0
# Apps du catalogue qui utilisent l'IA (id, nom, icône) ; fourni par main.py
apps_ia: Callable[[], list[dict[str, Any]]] = lambda: []  # noqa: E731


class ConnexionForm(BaseModel):
    name: str = ""
    api_base: str = ""
    api_key: str | None = None  # None : garder la clé enregistrée ; vide : l'effacer
    models: list[str] = Field(default_factory=list)
    context_tokens: int | None = Field(default=None, ge=1000, le=10_000_000)
    max_output_tokens: int = Field(default=0, ge=0, le=1_000_000)
    last_test: dict[str, Any] | None = None  # test fait sur ces valeurs avant d'enregistrer


class TestForm(ConnexionForm):
    id: str | None = None  # connexion enregistrée : sa clé et son certificat servent si rien d'autre n'est fourni
    certificate_b64: str | None = None  # certificat choisi mais pas encore enregistré


class Certificat(BaseModel):
    name: str = "certificat.crt"
    data: str  # contenu du fichier, en base64


class Choix(BaseModel):
    default: dict[str, Any] | None = None
    apps: dict[str, dict[str, Any]] = Field(default_factory=dict)


class OllamaForm(BaseModel):
    address: str = ollama.ADRESSE
    models: list[str] = Field(default_factory=list)
    context_tokens: int | None = Field(default=None, ge=1000, le=10_000_000)


class Pull(BaseModel):
    model: str
    address: str = ollama.ADRESSE


# --- Représentation pour l'interface (jamais la clé) -------------------------------------------------------

def _indice(cle: str) -> str:
    return cle[-4:] if len(cle) >= 8 else ""


def _publique(c: ia.Connexion) -> dict[str, Any]:
    cle = ia.cle(c)
    return {
        "id": c.id, "name": c.name, "provider": c.provider, "api_base": c.api_base,
        "has_api_key": bool(cle), "api_key_hint": _indice(cle),
        "certificate": c.certificate if ia.certificat(c) else None,
        "models": c.models, "context_tokens": c.context_tokens, "max_output_tokens": c.max_output_tokens,
        "last_test": c.last_test,
    }


def _tout() -> dict[str, Any]:
    connexions, defaut, apps = ia.lire()
    return {
        "connections": [_publique(c) for c in connexions],
        "default": defaut,
        "apps": [{**a, "choice": apps.get(a["id"])} for a in apps_ia()],
        "folder": str(ia.dossier()),
    }


def _verifier_adresse(adresse: str) -> None:
    if not adresse.strip().lower().startswith(("http://", "https://")):
        raise HTTPException(422, "Renseignez l'adresse du service (http:// ou https://).")


# --- Connexions --------------------------------------------------------------------------------------------

@router.get("")
async def lister() -> dict[str, Any]:
    return await asyncio.to_thread(_tout)


@router.post("/connections")
async def creer(form: ConnexionForm) -> dict[str, Any]:
    _verifier_adresse(form.api_base)
    c = ia.nouvelle(form.name, form.api_base, form.models, form.context_tokens, form.max_output_tokens,
                    last_test=form.last_test)
    ia.enregistrer(c, form.api_key)
    return {**_tout(), "created": c.id}


@router.put("/connections/{id_}")
async def modifier(id_: str, form: ConnexionForm) -> dict[str, Any]:
    _verifier_adresse(form.api_base)
    ancienne = ia.trouver(id_)
    if ancienne is None:
        raise HTTPException(404, "Connexion introuvable.")
    c = ia.nouvelle(form.name, form.api_base, form.models, form.context_tokens, form.max_output_tokens,
                    provider=ancienne.provider, id_=id_, last_test=form.last_test)
    ia.enregistrer(c, form.api_key)
    return _tout()


@router.delete("/connections/{id_}")
async def supprimer(id_: str) -> dict[str, Any]:
    ia.supprimer(id_)
    return _tout()


@router.post("/connections/{id_}/certificate")
async def importer_certificat(id_: str, corps: Certificat) -> dict[str, Any]:
    try:
        ia.importer_certificat(id_, corps.name, base64.b64decode(corps.data))
    except KeyError as e:
        raise HTTPException(404, "Connexion introuvable.") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return _tout()


@router.delete("/connections/{id_}/certificate")
async def retirer_certificat(id_: str) -> dict[str, Any]:
    try:
        ia.retirer_certificat(id_)
    except KeyError as e:
        raise HTTPException(404, "Connexion introuvable.") from e
    return _tout()


@router.put("/choices")
async def choisir(corps: Choix) -> dict[str, Any]:
    ia.choisir(corps.default, corps.apps)
    return _tout()


# --- Test de connexion (même diagnostic que DocAnalyser) ---------------------------------------------------

def _echec(champ: str | None, titre: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "field": champ, "title": titre, "message": message, **extra}


def _certificat_refuse(exc: BaseException) -> bool:
    courante: BaseException | None = exc
    while courante is not None:
        if isinstance(courante, ssl.SSLError) or "CERTIFICATE_VERIFY_FAILED" in str(courante):
            return True
        courante = courante.__cause__ or courante.__context__
    return False


class _Refus(Exception):
    def __init__(self, statut: int, texte: str):
        super().__init__(texte)
        self.statut = statut


def _diagnostic(exc: Exception, base: str) -> dict[str, Any]:
    if _certificat_refuse(exc):
        return _echec("certificate", "Échec de la connexion : certificat non reconnu",
                      "Le serveur a été joint, mais la connexion sécurisée a été refusée. Importez le certificat (.crt) de "
                      "l'autorité qui a signé celui du serveur, fourni par votre service informatique.")
    if isinstance(exc, httpx.TimeoutException):
        return _echec("api_base", "Échec de la connexion : délai dépassé",
                      "Le service n'a pas répondu à temps. Vérifiez l'adresse et votre accès au réseau.")
    if isinstance(exc, _Refus) and exc.statut in (401, 403):
        return _echec("api_key", "Échec de la connexion : clé API refusée",
                      "Le service a refusé la clé API. Vérifiez qu'elle a été copiée en entier et qu'elle est toujours valide.")
    if isinstance(exc, _Refus) and exc.statut == 404:
        return _echec("models", "Échec de la connexion : adresse ou modèle introuvable",
                      "Le service répond, mais l'adresse ou le modèle demandé n'existe pas. Vérifiez l'adresse (elle se "
                      f"termine souvent par /v1) et le nom du modèle. Détail : {str(exc)[:300]}")
    if isinstance(exc, _Refus):
        return _echec(None, f"Échec de la connexion : erreur {exc.statut}", str(exc)[:500])
    if isinstance(exc, httpx.HTTPError):
        return _echec("api_base", "Échec de la connexion : serveur injoignable",
                      f"Aucune réponse de {base}. Vérifiez l'adresse et votre accès au réseau (VPN). Détail : {exc}")
    return _echec(None, "Échec de la connexion", f"{type(exc).__name__} : {exc}")


def _client(ca: str, base: str) -> httpx.AsyncClient:
    local = any(h in base for h in ("://localhost", "://127.0.0.1", "://[::1]"))
    # Service sur ce poste (Ollama, LM Studio) : jamais par le proxy de l'entreprise
    return httpx.AsyncClient(verify=ia.verification(ca), timeout=httpx.Timeout(DELAI_TEST, connect=15.0),
                             trust_env=not local)


async def _modeles_du_serveur(base: str, cle: str, ca: str) -> list[str] | None:
    """Modèles listés par le serveur (GET /models), ou None s'il ne les liste pas. Lève les erreurs réseau."""
    entetes = {"Authorization": f"Bearer {cle}"} if cle else {}
    async with _client(ca, base) as client:
        reponse = await client.get(base.rstrip("/") + "/models", headers=entetes)
    if reponse.status_code in (401, 403):
        raise _Refus(reponse.status_code, reponse.text[:300])
    if reponse.status_code >= 400:
        return None  # passerelle sans /models (404, 405, 501…)
    try:
        donnees = reponse.json().get("data", [])
        return sorted({str(m.get("id")) for m in donnees if isinstance(m, dict) and m.get("id")})
    except (ValueError, AttributeError):
        return None


async def _ping(base: str, cle: str, ca: str, modele: str) -> None:
    entetes = {"Authorization": f"Bearer {cle}"} if cle else {}
    async with _client(ca, base) as client:
        reponse = await client.post(base.rstrip("/") + "/chat/completions", headers=entetes, json={
            "model": modele, "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]})
    if reponse.status_code >= 400:
        raise _Refus(reponse.status_code, reponse.text[:500])


async def tester_valeurs(base: str, cle: str, ca: str, modeles: list[str]) -> dict[str, Any]:
    try:
        disponibles = await _modeles_du_serveur(base, cle, ca)
    except Exception as e:  # noqa: BLE001 : diagnostiqué
        return _diagnostic(e, base)

    if disponibles is not None:
        # Ollama nomme les modèles « nom:étiquette » ; « mistral-small » désigne « mistral-small:latest »
        def present(m: str) -> bool:
            return any(d == m or d.split(":")[0] == m or d.endswith("/" + m) for d in disponibles)

        absents = [m for m in modeles if not present(m)]
        if modeles and len(absents) == len(modeles):
            return _echec("models", "Aucun des modèles indiqués n'est proposé par le serveur",
                          f"Introuvables : {', '.join(absents)}. Choisissez parmi les modèles disponibles.",
                          available=disponibles)
        message = f"{len(disponibles)} modèle(s) proposé(s) par le serveur"
        if absents:
            message += f" ; introuvable(s) : {', '.join(absents)}"
        return {"ok": True, "field": "models" if absents else None, "title": "Connexion opérationnelle",
                "message": message, "available": disponibles, "missing": absents}

    # Pas de liste : un petit appel au premier modèle vérifie l'adresse, la clé et le nom du modèle.
    if not modeles:
        return _echec("models", "Indiquez au moins un modèle",
                      "Ce serveur ne liste pas ses modèles : renseignez le nom d'un modèle pour tester la connexion.")
    try:
        await _ping(base, cle, ca, modeles[0])
    except Exception as e:  # noqa: BLE001 : diagnostiqué
        return _diagnostic(e, base)
    return {"ok": True, "field": None, "title": "Connexion opérationnelle", "message": f"modèle {modeles[0]}",
            "available": None, "missing": []}


@router.post("/test")
async def tester(form: TestForm) -> dict[str, Any]:
    maintenant = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731
    enregistree = ia.trouver(form.id) if form.id else None
    base = form.api_base.strip().rstrip("/")
    if not base.lower().startswith(("http://", "https://")):
        return {**_echec("api_base", "Adresse invalide", "Renseignez l'adresse du service (http:// ou https://)."),
                "at": maintenant()}
    if form.api_key is None and enregistree and enregistree.api_base and base != enregistree.api_base \
            and ia.cle(enregistree):
        # La clé enregistrée ne part que vers l'adresse pour laquelle elle a été saisie
        return {**_echec("api_key", "Saisissez à nouveau la clé API",
                         "L'adresse du service a changé : par sécurité, la clé enregistrée n'est pas envoyée à la "
                         "nouvelle adresse. Saisissez la clé pour tester."), "at": maintenant()}
    cle = form.api_key.strip() if form.api_key is not None else (ia.cle(enregistree) if enregistree else "")

    temporaire = None
    try:
        if form.certificate_b64:
            try:
                pem, _ = ia.lire_certificat(base64.b64decode(form.certificate_b64))
            except ValueError as e:
                return {**_echec("certificate", "Certificat invalide", str(e)), "at": maintenant()}
            temporaire = tempfile.NamedTemporaryFile(suffix=".crt", delete=False)
            temporaire.write(pem)
            temporaire.close()
            ca = temporaire.name
        else:
            ca = ia.certificat(enregistree) if enregistree else ""
        resultat = await tester_valeurs(base, cle, ca, ia.nettoyer_modeles(form.models))
    finally:
        if temporaire:
            Path(temporaire.name).unlink(missing_ok=True)

    resultat["at"] = maintenant()
    if enregistree:
        ia.enregistrer_test(enregistree.id, resultat)
    return resultat


# --- Ollama ------------------------------------------------------------------------------------------------

def _connexion_ollama() -> ia.Connexion | None:
    return next((c for c in ia.lister() if c.provider == "ollama"), None)


def _etat_ollama(adresse: str | None) -> dict[str, Any]:
    c = _connexion_ollama()
    adresse = adresse or (ollama.racine(c.api_base) if c else ollama.ADRESSE)
    return {**ollama.etat(adresse), "connection": _publique(c) if c else None}


@router.get("/ollama")
async def etat_ollama(address: str | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(_etat_ollama, address)


@router.post("/ollama/pull")
async def telecharger(corps: Pull) -> dict[str, Any]:
    try:
        ollama.telecharger(corps.model, corps.address)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return await asyncio.to_thread(_etat_ollama, corps.address)


@router.put("/ollama")
async def proposer(corps: OllamaForm) -> dict[str, Any]:
    """Modèles d'Ollama proposés aux apps : une seule connexion « Ollama (ce poste) », créée au premier choix,
    supprimée quand plus aucun modèle n'est proposé."""
    _verifier_adresse(corps.address)
    c = _connexion_ollama()
    modeles = ia.nettoyer_modeles(corps.models)
    if not modeles:
        if c is not None:
            ia.supprimer(c.id)
    else:
        nouvelle = ia.nouvelle(c.name if c else "Ollama (ce poste)", ollama.base_openai(corps.address), modeles,
                               corps.context_tokens or (c.context_tokens if c else None), provider="ollama",
                               id_=c.id if c else None)
        ia.enregistrer(nouvelle, None)
    return {**_tout(), "ollama": await asyncio.to_thread(_etat_ollama, corps.address)}
