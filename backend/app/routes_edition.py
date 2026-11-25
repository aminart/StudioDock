"""Préparer pour l'équipe › Applications : éditer catalogue.json par formulaire (edition.py).

POST   /api/admin/catalogue/apps          {folder}                apps du catalogue (exists=False s'il n'y en a pas)
POST   /api/admin/catalogue/create        {folder}                créer le catalogue avec les apps de la suite
PUT    /api/admin/catalogue/apps          {folder, id?, app}      ajouter (sans id) ou modifier une app
POST   /api/admin/catalogue/apps/delete   {folder, id}            retirer une app du catalogue
POST   /api/admin/catalogue/apps/move     {folder, id, direction} monter (-1) ou descendre (+1)
PUT    /api/admin/catalogue/transcription {folder, transcription} déclarer (ou retirer : null) le modèle de transcription
POST   /api/admin/catalogue/icon          {folder, id, name, data} importer une icône (base64), renvoie son chemin
GET    /api/admin/catalogue/icon?folder=&file=                    afficher une icône du dossier
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app import edition, reglages

router = APIRouter(prefix="/api/admin/catalogue")


class Dossier(BaseModel):
    folder: str


class Modification(Dossier):
    id: str | None = None  # app modifiée ; absent : nouvelle app
    app: dict[str, Any]


class Cible(Dossier):
    id: str


class Deplacement(Cible):
    direction: int


class ModeleTranscription(Dossier):
    transcription: dict[str, Any] | None = None  # {name, source} ; None : retirer le modèle du catalogue


class Icone(Cible):
    name: str
    data: str


def _dossier(brut: str) -> Path:
    dossier = reglages.developper(brut)
    if dossier is None or not dossier.is_absolute():
        raise HTTPException(422, "Indiquez le chemin complet du dossier du catalogue.")
    return dossier


def _avec_contexte(dossier: Path, resultat: dict[str, Any]) -> dict[str, Any]:
    """Le dossier édité est-il le dossier partagé de l'équipe ? Les changements y sont alors visibles tout de suite."""
    partage = reglages.dossier_partage()
    try:
        commun = partage is not None and partage.resolve() == dossier.resolve()
    except OSError:
        commun = False
    reglages.modifier(prepare_folder=str(dossier))
    return {**resultat, "isShared": commun}


async def _executer(dossier: Path, fonction, *args) -> dict[str, Any]:
    try:
        return _avec_contexte(dossier, await asyncio.to_thread(fonction, dossier, *args))
    except edition.ErreurEdition as e:
        raise HTTPException(422, str(e)) from e
    except OSError as e:
        raise HTTPException(409, f"Dossier inaccessible ({dossier}) : {e.strerror or e}") from e


@router.post("/apps")
async def lire(corps: Dossier):
    dossier = _dossier(corps.folder)
    if not await asyncio.to_thread(dossier.is_dir):
        raise HTTPException(409, f"Dossier introuvable : {dossier}")
    return await _executer(dossier, edition.etat)


@router.post("/create")
async def creer(corps: Dossier):
    return await _executer(_dossier(corps.folder), edition.creer)


@router.put("/apps")
async def enregistrer(corps: Modification):
    return await _executer(_dossier(corps.folder), edition.enregistrer, corps.app, corps.id)


@router.post("/apps/delete")
async def supprimer(corps: Cible):
    return await _executer(_dossier(corps.folder), edition.supprimer, corps.id)


@router.post("/apps/move")
async def deplacer(corps: Deplacement):
    return await _executer(_dossier(corps.folder), edition.deplacer, corps.id, 1 if corps.direction > 0 else -1)


@router.put("/transcription")
async def transcription(corps: ModeleTranscription):
    return await _executer(_dossier(corps.folder), edition.enregistrer_transcription, corps.transcription)


@router.post("/icon")
async def importer_icone(corps: Icone):
    dossier = _dossier(corps.folder)
    try:
        fichier = await asyncio.to_thread(edition.importer_icone, dossier, corps.id, corps.name, corps.data)
    except edition.ErreurEdition as e:
        raise HTTPException(422, str(e)) from e
    return {"file": fichier}


@router.get("/icon")
async def icone(folder: str, file: str):
    chemin = edition.chemin_icone(_dossier(folder), file)
    if chemin is None:
        raise HTTPException(404, "Icône introuvable.")
    return FileResponse(chemin, media_type="image/svg+xml" if chemin.suffix.lower() == ".svg" else "image/png",
                        headers={"Cache-Control": "no-store"})
