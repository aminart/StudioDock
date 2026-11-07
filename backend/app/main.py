"""API de Studio Dock et service de l'interface compilée (frontend/dist)."""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import installation, miseajour, reglages, winapi
from app.catalogue import AppEntry, Catalogue, Source, fichier_icone, partage_accessible
from app.info import (APP_ID, APP_NAME, EMPAQUETE, PLATEFORME, REPO_DIR, VERSION, dossier_installation_choisi, exe_dir,
                      home_dir, logs_dir, resources_dir)
from app.installeur import Installeur, installee
from app.pilote import ErreurAction, Pilote
from app.recherche import Trouvee, plus_recente, trouver_dans_partage

app = FastAPI(title=APP_NAME, version=VERSION, docs_url=None, redoc_url=None, openapi_url=None)
source = Source()
pilote = Pilote()
installeur = Installeur(pilote)
# Sélecteur de dossier natif, fourni par la fenêtre (pywebview) ; None dans le navigateur
choisir_dossier: Callable[[], str | None] | None = None

_cache_partage: dict[str, tuple[float, Trouvee | None]] = {}


def _disponible(entree: AppEntry, partage: Path | None) -> Trouvee | None:
    """Dernière version sur le partage, relue au plus toutes les 5 secondes (partage réseau parfois lent)."""
    if partage is None:
        return None
    cle = f"{partage}|{entree.id}|{entree.source}|{entree.exe}"
    instant, trouvee = _cache_partage.get(cle, (0.0, None))
    if time.monotonic() - instant > 5:
        trouvee = trouver_dans_partage(entree, partage)
        _cache_partage[cle] = (time.monotonic(), trouvee)
    return trouvee


def _partage_lisible() -> Path | None:
    """Dossier partagé utilisable pour installer : réglé, accessible et avec un catalogue."""
    return source.partage if source.origine == "shared" and partage_accessible(source.partage) else None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": APP_ID, "name": APP_NAME, "version": VERSION}


def _app_ou_404(app_id: str) -> AppEntry:
    entree = source.trouver(app_id)
    if entree is None:
        raise HTTPException(404, f"Application inconnue : {app_id}")
    return entree


def _carte(entree: AppEntry, etat: dict[str, Any], vues: set[str]) -> dict[str, Any]:
    equipe = source.origine != "local"
    est_installee, version_locale = installee(entree)
    if not equipe:
        est_installee = True  # liste locale : toutes les apps sont « mes applications »
    disponible = _disponible(entree, _partage_lisible())
    copie = installeur.en_cours(entree.id)
    return {
        **entree.model_dump(exclude={"path", "install_name", "source"}),
        "iconUrl": f"/api/apps/{entree.id}/icon" if fichier_icone(entree, source.partage) else None,
        **etat,
        "installed": est_installee,
        "availableVersion": disponible.version if disponible else None,
        "update": bool(disponible) and est_installee and equipe and plus_recente(disponible.version, version_locale),
        "progress": copie.progres if copie and not copie.fini else None,
        "installError": copie.erreur if copie else None,
        "isNew": equipe and not est_installee and entree.id not in vues,
    }


def _visibles(catalogue: Catalogue) -> list[AppEntry]:
    if source.origine == "local":
        return catalogue.apps
    return [a for a in catalogue.apps if a.mode != "masque"]


@app.get("/api/apps")
async def lister() -> dict[str, Any]:
    catalogue = source.lire()
    apps = _visibles(catalogue)
    partage = _partage_lisible()
    a_installer = installation.a_installer()
    if partage is not None and not a_installer:
        await asyncio.to_thread(installeur.installer_les_apps_imposees, apps, partage)
    etats = await pilote.etats(apps)
    if source.origine == "shared" and "seen" not in reglages.lire():
        # Premier catalogue d'équipe vu sur ce poste : rien n'est « nouveau », seules les apps ajoutées ensuite le seront
        reglages.marquer_vues([a.id for a in apps])
    vues = reglages.deja_vues()
    nouvelle = await asyncio.to_thread(miseajour.version_disponible, catalogue, partage)
    cartes = await asyncio.to_thread(lambda: [_carte(a, etats[a.id], vues) for a in apps])
    return {
        "version": VERSION,
        "platform": PLATEFORME,
        "home": str(home_dir()),
        "catalogue": str(source.chemin),
        "source": source.origine,
        "sharedFolder": str(source.partage) if source.partage else None,
        "sharedOk": partage is not None,
        "error": source.erreur,
        "dock": {"update": nouvelle.version if nouvelle else None, "canUpdate": miseajour.remplacement_possible()},
        "canChooseFolder": choisir_dossier is not None,
        "needsInstall": a_installer,
        "apps": cartes,
    }


async def _apres(entree: AppEntry) -> dict[str, Any]:
    etats = await pilote.etats([entree])
    return await asyncio.to_thread(_carte, entree, etats[entree.id], reglages.deja_vues())


@app.post("/api/apps/{app_id}/install")
async def installer(app_id: str):
    """Installe ou met à jour l'app depuis le dossier partagé (copie en arrière-plan, progression dans la liste)."""
    entree = _app_ou_404(app_id)
    if installation.a_installer():
        return JSONResponse(status_code=409, content={
            "detail": "Installez d'abord Studio Dock dans votre dossier (Réglages).", "code": "not_installed"})
    try:
        await asyncio.to_thread(installeur.installer, entree, _partage_lisible())
    except FileNotFoundError as e:
        return JSONResponse(status_code=409, content={"detail": str(e), "code": "unavailable"})
    except ErreurAction as e:
        return _erreur(e)
    return await _apres(entree)


@app.post("/api/apps/{app_id}/uninstall")
async def retirer(app_id: str):
    entree = _app_ou_404(app_id)
    if entree.mode == "auto" and source.origine != "local":
        return JSONResponse(status_code=409, content={
            "detail": f"{entree.name} est installée pour toute l'équipe : elle ne peut pas être retirée.", "code": "auto"})
    try:
        await asyncio.to_thread(installeur.retirer, entree)
    except (ValueError, ErreurAction) as e:
        return JSONResponse(status_code=409, content={"detail": getattr(e, "message", str(e)), "code": "unsupported"})
    return await _apres(entree)


class Vues(BaseModel):
    ids: list[str]


@app.post("/api/seen")
async def vues(corps: Vues):
    reglages.marquer_vues(corps.ids)
    return {"ok": True}


class Reglages(BaseModel):
    shared_folder: str | None = None


@app.get("/api/settings")
async def lire_reglages():
    valeurs = reglages.lire()
    partage = reglages.dossier_partage()
    return {
        "shared_folder": valeurs.get("shared_folder") or "",
        "resolved": str(partage) if partage else None,
        "reachable": partage_accessible(partage),
        "hasCatalogue": bool(partage) and partage_accessible(partage) and (partage / "catalogue.json").is_file(),
        "home": str(home_dir()),
        "canChooseFolder": choisir_dossier is not None,
        "install": _etat_installation(),
    }


def _etat_installation() -> dict[str, Any]:
    choisi = dossier_installation_choisi()
    return {
        "available": installation.disponible(),
        "installed": installation.est_installe(),
        "folder": str(choisi) if choisi else None,
        "suggested": str(installation.dossier_propose()),
        "running": str(exe_dir()) if exe_dir() else None,
    }


def _partage_detecte() -> Path | None:
    """Exe lancé depuis le sous-dossier StudioDock du dossier partagé : celui-ci, s'il a un catalogue."""
    dossier = exe_dir()
    if dossier is None:
        return None
    for candidat in (dossier, dossier.parent):
        if (candidat / "catalogue.json").is_file():
            return candidat
    return None


class Installation(BaseModel):
    folder: str


@app.put("/api/settings/install")
async def installer_studio_dock(corps: Installation):
    """Installe Studio Dock dans le dossier choisi (ou l'y déplace avec les apps), puis redémarre depuis celui-ci."""
    if not installation.disponible():
        raise HTTPException(409, "Le dossier d'installation se choisit dans la version Windows de Studio Dock.")
    dossier = reglages.developper(corps.folder)
    if dossier is None:
        raise HTTPException(400, "Indiquez un dossier.")
    detecte = _partage_detecte()
    partage = reglages.dossier_partage() or detecte
    try:
        installation.verifier(dossier, partage)
    except installation.ErreurInstallation as e:
        raise HTTPException(409, str(e)) from e
    ancien = dossier_installation_choisi()
    # Apps déjà installées : dans l'ancien dossier choisi, ou (version 0.1) à côté de l'exe hors du partage
    source_apps = ancien
    if source_apps is None and exe_dir() is not None and (exe_dir() / "apps").is_dir() \
            and not (partage and installation.dedans(exe_dir(), partage)):
        source_apps = exe_dir()
    pilote.tout_arreter()
    try:
        exe = await asyncio.to_thread(installation.installer, dossier, Path(sys.executable), source_apps)
    except installation.ErreurInstallation as e:
        raise HTTPException(409, str(e)) from e
    valeurs: dict[str, Any] = {"install_folder": str(dossier)}
    if detecte is not None and not reglages.locaux().get("shared_folder"):
        valeurs["shared_folder"] = str(detecte)  # premier lancement depuis le partage : il est retenu
    reglages.modifier(**valeurs)
    raccourci = await asyncio.to_thread(installation.creer_raccourci, exe)
    a_nettoyer = ancien if ancien is not None and not installation.meme(ancien, dossier) else None
    installation.redemarrer(exe, a_nettoyer, pilote.tout_arreter)
    return {"ok": True, "restarting": True, "folder": str(dossier), "shortcut": raccourci}


@app.put("/api/settings")
async def modifier_reglages(corps: Reglages):
    dossier = (corps.shared_folder or "").strip()
    reglages.modifier(shared_folder=dossier or None)
    _cache_partage.clear()
    return await lire_reglages()


@app.post("/api/settings/choose-folder")
async def choisir():
    if choisir_dossier is None:
        raise HTTPException(409, "Sélecteur indisponible : saisissez le chemin du dossier.")
    chemin = await asyncio.to_thread(choisir_dossier)
    return {"path": chemin}


@app.post("/api/dock/update")
async def mettre_a_jour_studio_dock():
    catalogue = source.lire()
    nouvelle = miseajour.version_disponible(catalogue, _partage_lisible())
    if nouvelle is None:
        raise HTTPException(409, "Aucune version plus récente de Studio Dock dans le dossier partagé.")
    if not miseajour.remplacement_possible():
        winapi.ouvrir(str(nouvelle.chemin.parent))
        return {"ok": True, "restarting": False}
    try:
        miseajour.appliquer(nouvelle, pilote.tout_arreter)
    except OSError as e:
        raise HTTPException(409, f"Mise à jour impossible : {e}") from e
    return {"ok": True, "restarting": True, "version": nouvelle.version}


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
    installeur.oublier_erreur(entree.id)
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
    if source.partage and partage_accessible(source.partage):
        dossiers["shared"] = source.partage
    if nom not in dossiers:
        raise HTTPException(404, "Dossier inaccessible.")
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
    chemin = fichier_icone(_app_ou_404(app_id), source.partage)
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
