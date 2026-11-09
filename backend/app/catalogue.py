"""Liste des applications affichées par Studio Dock.

Trois sources possibles :
- **catalogue d'équipe** : catalogue.json à la racine du dossier partagé (réglé dans Studio Dock). Chaque app y
  indique le sous-dossier du partage où sont déposées ses versions (« source »). Une copie est gardée sur le poste
  (catalogue.cache.json et cache/), utilisée quand le partage est inaccessible ;
- **catalogue en ligne** : quand l'équipe n'a qu'un dossier en ligne (SharePoint…) que Studio Dock ne peut pas lire,
  le catalogue est téléchargé avec le navigateur (studio-dock-catalogue.zip) et importé dans catalogue-en-ligne/.
  Chaque app y indique sa dernière version (« version ») et le lien de son dossier en ligne (« link ») ;
- **liste locale** : apps.json du dossier de Studio Dock, sans dossier partagé (créé au premier lancement à partir
  de resources/apps.default.json).

Studio Dock n'a aucune application écrite dans son code. Un fichier invalide ne casse rien : la dernière version
valide reste affichée et l'erreur est signalée.
"""
from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app import reglages
from app.info import home_dir, resources_dir

FICHIER = "apps.json"
CATALOGUE_PARTAGE = "catalogue.json"
COPIE_LOCALE = "catalogue.cache.json"
DOSSIER_COPIES = "cache"
DOSSIER_EN_LIGNE = "catalogue-en-ligne"  # catalogue en ligne importé (catalogue.json + icons/)


class Icone(BaseModel):
    file: str | None = None  # chemin relatif au catalogue (dossier partagé ou dossier de Studio Dock)
    style: Literal["symbole", "logo"] = "symbole"  # symbole : posé sur fond Night Navy ; logo : remplit la vignette


class Etape(BaseModel):
    title: str
    text: str = ""


class Lien(BaseModel):
    label: str
    url: str


class AppEntry(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,39}$")
    name: str = Field(min_length=1, max_length=60)
    kind: Literal["web", "native"] = "web"
    port: int | None = Field(default=None, ge=1024, le=65535)
    ai: bool = False
    exe: str = Field(min_length=1)  # nom du programme sans extension ni version, ex. « SpecGenerator »
    source: str | None = None  # catalogue d'équipe : sous-dossier du partage où sont déposées les versions
    mode: Literal["auto", "optionnel", "masque"] = "optionnel"  # catalogue d'équipe
    path: str | None = None  # emplacement imposé (fichier ou dossier), relatif au dossier de Studio Dock
    install_name: str | None = None  # app native : nom dans « Applications installées » de Windows
    tagline: str = ""
    description: str = ""
    points: list[str] = Field(default_factory=list)
    tutorial: list[Etape] = Field(default_factory=list)
    links: list[Lien] = Field(default_factory=list)
    icon: Icone = Field(default_factory=Icone)
    version: str | None = None  # catalogue en ligne : dernière version publiée
    link: str | None = None  # catalogue en ligne : lien du dossier en ligne de l'app (SharePoint…)

    @field_validator("exe")
    @classmethod
    def _sans_extension(cls, valeur: str) -> str:
        return valeur[:-4] if valeur.lower().endswith(".exe") else valeur

    @field_validator("source")
    @classmethod
    def _source_relative(cls, valeur: str | None) -> str | None:
        if valeur and (Path(valeur).is_absolute() or ".." in Path(valeur).parts):
            raise ValueError("« source » est un sous-dossier du dossier partagé (chemin relatif)")
        return valeur

    @model_validator(mode="after")
    def _port_si_web(self) -> "AppEntry":
        if self.kind == "web" and self.port is None:
            raise ValueError(f"{self.id} : une app web doit avoir un port")
        return self


class DockConf(BaseModel):
    source: str = "StudioDock"  # sous-dossier du partage où sont déposées les versions de Studio Dock
    version: str | None = None  # catalogue en ligne : dernière version publiée de Studio Dock
    link: str | None = None  # catalogue en ligne : lien de son dossier en ligne


class Catalogue(BaseModel):
    apps: list[AppEntry] = Field(default_factory=list)
    studiodock: DockConf = Field(default_factory=DockConf)
    link: str | None = None  # catalogue en ligne : lien du fichier studio-dock-catalogue.zip (ou de son dossier)
    published: str | None = None  # catalogue en ligne : date de fabrication du zip (AAAA-MM-JJ HH:MM)

    @model_validator(mode="after")
    def _uniques(self) -> "Catalogue":
        ids, ports = set(), {}
        for app in self.apps:
            if app.id in ids:
                raise ValueError(f"identifiant en double : {app.id}")
            ids.add(app.id)
            if app.port is not None:
                if app.port in ports:
                    raise ValueError(f"port {app.port} utilisé par {ports[app.port]} et {app.id}")
                ports[app.port] = app.id
        return self


def _message(erreur: Exception) -> str:
    if isinstance(erreur, ValidationError):
        details = []
        for e in erreur.errors():
            lieu = ".".join(str(x) for x in e["loc"])
            details.append(f"{lieu} : {e['msg']}" if lieu else e["msg"])
        return " ; ".join(details)
    if isinstance(erreur, json.JSONDecodeError):
        return f"JSON invalide, ligne {erreur.lineno}, colonne {erreur.colno} : {erreur.msg}"
    return str(erreur)


def partage_accessible(dossier: Path | None) -> bool:
    try:
        return bool(dossier) and dossier.is_dir()
    except OSError:
        return False


class Source:
    """Lit le catalogue (partage ou liste locale), le relit quand il change, garde la dernière version valide.

    Attributs pour l'interface : `origine` (« shared », « cache », « online » ou « local »), `erreur`, `partage`."""

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._signature: tuple | None = None
        self._valide = Catalogue()
        self.erreur: str | None = None
        self.origine = "local"
        self.partage: Path | None = None

    @property
    def chemin(self) -> Path:
        """Fichier lu : catalogue du partage, sa copie locale, ou apps.json."""
        if self.origine == "shared" and self.partage:
            return self.partage / CATALOGUE_PARTAGE
        if self.origine == "cache":
            return home_dir() / COPIE_LOCALE
        if self.origine == "online":
            return home_dir() / DOSSIER_EN_LIGNE / CATALOGUE_PARTAGE
        return home_dir() / FICHIER

    def _choisir_fichier(self) -> Path:
        self.partage = reglages.dossier_partage()
        if self.partage is not None:
            if partage_accessible(self.partage) and (self.partage / CATALOGUE_PARTAGE).is_file():
                self.origine = "shared"
            else:
                self.origine = "cache"
            if self.origine == "cache" and not (home_dir() / COPIE_LOCALE).is_file():
                self.origine = "shared"  # rien en copie : on signale l'absence du catalogue partagé
            return self.chemin
        if (home_dir() / DOSSIER_EN_LIGNE / CATALOGUE_PARTAGE).is_file():
            self.origine = "online"
            return self.chemin
        self.origine = "local"
        if not self.chemin.exists():
            self.chemin.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resources_dir() / "resources" / "apps.default.json", self.chemin)
        return self.chemin

    def lire(self) -> Catalogue:
        with self._verrou:
            try:
                fichier = self._choisir_fichier()
                stat = fichier.stat()
            except OSError as e:
                if self.origine == "shared":
                    self.erreur = f"Catalogue introuvable dans le dossier partagé ({self.partage})."
                else:
                    self.erreur = f"{self.chemin} illisible : {e}"
                return self._valide
            signature = (str(fichier), stat.st_mtime, stat.st_size)
            if signature != self._signature:
                self._signature = signature
                try:
                    texte = fichier.read_text(encoding="utf-8")
                    self._valide = Catalogue.model_validate(json.loads(texte))
                    self.erreur = None
                    if self.origine == "shared":
                        self._garder_copie(texte)
                except (OSError, ValueError) as e:  # ValidationError et JSONDecodeError sont des ValueError
                    self.erreur = f"{fichier.name} : {_message(e)}"
            return self._valide

    def _garder_copie(self, texte: str) -> None:
        """Copie locale du catalogue et des icônes, pour afficher les cartes quand le partage est inaccessible."""
        try:
            (home_dir() / COPIE_LOCALE).write_text(texte, encoding="utf-8")
            for app in self._valide.apps:
                if app.icon.file and _relatif_sur(app.icon.file):
                    origine = self.partage / app.icon.file
                    copie = home_dir() / DOSSIER_COPIES / app.icon.file
                    if origine.is_file():
                        copie.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(origine, copie)
        except OSError:
            pass

    def trouver(self, app_id: str) -> AppEntry | None:
        return next((a for a in self.lire().apps if a.id == app_id), None)


def _relatif_sur(chemin: str) -> bool:
    relatif = Path(chemin)
    return not relatif.is_absolute() and ".." not in relatif.parts


def fichier_icone(app: AppEntry, partage: Path | None = None) -> Path | None:
    """Icône de l'app : dossier partagé, sa copie locale, dossier de Studio Dock, sinon icône livrée."""
    if not app.icon.file or not _relatif_sur(app.icon.file):
        return None
    bases = [home_dir() / DOSSIER_COPIES, home_dir() / DOSSIER_EN_LIGNE, home_dir(), resources_dir() / "resources"]
    if partage is not None:
        bases.insert(0, partage)
    for base in bases:
        try:
            chemin = base / app.icon.file
            if chemin.is_file():
                return chemin
        except OSError:
            continue
    return None
