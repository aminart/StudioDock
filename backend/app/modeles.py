"""Modèles d'IA de l'équipe : déposés une fois par l'administratrice, installés chez chacun par Studio Dock.

Deux types de modèles, gérés de la même façon (voir TypeModele) :
- **transcription** : un modèle faster-whisper / CTranslate2 (config.json, model.bin, tokenizer.json…) ;
- **intervenants** : un pipeline pyannote d'identification des intervenants (config.yaml, embedding/, segmentation/…).

Le catalogue déclare chaque modèle (sections « transcription » et « intervenants ») : son nom et le sous-dossier du
partage où l'on dépose son archive .zip. Comme pour les apps :
- **dossier partagé** : la dernière archive du sous-dossier est installée d'office (et remplacée quand une nouvelle
  arrive), sans rien demander ;
- **catalogue en ligne** : le bouton « Télécharger » ouvre le lien dans le navigateur ; l'archive arrivée dans
  Téléchargements est vérifiée (taille, empreinte) puis installée.

Installation : home_dir()/modeles/<type>/ (dossier d'installation de la personne, déplacé avec lui).
Les apps trouvent le modèle dans le dossier « ia » de Studio Dock :
    transcription.json   {"format": 1, "name", "version", "path"}   lu avec studiodock_ia.transcription()
    intervenants.json    {"format": 1, "name", "version", "path"}   lu avec studiodock_ia.intervenants()
(copie du contrat dans chaque app).
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
from app.catalogue import ModelePartage
from app.info import home_dir

FORMAT = 1
INFO = "modele.json"
VERSION_NOM = re.compile(r"(\d+(?:\.\d+){1,3})")


class ErreurModele(Exception):
    pass


@dataclass
class Suivi:
    progres: int = 0
    erreur: str | None = None
    fini: bool = False
    archive: tuple[str, int] | None = None  # (nom, taille) de l'archive installée ou refusée


def version_de(archive: Path) -> str | None:
    trouve = VERSION_NOM.search(archive.stem)
    return trouve.group(1) if trouve else None


def _cle(version: str | None) -> tuple[int, ...]:
    return tuple(int(x) for x in version.split(".")) if version else ()


def dans_partage(conf: ModelePartage, partage: Path | None) -> Path | None:
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


class TypeModele:
    """Un type de modèle distribué à l'équipe : où il s'installe, comment on le reconnaît, comment les apps le trouvent."""

    def __init__(self, cle: str, requis: tuple[str, ...], nom_par_defaut: str, prefixe_telechargement: str, erreur_contenu: str):
        self.cle = cle                          # section du catalogue, clé de téléchargement, dossier, fichier « ia »
        self.fichier_ia = f"{cle}.json"
        self.requis = requis                    # fichiers qui prouvent qu'une archive contient bien ce modèle
        self.nom_par_defaut = nom_par_defaut
        self.prefixe_telechargement = prefixe_telechargement  # nom d'archive attendu dans Téléchargements
        self.erreur_contenu = erreur_contenu
        self._suivi: Suivi | None = None
        self._verrou = threading.Lock()

    def dossier_local(self) -> Path:
        return home_dir() / "modeles" / self.cle

    def _fichier_ia(self) -> Path:
        return ia.dossier() / self.fichier_ia

    # --- Ce qui est installé ---

    def installe(self) -> dict[str, Any] | None:
        """{name, version, archive, size, path} du modèle installé sur ce poste, ou None."""
        try:
            info = json.loads((self.dossier_local() / INFO).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        racine = self.dossier_local() / str(info.get("root") or "")
        if not isinstance(info, dict) or not all((racine / f).is_file() for f in self.requis):
            return None
        return {**info, "path": str(racine)}

    def publier(self) -> None:
        """Indique aux apps où est le modèle (réécrit seulement si nécessaire : le dossier d'installation peut changer)."""
        modele = self.installe()
        cible = self._fichier_ia()
        if modele is None:
            cible.unlink(missing_ok=True)
            return
        valeur = {"format": FORMAT, "name": modele.get("name") or self.nom_par_defaut,
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

    def retirer(self) -> None:
        shutil.rmtree(self.dossier_local(), ignore_errors=True)
        self._fichier_ia().unlink(missing_ok=True)

    def a_jour(self, archive: Path) -> bool:
        """La même archive (nom et taille) est déjà installée."""
        modele = self.installe()
        try:
            return modele is not None and modele.get("archive") == archive.name and modele.get("size") == archive.stat().st_size
        except OSError:
            return True  # partage momentanément illisible : on ne touche à rien

    # --- Installation ---

    def en_cours(self) -> Suivi | None:
        return self._suivi

    def signaler(self, erreur: str) -> None:
        """Erreur affichée dans Réglages (par exemple : téléchargement incomplet)."""
        with self._verrou:
            self._suivi = Suivi(erreur=erreur, fini=True)

    def oublier_erreur(self) -> None:
        with self._verrou:
            if self._suivi is not None and self._suivi.fini:
                self._suivi = None

    def _racine_du_modele(self, noms: list[str]) -> str:
        """Dossier de l'archive qui contient le modèle : la racine, ou un seul niveau de sous-dossier."""
        fichiers = {n for n in noms if not n.endswith("/")}
        for prefixe in [""] + sorted({n.split("/")[0] + "/" for n in fichiers if "/" in n}):
            if all(prefixe + f in fichiers for f in self.requis):
                return prefixe
        raise ErreurModele(self.erreur_contenu)

    def _extraire(self, archive: Path, suivi: Suivi) -> str:
        """Extrait dans un dossier temporaire, puis remplace l'ancien modèle d'un coup. Renvoie la racine du modèle."""
        cible = self.dossier_local()
        temporaire = cible.with_name(cible.name + ".part")
        shutil.rmtree(temporaire, ignore_errors=True)
        temporaire.mkdir(parents=True)
        try:
            with zipfile.ZipFile(archive) as z:
                membres = z.infolist()
                racine = self._racine_du_modele([m.filename for m in membres])
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

    def installer(self, archive: Path, nom: str, version: str | None = None, apres: Callable[[], None] | None = None,
                  origine: str = "le dossier partagé") -> bool:
        """Installe l'archive en arrière-plan (progression : en_cours()). False si une installation est déjà en cours."""
        with self._verrou:
            if self._suivi is not None and not self._suivi.fini:
                return False
            try:
                suivi = self._suivi = Suivi(archive=(archive.name, archive.stat().st_size))
            except OSError:
                suivi = self._suivi = Suivi()

        def travail() -> None:
            try:
                taille = archive.stat().st_size
                racine = self._extraire(archive, suivi)
                info = {"name": nom, "version": version or version_de(archive), "archive": archive.name, "size": taille,
                        "root": racine}
                (self.dossier_local() / INFO).write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
                self.publier()
                suivi.progres = 100
                if apres:
                    apres()
            except ErreurModele as e:
                suivi.erreur = str(e)
            except OSError as e:
                suivi.erreur = f"Installation depuis {origine} impossible : {e.strerror or e}"
            finally:
                suivi.fini = True

        threading.Thread(target=travail, name=f"modele-{self.cle}", daemon=True).start()
        return True

    def installer_si_besoin(self, conf: ModelePartage | None, partage: Path | None) -> None:
        """Dossier partagé : installe ou met à jour d'office (appelé à chaque rafraîchissement de la liste des apps)."""
        if conf is None:
            return
        archive = dans_partage(conf, partage)
        if archive is None or self.a_jour(archive):
            self.publier()
            return
        suivi = self._suivi
        if suivi is not None and suivi.fini and suivi.erreur and suivi.archive == (archive.name, archive.stat().st_size):
            return  # même archive déjà refusée : on ne recommence pas en boucle (l'erreur reste affichée)
        self.installer(archive, conf.name, version_de(archive))

    # --- État pour l'interface ---

    def etat(self, conf: ModelePartage | None, partage: Path | None, origine: str, en_attente: bool) -> dict[str, Any]:
        modele = self.installe()
        suivi = self.en_cours()
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


TRANSCRIPTION = TypeModele(
    "transcription", ("config.json", "model.bin"), "Modèle de transcription", "faster-whisper",
    "Cette archive ne contient pas de modèle faster-whisper (config.json et model.bin introuvables).")
INTERVENANTS = TypeModele(
    "intervenants", ("config.yaml",), "Identification des intervenants", "pyannote",
    "Cette archive ne contient pas de modèle pyannote d'identification des intervenants (config.yaml introuvable).")
TYPES = {t.cle: t for t in (TRANSCRIPTION, INTERVENANTS)}

# Compatibilité : le modèle de transcription reste accessible par les fonctions du module.
CLE = TRANSCRIPTION.cle
FICHIER_IA = TRANSCRIPTION.fichier_ia
REQUIS = TRANSCRIPTION.requis
dossier_local = TRANSCRIPTION.dossier_local
installe = TRANSCRIPTION.installe
publier = TRANSCRIPTION.publier
retirer = TRANSCRIPTION.retirer
a_jour = TRANSCRIPTION.a_jour
en_cours = TRANSCRIPTION.en_cours
signaler = TRANSCRIPTION.signaler
oublier_erreur = TRANSCRIPTION.oublier_erreur
installer = TRANSCRIPTION.installer
installer_si_besoin = TRANSCRIPTION.installer_si_besoin
etat = TRANSCRIPTION.etat
