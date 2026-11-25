"""Modèle de transcription de l'équipe : déposé une fois par l'administratrice, installé chez chacun par Studio Dock.

Le catalogue déclare le modèle (section « transcription ») : son nom et le sous-dossier du partage où l'on dépose son
archive .zip (un modèle faster-whisper / CTranslate2 : config.json, model.bin, tokenizer.json…). Comme pour les apps :
- **dossier partagé** : la dernière archive du sous-dossier est installée d'office (et remplacée quand une nouvelle
  arrive), sans rien demander ;
- **catalogue en ligne** : le bouton « Télécharger » ouvre le lien dans le navigateur ; l'archive arrivée dans
  Téléchargements est vérifiée (taille, empreinte) puis installée.

Installation : home_dir()/modeles/transcription/ (dossier d'installation de la personne, déplacé avec lui).
Les apps trouvent le modèle dans le dossier « ia » de Studio Dock :
    transcription.json   {"format": 1, "name", "version", "path"}
lu avec studiodock_ia.transcription() (copie du contrat dans chaque app).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from app import ia
from app.catalogue import Transcription
from app.info import home_dir

FORMAT = 1
CLE = "transcription"  # clé des demandes de téléchargement (catalogue en ligne)
FICHIER_IA = "transcription.json"
INFO = "modele.json"
REQUIS = ("config.json", "model.bin")  # minimum d'un modèle CTranslate2 (tokenizer.json ou vocabulary.* en plus)
VERSION_NOM = re.compile(r"(\d+(?:\.\d+){1,3})")
_VERROU = threading.Lock()


class ErreurModele(Exception):
    pass


@dataclass
class Suivi:
    progres: int = 0
    erreur: str | None = None
    fini: bool = False
    archive: tuple[str, int] | None = None  # (nom, taille) de l'archive installée ou refusée


_suivi: Suivi | None = None


def dossier_local() -> Path:
    return home_dir() / "modeles" / "transcription"


def _fichier_ia() -> Path:
    return ia.dossier() / FICHIER_IA


def version_de(archive: Path) -> str | None:
    trouve = VERSION_NOM.search(archive.stem)
    return trouve.group(1) if trouve else None


def _cle(version: str | None) -> tuple[int, ...]:
    return tuple(int(x) for x in version.split(".")) if version else ()


# --- Ce qui est installé ------------------------------------------------------------------------------------

def installe() -> dict[str, Any] | None:
    """{name, version, archive, size, path} du modèle installé sur ce poste, ou None."""
    try:
        info = json.loads((dossier_local() / INFO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    racine = dossier_local() / str(info.get("root") or "")
    if not isinstance(info, dict) or not all((racine / f).is_file() for f in REQUIS):
        return None
    return {**info, "path": str(racine)}


def publier() -> None:
    """Indique aux apps où est le modèle (réécrit seulement si nécessaire : le dossier d'installation peut changer)."""
    modele = installe()
    cible = _fichier_ia()
    if modele is None:
        cible.unlink(missing_ok=True)
        return
    valeur = {"format": FORMAT, "name": modele.get("name") or "Modèle de transcription",
              "version": modele.get("version"), "path": modele["path"]}
    try:
        if json.loads(cible.read_text(encoding="utf-8")) == valeur:
            return
    except (OSError, ValueError):
        pass
    cible.parent.mkdir(parents=True, exist_ok=True)
    temporaire = cible.with_suffix(".json.part")
    temporaire.write_text(json.dumps(valeur, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporaire, cible)


def retirer() -> None:
    shutil.rmtree(dossier_local(), ignore_errors=True)
    _fichier_ia().unlink(missing_ok=True)


# --- Où trouver l'archive -----------------------------------------------------------------------------------

def dans_partage(conf: Transcription, partage: Path | None) -> Path | None:
    """Archive la plus récente du sous-dossier : numéro de version dans le nom, sinon date de modification."""
    if partage is None:
        return None
    try:
        dossier = partage / conf.source
        archives = [f for f in dossier.iterdir() if f.is_file() and f.suffix.lower() == ".zip"]
    except OSError:
        return None
    if not archives:
        return None
    return max(archives, key=lambda f: (_cle(version_de(f)), f.stat().st_mtime))


def a_jour(archive: Path) -> bool:
    """La même archive (nom et taille) est déjà installée."""
    modele = installe()
    try:
        return modele is not None and modele.get("archive") == archive.name and modele.get("size") == archive.stat().st_size
    except OSError:
        return True  # partage momentanément illisible : on ne touche à rien


# --- Installation -------------------------------------------------------------------------------------------

def en_cours() -> Suivi | None:
    return _suivi


def signaler(erreur: str) -> None:
    """Erreur affichée dans Réglages (par exemple : téléchargement incomplet)."""
    global _suivi
    with _VERROU:
        _suivi = Suivi(erreur=erreur, fini=True)


def oublier_erreur() -> None:
    global _suivi
    with _VERROU:
        if _suivi is not None and _suivi.fini:
            _suivi = None


def _racine_du_modele(noms: list[str]) -> str:
    """Dossier de l'archive qui contient le modèle : la racine, ou un seul niveau de sous-dossier."""
    fichiers = {n for n in noms if not n.endswith("/")}
    for prefixe in [""] + sorted({n.split("/")[0] + "/" for n in fichiers if "/" in n}):
        if all(prefixe + f in fichiers for f in REQUIS):
            return prefixe
    raise ErreurModele("Cette archive ne contient pas de modèle faster-whisper (config.json et model.bin introuvables).")


def _extraire(archive: Path, suivi: Suivi) -> str:
    """Extrait dans un dossier temporaire, puis remplace l'ancien modèle d'un coup. Renvoie la racine du modèle."""
    cible = dossier_local()
    temporaire = cible.with_name(cible.name + ".part")
    shutil.rmtree(temporaire, ignore_errors=True)
    temporaire.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive) as z:
            membres = z.infolist()
            racine = _racine_du_modele([m.filename for m in membres])
            total = max(1, sum(m.file_size for m in membres))
            fait = 0
            for m in membres:
                chemin = PurePosixPath(m.filename)
                if chemin.is_absolute() or ".." in chemin.parts:
                    raise ErreurModele(f"Archive refusée : chemin interdit ({m.filename}).")
                z.extract(m, temporaire)
                fait += m.file_size
                suivi.progres = min(99, int(fait * 100 / total))
    except zipfile.BadZipFile as e:
        shutil.rmtree(temporaire, ignore_errors=True)
        raise ErreurModele("Archive .zip illisible ou incomplète.") from e
    except BaseException:
        shutil.rmtree(temporaire, ignore_errors=True)
        raise
    ancien = cible.with_name(cible.name + ".old")
    shutil.rmtree(ancien, ignore_errors=True)
    if cible.exists():
        cible.replace(ancien)
    temporaire.replace(cible)
    shutil.rmtree(ancien, ignore_errors=True)  # une app qui lit encore l'ancien modèle : nettoyé la fois suivante
    return racine.rstrip("/")


def installer(archive: Path, nom: str, version: str | None = None, apres: Callable[[], None] | None = None,
              origine: str = "le dossier partagé") -> bool:
    """Installe l'archive en arrière-plan (progression : en_cours()). False si une installation est déjà en cours."""
    global _suivi
    with _VERROU:
        if _suivi is not None and not _suivi.fini:
            return False
        try:
            suivi = _suivi = Suivi(archive=(archive.name, archive.stat().st_size))
        except OSError:
            suivi = _suivi = Suivi()

    def travail() -> None:
        try:
            taille = archive.stat().st_size
            racine = _extraire(archive, suivi)
            info = {"name": nom, "version": version or version_de(archive), "archive": archive.name, "size": taille,
                    "root": racine}
            (dossier_local() / INFO).write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
            publier()
            suivi.progres = 100
            if apres:
                apres()
        except ErreurModele as e:
            suivi.erreur = str(e)
        except OSError as e:
            suivi.erreur = f"Installation depuis {origine} impossible : {e.strerror or e}"
        finally:
            suivi.fini = True

    threading.Thread(target=travail, name="modele-transcription", daemon=True).start()
    return True


def installer_si_besoin(conf: Transcription | None, partage: Path | None) -> None:
    """Dossier partagé : installe ou met à jour d'office (appelé à chaque rafraîchissement de la liste des apps)."""
    if conf is None:
        return
    archive = dans_partage(conf, partage)
    if archive is None or a_jour(archive):
        publier()
        return
    suivi = _suivi
    if suivi is not None and suivi.fini and suivi.erreur and suivi.archive == (archive.name, archive.stat().st_size):
        return  # même archive déjà refusée : on ne recommence pas en boucle (l'erreur reste affichée)
    installer(archive, conf.name, version_de(archive))


# --- État pour l'interface ----------------------------------------------------------------------------------

def etat(conf: Transcription | None, partage: Path | None, origine: str, en_attente: bool) -> dict[str, Any]:
    modele = installe()
    suivi = en_cours()
    disponible = None
    if conf is not None:
        if origine == "online":
            disponible = conf.version if conf.link else None
        elif (archive := dans_partage(conf, partage)) is not None:
            disponible = version_de(archive) or archive.name
    return {
        "offered": conf is not None,
        "name": (conf.name if conf else None) or (modele or {}).get("name"),
        "installed": modele is not None,
        "version": (modele or {}).get("version"),
        "path": (modele or {}).get("path"),
        "available": disponible,
        "update": bool(conf and origine == "online" and modele and conf.version
                       and _cle(conf.version) > _cle(modele.get("version"))),
        "size": conf.size if conf else None,
        "online": origine == "online",
        "canDownload": bool(conf and origine == "online" and conf.link),
        "waiting": en_attente,
        "progress": suivi.progres if suivi and not suivi.fini else None,
        "error": suivi.erreur if suivi and suivi.fini else None,
    }
