"""Trouver l'exe d'une app et sa version.

App web : dans apps\\<id>\\ (ou apps\\<exe>\\, ou à côté de Studio Dock), un fichier « <exe>*.exe ».
Plusieurs versions côte à côte (SpecGenerator-1.1.0.exe, SpecGenerator-1.2.0.exe) : la plus récente gagne.
App native : emplacement imposé, sinon programme installé (registre Windows), sinon dossiers d'installation usuels.
"""
from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app import winapi
from app.catalogue import AppEntry
from app.info import home_dir

VERSION_NOM = re.compile(r"(\d+)\.(\d+)\.(\d+)")
# .py : apps de test et de développement, lancées avec l'interpréteur Python
EXTENSIONS = (".exe",) if winapi.IS_WIN else (".exe", ".py")


@dataclass
class Trouvee:
    chemin: Path
    version: str | None


def _cle_version(version: str | None) -> tuple[int, ...]:
    m = VERSION_NOM.search(version or "")
    return tuple(int(x) for x in m.groups()) if m else (-1,)


def _resoudre(relatif: str) -> Path:
    chemin = Path(os.path.expandvars(relatif)).expanduser()
    return chemin if chemin.is_absolute() else home_dir() / chemin


def _candidats(dossier: Path, exe: str) -> list[Path]:
    if not dossier.is_dir():
        return []
    prefixe = exe.lower()
    return [f for f in dossier.iterdir()
            if f.is_file() and f.suffix.lower() in EXTENSIONS and f.name.lower().startswith(prefixe)
            and (len(f.stem) == len(prefixe) or not f.stem[len(prefixe)].isalpha())]


def _version_de(chemin: Path) -> str | None:
    m = VERSION_NOM.search(chemin.stem)
    if m:
        return ".".join(m.groups())
    return _version_fichier_cache(chemin)


_cache_versions: dict[tuple[str, float], str | None] = {}


def _version_fichier_cache(chemin: Path) -> str | None:
    try:
        cle = (str(chemin), chemin.stat().st_mtime)
    except OSError:
        return None
    if cle not in _cache_versions:
        _cache_versions[cle] = winapi.version_fichier(chemin)
    return _cache_versions[cle]


def _plus_recent(fichiers: list[Path]) -> Trouvee | None:
    if not fichiers:
        return None
    tries = sorted(fichiers, key=lambda f: (_cle_version(_version_de(f)), f.stat().st_mtime), reverse=True)
    return Trouvee(tries[0], _version_de(tries[0]))


def trouver_web(app: AppEntry) -> Trouvee | None:
    if app.path:
        cible = _resoudre(app.path)
        if cible.is_file():
            return Trouvee(cible, _version_de(cible))
        return _plus_recent(_candidats(cible, app.exe))
    for dossier in (home_dir() / "apps" / app.id, home_dir() / "apps" / app.exe, home_dir()):
        if trouvee := _plus_recent(_candidats(dossier, app.exe)):
            return trouvee
    return None


def dossier_web(app: AppEntry) -> Path:
    """Où déposer l'exe d'une app web."""
    if app.path:
        cible = _resoudre(app.path)
        return cible.parent if cible.suffix else cible
    return home_dir() / "apps" / app.id


_cache_installees: tuple[float, list[dict[str, str]]] = (0.0, [])


def _installees() -> list[dict[str, str]]:
    global _cache_installees
    if time.monotonic() - _cache_installees[0] > 30:
        _cache_installees = (time.monotonic(), winapi.applications_installees())
    return _cache_installees[1]


def trouver_native(app: AppEntry) -> Trouvee | None:
    nom_exe = app.exe + ".exe"
    if app.path:
        cible = _resoudre(app.path)
        if cible.is_dir():
            cible = cible / nom_exe
        return Trouvee(cible, _version_de(cible)) if cible.is_file() else None

    nom_installe = (app.install_name or app.name).lower()
    for prog in _installees():
        if not prog["DisplayName"].lower().startswith(nom_installe):
            continue
        possibles = []
        if prog.get("InstallLocation"):
            possibles.append(Path(prog["InstallLocation"].strip('"')) / nom_exe)
        if prog.get("DisplayIcon"):
            icone = prog["DisplayIcon"].split(",")[0].strip('"')
            if icone.lower().endswith(".exe"):
                possibles.append(Path(icone))
        for chemin in possibles:
            if chemin.is_file():
                return Trouvee(chemin, prog.get("DisplayVersion") or _version_de(chemin))

    if sys.platform == "win32":
        bases = [os.environ.get("LOCALAPPDATA", ""), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
                 os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")]
        for base in filter(None, bases):
            chemin = Path(base) / app.name / nom_exe
            if chemin.is_file():
                return Trouvee(chemin, _version_de(chemin))
    return None
