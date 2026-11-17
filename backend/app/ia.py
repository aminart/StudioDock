"""Modèles d'IA communs à la suite : connexions réglées une fois dans Studio Dock, utilisées par toutes les apps.

Même modèle que l'écran Réglages de DocAnalyser :
- une connexion est un service compatible OpenAI (passerelle interne, vLLM, Mistral, Ollama, LM Studio…) :
  un nom, une adresse, une clé facultative, un certificat facultatif et sa liste de modèles, avec la fenêtre de
  contexte et la longueur maximale de réponse ;
- la clé est chiffrée avec le compte Windows (DPAPI) : seul ce compte, sur ce poste, peut la relire. Les apps
  tournent sous le même compte et la déchiffrent elles-mêmes ; elle n'est jamais renvoyée à l'interface ;
- le certificat (.crt, PEM ou DER) est copié dans certificats/<id>.crt.

En plus, Studio Dock choisit le modèle utilisé par défaut, et éventuellement un modèle par app ; une app peut
aussi garder sa configuration propre.

Fichier lu par les apps (format 1), dans le dossier « ia » :
    connexions.json   {"format": 1, "connections": [...], "default": {"connection", "model"} | null,
                       "apps": {"<id>": {"connection", "model"} | {"own": true}}}
    certificats/<id>.crt
Emplacement : variable STUDIODOCK_IA (donnée par Studio Dock aux apps qu'il lance), sinon
%LOCALAPPDATA%\\StudioDock\\ia (Windows), ~/Library/Application Support/StudioDock/ia (Mac).
Les apps le lisent avec studiodock_ia.py (même fichier dans chaque dépôt).
"""
from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.info import config_dir

FORMAT = 1
FICHIER = "connexions.json"
CONTEXTE_DEFAUT = 128_000
CONTEXTE_OLLAMA = 4096  # contexte réglé par défaut dans Ollama, plus court que celui des modèles
_VERROU = threading.Lock()


def dossier() -> Path:
    if autre := os.environ.get("STUDIODOCK_IA", "").strip():
        return Path(autre).expanduser()
    return config_dir() / "ia"


def _fichier() -> Path:
    return dossier() / FICHIER


def chemin_certificat(id_: str) -> Path:
    return dossier() / "certificats" / f"{id_}.crt"


@dataclass
class Connexion:
    id: str
    name: str
    kind: str = "openai"  # protocole : compatible OpenAI (comme les connexions de DocAnalyser)
    provider: str = "openai"  # « openai » : service en ligne ou d'entreprise ; « ollama » : modèles sur ce poste
    api_base: str = ""
    api_key: dict[str, str] | None = None  # chiffrée
    certificate: dict[str, str] | None = None  # nom, date d'import, date d'expiration
    models: list[str] = field(default_factory=list)
    context_tokens: int = CONTEXTE_DEFAUT
    max_output_tokens: int = 0  # 0 : valeur par défaut du serveur
    last_test: dict[str, Any] | None = None


# --- Chiffrement de la clé (même code que DocAnalyser, SpecGen et AuditErgo) ---------------------------

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _dpapi(donnees: bytes, chiffrer: bool) -> bytes:
        tampon = ctypes.create_string_buffer(donnees, len(donnees))
        entree = _Blob(len(donnees), ctypes.cast(tampon, ctypes.POINTER(ctypes.c_char)))
        sortie = _Blob()
        if chiffrer:
            ok = ctypes.windll.crypt32.CryptProtectData(ctypes.byref(entree), "StudioDock", None, None, None, 0,
                                                        ctypes.byref(sortie))
        else:
            ok = ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(entree), None, None, None, None, 0,
                                                          ctypes.byref(sortie))
        if not ok:
            raise ctypes.WinError()
        try:
            return ctypes.string_at(sortie.pbData, sortie.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(sortie.pbData)

    def chiffrer(valeur: str) -> dict[str, str]:
        return {"scheme": "dpapi", "data": base64.b64encode(_dpapi(valeur.encode("utf-8"), True)).decode("ascii")}

else:
    # Mac et développement : pas de coffre du système branché (comme les apps), la clé est seulement encodée.
    def chiffrer(valeur: str) -> dict[str, str]:
        return {"scheme": "plain", "data": base64.b64encode(valeur.encode("utf-8")).decode("ascii")}


def dechiffrer(stocke: dict[str, str] | None) -> str:
    if not stocke:
        return ""
    try:
        brut = base64.b64decode(stocke["data"])
        if stocke.get("scheme") == "dpapi":
            return _dpapi(brut, False).decode("utf-8") if sys.platform == "win32" else ""
        return brut.decode("utf-8")
    except (OSError, ValueError, KeyError):
        return ""  # chiffrée par un autre compte Windows, ou illisible : considérée comme absente


# --- Lecture et écriture --------------------------------------------------------------------------------

def _lire() -> dict[str, Any]:
    try:
        brut = json.loads(_fichier().read_text(encoding="utf-8"))
        return brut if isinstance(brut, dict) else {}
    except (OSError, ValueError):
        return {}


def _connexions(brut: dict[str, Any]) -> list[Connexion]:
    sortie = []
    for c in brut.get("connections", []) or []:
        if not isinstance(c, dict):
            continue
        try:
            sortie.append(Connexion(**{k: v for k, v in c.items() if k in Connexion.__dataclass_fields__}))
        except TypeError:
            continue
    return sortie


def _ecrire(connexions: list[Connexion], defaut: dict | None, apps: dict[str, dict]) -> None:
    """Écriture atomique : une app qui lit le fichier au même moment voit l'ancien ou le nouveau, jamais un morceau."""
    dossier().mkdir(parents=True, exist_ok=True)
    texte = json.dumps({"format": FORMAT, "connections": [asdict(c) for c in connexions], "default": defaut,
                        "apps": apps}, ensure_ascii=False, indent=2)
    temporaire = _fichier().with_suffix(".json.part")
    temporaire.write_text(texte, encoding="utf-8")
    os.replace(temporaire, _fichier())


def lire() -> tuple[list[Connexion], dict | None, dict[str, dict]]:
    brut = _lire()
    defaut = brut.get("default") if isinstance(brut.get("default"), dict) else None
    apps = brut.get("apps") if isinstance(brut.get("apps"), dict) else {}
    return _connexions(brut), defaut, apps


def lister() -> list[Connexion]:
    return lire()[0]


def trouver(id_: str) -> Connexion | None:
    return next((c for c in lister() if c.id == id_), None)


def cle(c: Connexion) -> str:
    return dechiffrer(c.api_key)


def certificat(c: Connexion) -> str:
    chemin = chemin_certificat(c.id)
    return str(chemin) if c.certificate and chemin.is_file() else ""


def nettoyer_modeles(modeles: list[str]) -> list[str]:
    vus, sortie = set(), []
    for m in modeles:
        m = m.strip()
        if m and m not in vus:
            vus.add(m)
            sortie.append(m)
    return sortie


def _choix_valide(choix: Any, connexions: list[Connexion]) -> dict | None:
    """Garde un choix {connection, model} seulement s'il désigne une connexion et un modèle existants."""
    if not isinstance(choix, dict):
        return None
    if choix.get("own") is True:
        return {"own": True}
    c = next((c for c in connexions if c.id == choix.get("connection")), None)
    if c is None or choix.get("model") not in c.models:
        return None
    return {"connection": c.id, "model": choix["model"]}


def _reparer(connexions: list[Connexion], defaut: dict | None, apps: dict[str, dict]) -> tuple[dict | None, dict]:
    """Après une modification : retire les choix devenus invalides ; sans modèle par défaut, prend le premier."""
    defaut = _choix_valide(defaut, connexions)
    if defaut is not None and defaut.get("own"):
        defaut = None
    apps = {k: v for k, v in ((k, _choix_valide(v, connexions)) for k, v in apps.items()) if v is not None}
    if defaut is None:
        premiere = next((c for c in connexions if c.models), None)
        if premiere is not None:
            defaut = {"connection": premiere.id, "model": premiere.models[0]}
    return defaut, apps


def enregistrer(c: Connexion, api_key: str | None) -> Connexion:
    """Ajoute ou remplace la connexion `c`. `api_key` None garde la clé enregistrée ; une chaîne vide l'efface."""
    with _VERROU:
        connexions, defaut, apps = lire()
        ancienne = next((x for x in connexions if x.id == c.id), None)
        if api_key is not None:
            c.api_key = chiffrer(api_key.strip()) if api_key.strip() else None
        elif ancienne is not None:
            c.api_key = ancienne.api_key
        if ancienne is not None:
            c.certificate = ancienne.certificate
            if c.last_test is None and ancienne.api_base == c.api_base:
                c.last_test = ancienne.last_test
            connexions = [c if x.id == c.id else x for x in connexions]
        else:
            connexions.append(c)
        defaut, apps = _reparer(connexions, defaut, apps)
        _ecrire(connexions, defaut, apps)
        return c


def nouvelle(name: str, api_base: str, models: list[str], context_tokens: int | None, max_output_tokens: int = 0,
             provider: str = "openai", id_: str | None = None, last_test: dict | None = None) -> Connexion:
    return Connexion(
        id=id_ or f"sd{uuid.uuid4().hex[:8]}",
        name=name.strip() or ("Ollama (ce poste)" if provider == "ollama" else "Service d'IA"),
        provider=provider, api_base=api_base.strip().rstrip("/"), models=nettoyer_modeles(models),
        context_tokens=context_tokens or (CONTEXTE_OLLAMA if provider == "ollama" else CONTEXTE_DEFAUT),
        max_output_tokens=max_output_tokens, last_test=last_test,
    )


def supprimer(id_: str) -> None:
    with _VERROU:
        connexions, defaut, apps = lire()
        connexions = [c for c in connexions if c.id != id_]
        defaut, apps = _reparer(connexions, defaut, apps)
        _ecrire(connexions, defaut, apps)
        chemin_certificat(id_).unlink(missing_ok=True)


def choisir(defaut: dict | None, apps: dict[str, dict]) -> None:
    """Modèle par défaut et choix de chaque app ({connection, model}, {own: true}, ou absent : le défaut)."""
    with _VERROU:
        connexions, _, _ = lire()
        defaut, apps = _reparer(connexions, defaut, apps)
        _ecrire(connexions, defaut, apps)


def enregistrer_test(id_: str, resultat: dict[str, Any]) -> None:
    with _VERROU:
        connexions, defaut, apps = lire()
        for c in connexions:
            if c.id == id_:
                c.last_test = resultat
                _ecrire(connexions, defaut, apps)
                return


# --- Certificat de l'entreprise ----------------------------------------------------------------------------

def lire_certificat(contenu: bytes) -> tuple[bytes, str | None]:
    """Vérifie un .crt (PEM ou DER, éventuellement une chaîne) ; renvoie (PEM, date d'expiration la plus proche).

    Sans dépendance : le module ssl charge le certificat (refus s'il est invalide) et lit sa date d'expiration.
    """
    texte = contenu.decode("ascii", errors="ignore")
    if "-----BEGIN CERTIFICATE-----" in texte:
        blocs = ["-----BEGIN CERTIFICATE-----" + b.split("-----END CERTIFICATE-----")[0] + "-----END CERTIFICATE-----\n"
                 for b in texte.split("-----BEGIN CERTIFICATE-----")[1:]]
    else:
        try:
            blocs = [ssl.DER_cert_to_PEM_cert(contenu)]
        except ValueError:
            blocs = []
    erreur = ValueError("Ce fichier n'est pas un certificat valide (.crt au format PEM ou DER attendu).")
    if not blocs:
        raise erreur
    pem = "".join(blocs)
    try:
        ssl.create_default_context().load_verify_locations(cadata=pem)
    except (ssl.SSLError, ValueError) as e:
        raise erreur from e
    expirations = []
    for bloc in blocs:
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
            f.write(bloc)
        try:
            infos = ssl._ssl._test_decode_cert(f.name)  # type: ignore[attr-defined]  # noqa: SLF001
            expirations.append(datetime.strptime(infos["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc))
        except (AttributeError, KeyError, ValueError, ssl.SSLError):
            pass
        finally:
            Path(f.name).unlink(missing_ok=True)
    return pem.encode("ascii"), (min(expirations).isoformat() if expirations else None)


def importer_certificat(id_: str, nom: str, contenu: bytes) -> Connexion:
    pem, expiration = lire_certificat(contenu)
    with _VERROU:
        connexions, defaut, apps = lire()
        c = next((c for c in connexions if c.id == id_), None)
        if c is None:
            raise KeyError(id_)
        chemin = chemin_certificat(id_)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_bytes(pem)
        c.certificate = {"name": nom, "imported_at": datetime.now(timezone.utc).isoformat(), "expires_at": expiration}
        c.last_test = None
        _ecrire(connexions, defaut, apps)
        return c


def retirer_certificat(id_: str) -> Connexion:
    with _VERROU:
        connexions, defaut, apps = lire()
        c = next((c for c in connexions if c.id == id_), None)
        if c is None:
            raise KeyError(id_)
        c.certificate = None
        chemin_certificat(id_).unlink(missing_ok=True)
        _ecrire(connexions, defaut, apps)
        return c


def verification(ca: str) -> ssl.SSLContext | bool:
    """Certificats du système, ou l'autorité fournie (certificat d'entreprise), comme DocAnalyser :
    sans la vérification X.509 « stricte » de Python 3.13 qui refuse des autorités internes courantes."""
    if not ca:
        return True
    contexte = ssl.create_default_context(cafile=ca)
    contexte.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return contexte
