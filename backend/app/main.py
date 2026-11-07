"""API de Studio Dock et service de l'interface compilée (frontend/dist)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import winapi
from app.catalogue import AppEntry, Source, fichier_icone
from app.info import APP_ID, APP_NAME, EMPAQUETE, PLATEFORME, REPO_DIR, VERSION, home_dir, logs_dir, resources_dir
from app.pilote import ErreurAction, Pilote

app = FastAPI(title=APP_NAME, version=VERSION, docs_url=None, redoc_url=None, openapi_url=None)
source = Source()
pilote = Pilote()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": APP_ID, "name": APP_NAME, "version": VERSION}


def _app_ou_404(app_id: str) -> AppEntry:
    entree = source.trouver(app_id)
    if entree is None:
        raise HTTPException(404, f"Application inconnue : {app_id}")
    return entree


def _carte(entree: AppEntry, etat: dict[str, Any]) -> dict[str, Any]:
    return {
        **entree.model_dump(exclude={"path", "install_name"}),
        "iconUrl": f"/api/apps/{entree.id}/icon" if fichier_icone(entree) else None,
        **etat,
    }


@app.get("/api/apps")
async def lister() -> dict[str, Any]:
    catalogue = source.lire()
    etats = await pilote.etats(catalogue.apps)
    return {
        "version": VERSION,
        "platform": PLATEFORME,
        "home": str(home_dir()),
        "catalogue": str(source.chemin),
        "error": source.erreur,
        "apps": [_carte(a, etats[a.id]) for a in catalogue.apps],
    }


async def _apres(entree: AppEntry) -> dict[str, Any]:
    etats = await pilote.etats([entree])
    return _carte(entree, etats[entree.id])


def _erreur(e: ErreurAction) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": e.message, "code": e.code})


@app.post("/api/apps/{app_id}/launch")
async def lancer(app_id: str):
    entree = _app_ou_404(app_id)
    try:
        pilote.lancer(entree)
    except ErreurAction as e:
        return _erreur(e)
    return await _apres(entree)


@app.post("/api/apps/{app_id}/stop")
async def arreter(app_id: str):
    entree = _app_ou_404(app_id)
    try:
        pilote.arreter(entree)
    except ErreurAction as e:
        return _erreur(e)
    return await _apres(entree)


@app.post("/api/apps/{app_id}/open")
async def ouvrir(app_id: str):
    entree = _app_ou_404(app_id)
    try:
        pilote.ouvrir(entree)
    except ErreurAction as e:
        return _erreur(e)
    return {"ok": True}


@app.post("/api/apps/{app_id}/dismiss")
async def effacer(app_id: str):
    entree = _app_ou_404(app_id)
    pilote.effacer_erreur(entree)
    return await _apres(entree)


@app.post("/api/apps/{app_id}/folder")
async def dossier(app_id: str):
    """Ouvre le dossier où se trouve (ou doit être déposé) l'exe de l'app."""
    entree = _app_ou_404(app_id)
    etat = (await pilote.etats([entree]))[entree.id]
    cible = etat.get("folder")
    if not cible:
        raise HTTPException(404, f"Pas de dossier connu pour {entree.name}.")
    Path(cible).mkdir(parents=True, exist_ok=True)
    winapi.ouvrir(cible)
    return {"ok": True, "folder": cible}


@app.post("/api/open-folder/{nom}")
async def ouvrir_dossier(nom: str):
    dossiers = {"home": home_dir(), "logs": logs_dir()}
    if nom not in dossiers:
        raise HTTPException(404)
    dossiers[nom].mkdir(parents=True, exist_ok=True)
    winapi.ouvrir(str(dossiers[nom]))
    return {"ok": True}


class Lien(BaseModel):
    url: str


@app.post("/api/open-link")
async def ouvrir_lien(lien: Lien):
    """Lien d'une fiche : ouvert dans le navigateur par défaut, pas dans la fenêtre de Studio Dock."""
    if not lien.url.startswith(("http://", "https://")):
        raise HTTPException(400, "Seules les adresses http(s) sont acceptées.")
    winapi.ouvrir(lien.url)
    return {"ok": True}


@app.get("/api/apps/{app_id}/icon")
async def icone(app_id: str):
    chemin = fichier_icone(_app_ou_404(app_id))
    if not chemin:
        raise HTTPException(404)
    return FileResponse(chemin, headers={"Cache-Control": "no-cache"})


def _dossier_interface() -> Path:
    if autre := os.getenv("FRONTEND_DIST"):
        return Path(autre)
    if EMPAQUETE:
        return resources_dir() / "frontend_dist"
    return REPO_DIR / "frontend" / "dist"


INTERFACE = _dossier_interface()

if (INTERFACE / "index.html").is_file():
    if (INTERFACE / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=INTERFACE / "assets"), name="assets")

    @app.get("/{chemin:path}", include_in_schema=False)
    async def interface(chemin: str):
        if chemin.startswith("api/"):
            raise HTTPException(404)
        fichier = (INTERFACE / chemin).resolve()
        if chemin and fichier.is_file() and INTERFACE.resolve() in fichier.parents:
            return FileResponse(fichier)
        return FileResponse(INTERFACE / "index.html", headers={"Cache-Control": "no-cache"})
