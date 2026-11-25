"""Éditer le catalogue de l'équipe sans écrire de JSON (Réglages › Préparer pour l'équipe).

Le dossier édité est le dossier partagé de l'équipe (Q:\\Studio Dock…) ou la copie locale du dossier en ligne :
catalogue.json, icons/ et un sous-dossier par app. Chaque enregistrement réécrit catalogue.json en entier, après
validation (identifiants et ports uniques…), de façon atomique, avec une copie de la version précédente
(catalogue.json.bak). Les champs du catalogue en ligne (version, lien, taille, empreinte) sont conservés.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import threading
import unicodedata
from pathlib import Path
from typing import Any

from app.catalogue import CATALOGUE_PARTAGE, AppEntry, Catalogue, Transcription, _message
from app.info import resources_dir

ICONES = "icons"
FORMATS_ICONE = {".svg", ".png"}
TAILLE_ICONE = 1_000_000
CHAMPS_EN_LIGNE = ("version", "link", "size", "sha256")  # écrits par « Fabriquer le catalogue »
PREMIER_PORT = 8030
_VERROU = threading.Lock()


class ErreurEdition(ValueError):
    pass


def _fichier(dossier: Path) -> Path:
    return dossier / CATALOGUE_PARTAGE


def _lire_brut(dossier: Path) -> dict[str, Any]:
    try:
        donnees = json.loads(_fichier(dossier).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErreurEdition(f"catalogue.json illisible : {_message(e)}") from e
    if not isinstance(donnees, dict):
        raise ErreurEdition("catalogue.json illisible : un objet JSON est attendu.")
    donnees.setdefault("apps", [])
    return donnees


def _ecrire(dossier: Path, donnees: dict[str, Any]) -> None:
    """Valide puis écrit : un catalogue refusé n'écrase jamais le précédent."""
    try:
        Catalogue.model_validate(donnees)
    except Exception as e:  # noqa: BLE001 : message lisible
        raise ErreurEdition(_message(e)) from e
    fichier = _fichier(dossier)
    if fichier.is_file():
        shutil.copyfile(fichier, fichier.with_suffix(".json.bak"))
    temporaire = fichier.with_suffix(".json.part")
    temporaire.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporaire, fichier)


def etat(dossier: Path) -> dict[str, Any]:
    """Apps du catalogue telles qu'elles s'éditent, ou exists=False s'il n'y a pas encore de catalogue.json."""
    if not _fichier(dossier).is_file():
        return {"folder": str(dossier), "exists": False, "apps": [], "studiodock": {"source": "StudioDock"},
                "transcription": None}
    donnees = _lire_brut(dossier)
    apps = []
    for brut in donnees["apps"]:
        try:
            app = AppEntry.model_validate(brut).model_dump(exclude={"path", *CHAMPS_EN_LIGNE})
        except Exception as e:  # noqa: BLE001 : une app invalide est signalée, pas bloquante
            apps.append({"id": brut.get("id", "?"), "name": brut.get("name", "?"), "invalid": _message(e)})
            continue
        app["source"] = app["source"] or app["id"]
        fichier = app["icon"]["file"]
        app["iconFound"] = bool(fichier) and (dossier / fichier).is_file()
        app["sourceFound"] = (dossier / app["source"]).is_dir()
        apps.append(app)
    return {"folder": str(dossier), "exists": True, "apps": apps,
            "studiodock": {"source": (donnees.get("studiodock") or {}).get("source", "StudioDock")},
            "transcription": _etat_transcription(dossier, donnees.get("transcription"))}


def _etat_transcription(dossier: Path, brut: Any) -> dict[str, Any] | None:
    if not isinstance(brut, dict):
        return None
    from app import modeles

    try:
        conf = Transcription.model_validate(brut)
    except Exception as e:  # noqa: BLE001
        return {"name": brut.get("name", "?"), "source": brut.get("source", "?"), "invalid": _message(e)}
    archive = modeles.dans_partage(conf, dossier)
    return {"name": conf.name, "source": conf.source, "sourceFound": (dossier / conf.source).is_dir(),
            "found": archive.name if archive else None, "version": modeles.version_de(archive) if archive else None}


def enregistrer_transcription(dossier: Path, valeurs: dict[str, Any] | None) -> dict[str, Any]:
    """Déclare (ou retire, valeurs None) le modèle de transcription de l'équipe ; crée son sous-dossier."""
    with _VERROU:
        donnees = _lire_brut(dossier)
        if valeurs is None:
            donnees.pop("transcription", None)
        else:
            nom = str(valeurs.get("name") or "").strip() or "Modèle de transcription"
            sous_dossier = str(valeurs.get("source") or "").strip().strip("/\\") or "Modeles"
            if ".." in Path(sous_dossier).parts or Path(sous_dossier).is_absolute():
                raise ErreurEdition("Le sous-dossier doit être dans le dossier du catalogue.")
            ancien = donnees.get("transcription") if isinstance(donnees.get("transcription"), dict) else {}
            # Les champs du catalogue en ligne (version, lien, taille, empreinte) sont conservés
            donnees["transcription"] = {**{k: v for k, v in ancien.items() if k in (*CHAMPS_EN_LIGNE, "file")},
                                        "name": nom, "source": sous_dossier}
        _ecrire(dossier, donnees)
        if valeurs is not None:
            (dossier / donnees["transcription"]["source"]).mkdir(parents=True, exist_ok=True)
    return etat(dossier)


def creer(dossier: Path) -> dict[str, Any]:
    """Nouveau catalogue avec les apps de la suite (fiches, icônes, sous-dossiers), à compléter ou modifier."""
    with _VERROU:
        if _fichier(dossier).is_file():
            raise ErreurEdition("Ce dossier contient déjà un catalogue.json.")
        dossier.mkdir(parents=True, exist_ok=True)
        modele = json.loads((resources_dir() / "resources" / "apps.default.json").read_text(encoding="utf-8"))
        sources = {"specgen": "SpecGen", "audit-ergo": "AuditErgo", "docanalyser": "DocAnalyser", "mapline": "Mapline"}
        apps = []
        for app in modele.get("apps", []):
            app = {k: v for k, v in app.items() if k != "path"}
            app["source"] = sources.get(app["id"], app.get("name") or app["id"])
            app.setdefault("mode", "optionnel")
            fichier = (app.get("icon") or {}).get("file")
            if fichier:
                origine = resources_dir() / "resources" / fichier
                if origine.is_file():
                    (dossier / ICONES).mkdir(exist_ok=True)
                    shutil.copyfile(origine, dossier / fichier)
            (dossier / app["source"]).mkdir(exist_ok=True)
            apps.append(app)
        (dossier / "StudioDock").mkdir(exist_ok=True)
        _ecrire(dossier, {"apps": apps, "studiodock": {"source": "StudioDock"}})
    return etat(dossier)


def identifiant(nom: str, pris: set[str]) -> str:
    """« Mon App 2 » -> « mon-app-2 », unique dans le catalogue."""
    base = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:36] or "app"
    if not base[0].isalnum():
        base = "app-" + base
    candidat, n = base, 2
    while candidat in pris:
        candidat, n = f"{base}-{n}", n + 1
    return candidat


def port_libre(pris: set[int]) -> int:
    port = PREMIER_PORT
    while port in pris:
        port += 10
    return port


def enregistrer(dossier: Path, valeurs: dict[str, Any], ancien_id: str | None) -> dict[str, Any]:
    """Ajoute (ancien_id None) ou remplace une app. L'identifiant, le programme, le sous-dossier et le port d'une
    nouvelle app sont déduits de son nom s'ils ne sont pas donnés."""
    with _VERROU:
        donnees = _lire_brut(dossier)
        apps: list[dict[str, Any]] = donnees["apps"]
        index = next((i for i, a in enumerate(apps) if a.get("id") == ancien_id), None) if ancien_id else None
        if ancien_id and index is None:
            raise ErreurEdition("Cette app n'est plus dans le catalogue : rechargez la page.")
        autres = [a for i, a in enumerate(apps) if i != index]
        nom = str(valeurs.get("name") or "").strip()
        if not nom:
            raise ErreurEdition("Donnez un nom à l'app.")
        app = dict(apps[index]) if index is not None else {}
        compact = re.sub(r"[^A-Za-z0-9]+", "", unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode())
        app.update({k: v for k, v in valeurs.items() if k not in ("iconFound", "sourceFound", "invalid", *CHAMPS_EN_LIGNE)})
        app["name"] = nom
        app["id"] = ancien_id or str(valeurs.get("id") or "").strip() or identifiant(nom, {a.get("id") for a in autres})
        app["exe"] = str(app.get("exe") or "").strip() or compact or app["id"]
        app["source"] = str(app.get("source") or "").strip() or compact or app["id"]
        if app.get("kind", "web") == "web":
            if not app.get("port"):
                app["port"] = port_libre({a.get("port") for a in autres if a.get("port")})
            app.pop("install_name", None)
            app.pop("address", None)
        elif app.get("kind") == "external":
            # Port fixé par l'adresse (validation du catalogue), ou détecté au lancement si l'adresse est vide
            app["address"] = str(app.get("address") or "").strip() or None
            app["port"] = None
            app.pop("install_name", None)
        else:
            app.pop("address", None)
            app["port"] = None
            app["install_name"] = str(app.get("install_name") or "").strip() or None
        # Listes nettoyées : lignes vides retirées
        app["points"] = [p.strip() for p in app.get("points") or [] if str(p).strip()]
        app["tutorial"] = [e for e in app.get("tutorial") or [] if str(e.get("title") or "").strip()]
        app["links"] = [l for l in app.get("links") or [] if str(l.get("label") or "").strip() and str(l.get("url") or "").strip()]
        app = {k: v for k, v in app.items() if v is not None}
        if index is None:
            apps.append(app)
        else:
            apps[index] = app
        _ecrire(dossier, donnees)
        (dossier / app["source"]).mkdir(exist_ok=True)
    return {**etat(dossier), "saved": app["id"]}


def supprimer(dossier: Path, app_id: str) -> dict[str, Any]:
    """Retire l'app du catalogue ; ses fichiers (sous-dossier, icône) restent dans le dossier."""
    with _VERROU:
        donnees = _lire_brut(dossier)
        donnees["apps"] = [a for a in donnees["apps"] if a.get("id") != app_id]
        _ecrire(dossier, donnees)
    return etat(dossier)


def deplacer(dossier: Path, app_id: str, sens: int) -> dict[str, Any]:
    """Monte (-1) ou descend (+1) l'app : l'ordre du catalogue est celui des cartes."""
    with _VERROU:
        donnees = _lire_brut(dossier)
        apps = donnees["apps"]
        i = next((i for i, a in enumerate(apps) if a.get("id") == app_id), None)
        j = (i + sens) if i is not None else None
        if i is not None and j is not None and 0 <= j < len(apps):
            apps[i], apps[j] = apps[j], apps[i]
            _ecrire(dossier, donnees)
    return etat(dossier)


def importer_icone(dossier: Path, app_id: str, nom: str, contenu_b64: str) -> str:
    """Copie l'icône (SVG ou PNG) dans icons/ ; renvoie son chemin relatif, à mettre dans la fiche."""
    extension = Path(nom).suffix.lower()
    if extension not in FORMATS_ICONE:
        raise ErreurEdition("Icône au format SVG ou PNG attendue.")
    try:
        contenu = base64.b64decode(contenu_b64, validate=True)
    except ValueError as e:
        raise ErreurEdition("Fichier d'icône illisible.") from e
    if len(contenu) > TAILLE_ICONE:
        raise ErreurEdition("Icône trop lourde (1 Mo au plus).")
    if extension == ".png" and not contenu.startswith(b"\x89PNG"):
        raise ErreurEdition("Ce fichier n'est pas une image PNG.")
    if extension == ".svg" and b"<svg" not in contenu[:4096].lower():
        raise ErreurEdition("Ce fichier n'est pas une image SVG.")
    sur = re.sub(r"[^a-z0-9-]+", "-", app_id.lower()).strip("-") or "app"
    (dossier / ICONES).mkdir(parents=True, exist_ok=True)
    for ancien in FORMATS_ICONE - {extension}:
        (dossier / ICONES / f"{sur}{ancien}").unlink(missing_ok=True)
    (dossier / ICONES / f"{sur}{extension}").write_bytes(contenu)
    return f"{ICONES}/{sur}{extension}"


def chemin_icone(dossier: Path, fichier: str) -> Path | None:
    """Icône d'une fiche, seulement si elle est dans le dossier du catalogue."""
    try:
        chemin = (dossier / fichier).resolve()
        chemin.relative_to(dossier.resolve())
    except (OSError, ValueError):
        return None
    return chemin if chemin.is_file() and chemin.suffix.lower() in FORMATS_ICONE else None
