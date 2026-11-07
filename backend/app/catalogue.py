"""Liste des applications affichées par Studio Dock : fichier apps.json du dossier de Studio Dock.

Studio Dock n'a aucune application écrite dans son code : cartes et fiches viennent toutes de ce fichier.
Au premier lancement, il est créé à partir de resources/apps.default.json.

Un fichier invalide ne casse rien : la dernière version valide reste affichée et l'erreur est signalée.
"""
from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from app.info import home_dir, resources_dir

FICHIER = "apps.json"


class Icone(BaseModel):
    file: str | None = None  # chemin relatif au dossier de Studio Dock (sinon : icône livrée)
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
    exe: str = Field(min_length=1)  # nom de l'exe sans « .exe » ni version, ex. « SpecGenerator »
    path: str | None = None  # emplacement imposé (fichier ou dossier), relatif au dossier de Studio Dock
    install_name: str | None = None  # app native : nom dans « Applications installées » de Windows
    tagline: str = ""
    description: str = ""
    points: list[str] = Field(default_factory=list)
    tutorial: list[Etape] = Field(default_factory=list)
    links: list[Lien] = Field(default_factory=list)
    icon: Icone = Field(default_factory=Icone)

    @field_validator("exe")
    @classmethod
    def _sans_extension(cls, valeur: str) -> str:
        return valeur[:-4] if valeur.lower().endswith(".exe") else valeur

    @model_validator(mode="after")
    def _port_si_web(self) -> "AppEntry":
        if self.kind == "web" and self.port is None:
            raise ValueError(f"{self.id} : une app web doit avoir un port")
        return self


class Catalogue(BaseModel):
    apps: list[AppEntry] = Field(default_factory=list)

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


class Source:
    """Lit apps.json, le relit quand il change, garde la dernière version valide."""

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._signature: tuple[float, int] | None = None
        self._valide = Catalogue()
        self.erreur: str | None = None

    @property
    def chemin(self) -> Path:
        return home_dir() / FICHIER

    def _creer_si_absent(self) -> None:
        if not self.chemin.exists():
            self.chemin.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resources_dir() / "resources" / "apps.default.json", self.chemin)

    def lire(self) -> Catalogue:
        with self._verrou:
            try:
                self._creer_si_absent()
                stat = self.chemin.stat()
            except OSError as e:
                self.erreur = f"{self.chemin} illisible : {e}"
                return self._valide
            signature = (stat.st_mtime, stat.st_size)
            if signature != self._signature:
                self._signature = signature
                try:
                    self._valide = Catalogue.model_validate(json.loads(self.chemin.read_text(encoding="utf-8")))
                    self.erreur = None
                except (OSError, ValueError) as e:  # ValidationError et JSONDecodeError sont des ValueError
                    self.erreur = f"{FICHIER} : {_message(e)}"
            return self._valide

    def trouver(self, app_id: str) -> AppEntry | None:
        return next((a for a in self.lire().apps if a.id == app_id), None)


def fichier_icone(app: AppEntry) -> Path | None:
    """Icône de l'app : fichier du dossier de Studio Dock, sinon celle livrée avec Studio Dock."""
    if not app.icon.file:
        return None
    relatif = Path(app.icon.file)
    if relatif.is_absolute() or ".." in relatif.parts:
        return None
    for base in (home_dir(), resources_dir() / "resources"):
        chemin = base / relatif
        if chemin.is_file():
            return chemin
    return None
