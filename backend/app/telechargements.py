"""Catalogue en ligne : le navigateur télécharge, Studio Dock installe.

Quand l'équipe n'a qu'un dossier en ligne (SharePoint, Teams…) protégé par la connexion de l'entreprise, Studio
Dock ne s'y connecte pas : il ouvre le bon lien dans le navigateur (où la connexion se fait toute seule), puis
surveille le dossier Téléchargements. Ce qui y arrive est vérifié (nom attendu, téléchargement terminé), copié
dans le dossier d'installation, puis retiré des Téléchargements. Rien n'est jamais lancé depuis Téléchargements.

- studio-dock-catalogue*.zip : catalogue de l'équipe (catalogue.json + icons/), importé dès qu'il apparaît ;
- l'exe (ou l'installateur) d'une app : pris seulement quand on a cliqué sur « Installer » ou « Mettre à jour » ;
- StudioDock*.exe : pris quand on a demandé la mise à jour de Studio Dock.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path, PurePosixPath

from app.catalogue import CATALOGUE_PARTAGE, DOSSIER_EN_LIGNE, AppEntry, Catalogue, _message
from app.info import home_dir
from app.recherche import Trouvee, _cle_version, _est_installateur, _est_programme, _nom_sans_extension

PREFIXE_CATALOGUE = "studio-dock-catalogue"
EN_COURS = (".crdownload", ".part", ".partial", ".download", ".tmp", ".opdownload")
DUREE_ATTENTE = 30 * 60  # une demande de téléchargement est oubliée au bout de 30 minutes
DOUBLON = re.compile(r"\s*\(\d+\)$")  # « SpecGenerator-1.2.0 (1) » : copie renommée par le navigateur
MAX_CATALOGUE = 20 * 1024 * 1024


def dossier_telechargements() -> Path:
    """Dossier Téléchargements de la personne (Windows : celui réglé dans l'Explorateur, même déplacé)."""
    if autre := os.environ.get("STUDIODOCK_DOWNLOADS", "").strip():
        return Path(autre)
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                            ("Data4", ctypes.c_ubyte * 8)]

            # FOLDERID_Downloads {374DE290-123F-4565-9164-39C4925E467B}
            guid = GUID(0x374DE290, 0x123F, 0x4565, (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B))
            chemin = ctypes.c_wchar_p()
            shell32 = ctypes.windll.shell32
            if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(chemin)) == 0:
                resultat = Path(chemin.value)
                ctypes.windll.ole32.CoTaskMemFree(chemin)
                return resultat
        except (OSError, AttributeError):
            pass
    return Path.home() / "Downloads"


def nom_de_base(f: Path) -> str:
    """Nom sans extension et sans le « (1) » ajouté par le navigateur aux doublons."""
    base = _nom_sans_extension(f) if f.suffix.lower() in (".exe", ".py") else f.stem
    return DOUBLON.sub("", base)


def _commence_par(base: str, prefixe: str) -> bool:
    base, prefixe = base.lower().replace(" ", ""), prefixe.lower().replace(" ", "")
    return base.startswith(prefixe) and (len(base) == len(prefixe) or not base[len(prefixe)].isalpha())


class Telechargements:
    """Demandes de téléchargement en attente et fichiers repérés dans Téléchargements."""

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self.attentes: dict[str, float] = {}  # id d'app, « catalogue » ou « studiodock » → instant de la demande
        self._tailles: dict[str, tuple[int, float]] = {}  # fichier → (taille, mtime) au passage précédent
        self.dernier_import: str | None = None  # message après l'import d'un catalogue
        self.erreur_catalogue: str | None = None

    # --- demandes ---------------------------------------------------------------------------------------------

    def attendre(self, cle: str) -> None:
        with self._verrou:
            self.attentes[cle] = time.time()

    def annuler(self, cle: str) -> None:
        with self._verrou:
            self.attentes.pop(cle, None)

    def en_attente(self, cle: str) -> bool:
        with self._verrou:
            debut = self.attentes.get(cle)
            if debut is not None and time.time() - debut > DUREE_ATTENTE:
                self.attentes.pop(cle, None)
                return False
            return debut is not None

    # --- fichiers ---------------------------------------------------------------------------------------------

    def _termine(self, f: Path) -> bool:
        """Téléchargement fini : pas de fichier « .crdownload » à côté, taille stable depuis le passage précédent."""
        try:
            stat = f.stat()
        except OSError:
            return False
        if any((f.parent / (f.name + ext)).exists() for ext in EN_COURS):
            return False
        cle = str(f)
        precedent = self._tailles.get(cle)
        self._tailles[cle] = (stat.st_size, stat.st_mtime)
        if stat.st_size == 0 or en_cours_d_ecriture(f):
            return False
        # Stable depuis le passage précédent, ou pas modifié depuis 3 secondes (Studio Dock vient de démarrer).
        # Une copie par l'Explorateur garde la date d'origine : c'est le verrou ci-dessus qui la repère.
        return precedent == (stat.st_size, stat.st_mtime) or time.time() - stat.st_mtime > 3

    def fichiers(self, prefixe: str, accepte) -> list[Path]:
        """Fichiers terminés de Téléchargements dont le nom commence par `prefixe` et que `accepte` retient."""
        dossier = dossier_telechargements()
        try:
            candidats = [f for f in dossier.iterdir() if f.is_file()]
        except OSError:
            return []
        retenus = []
        for f in candidats:
            if f.name.lower().endswith(EN_COURS) or not _commence_par(nom_de_base(f), prefixe):
                continue
            if accepte(f) and self._termine(f):
                retenus.append(f)
        return retenus

    def plus_recent(self, fichiers: list[Path]) -> Trouvee | None:
        """Version la plus haute (d'après le nom), puis le plus récemment téléchargé."""
        if not fichiers:
            return None
        def cle(f: Path):
            version = _version(f)
            return (_cle_version(version), f.stat().st_mtime)
        meilleur = max(fichiers, key=cle)
        return Trouvee(meilleur, _version(meilleur))

    def programme_de(self, app: AppEntry) -> Trouvee | None:
        """Exe (app web) ou installateur (app native) d'une app, arrivé dans Téléchargements."""
        if app.kind == "web":
            accepte = _est_programme
        else:
            accepte = lambda f: _est_installateur(f) or _est_programme(f)  # noqa: E731
        trouvee = self.plus_recent(self.fichiers(app.exe, accepte))
        if trouvee is None and app.kind == "native" and app.install_name:
            trouvee = self.plus_recent(self.fichiers(app.install_name, accepte))
        return trouvee

    def studio_dock(self) -> Trouvee | None:
        return self.plus_recent(self.fichiers("StudioDock", _est_programme))

    def catalogue(self) -> Path | None:
        zips = self.fichiers(PREFIXE_CATALOGUE, lambda f: f.suffix.lower() == ".zip")
        return max(zips, key=lambda f: f.stat().st_mtime) if zips else None


def en_cours_d_ecriture(f: Path) -> bool:
    """Windows : un autre programme a encore le fichier ouvert en écriture (copie de l'Explorateur, navigateur,
    antivirus) ; l'ouvrir sans partage échoue alors. Ailleurs : False."""
    if sys.platform != "win32":
        return False
    import ctypes

    GENERIC_READ, OPEN_EXISTING, INVALID = 0x80000000, 3, ctypes.c_void_p(-1).value
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateFileW.restype = ctypes.c_void_p
    poignee = kernel32.CreateFileW(str(f), GENERIC_READ, 0, None, OPEN_EXISTING, 0, None)  # 0 : aucun partage
    if poignee in (None, INVALID):
        return True
    kernel32.CloseHandle(ctypes.c_void_p(poignee))
    return False


def empreinte(f: Path) -> str:
    """SHA-256 d'un fichier (contrôle qu'un téléchargement est complet et identique à la version publiée)."""
    import hashlib

    h = hashlib.sha256()
    with open(f, "rb") as entree:
        for bloc in iter(lambda: entree.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def conforme(f: Path, taille: int | None, sha256: str | None) -> str | None:
    """None si le fichier correspond à la version publiée (taille, empreinte), sinon la raison."""
    if taille is not None and f.stat().st_size != taille:
        return (f"{f.name} fait {f.stat().st_size:,} octets au lieu de {taille:,} : téléchargement incomplet "
                "ou fichier différent de celui publié. Retéléchargez-le.").replace(",", " ")
    if sha256 and empreinte(f).lower() != sha256.lower():
        return f"{f.name} est différent de la version publiée (empreinte). Retéléchargez-le."
    return None


def _version(f: Path) -> str | None:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", nom_de_base(f))
    return ".".join(m.groups()) if m else None


def retirer(f: Path) -> None:
    """Retire un fichier des Téléchargements une fois copié (s'il est encore ouvert, il reste)."""
    try:
        f.unlink()
    except OSError:
        pass


class ErreurCatalogue(Exception):
    pass


def importer_catalogue(archive: Path) -> Catalogue:
    """Vérifie puis installe un catalogue téléchargé : catalogue.json valide, seulement des icônes à côté.

    Le catalogue précédent n'est remplacé qu'une fois le nouveau entièrement extrait."""
    try:
        if archive.stat().st_size > MAX_CATALOGUE:
            raise ErreurCatalogue("Fichier trop gros pour un catalogue.")
        with zipfile.ZipFile(archive) as z:
            noms = [n for n in z.namelist() if not n.endswith("/")]
            racine = _racine(noms)
            if f"{racine}{CATALOGUE_PARTAGE}" not in noms:
                raise ErreurCatalogue("Le zip ne contient pas de catalogue.json.")
            texte = z.read(f"{racine}{CATALOGUE_PARTAGE}").decode("utf-8")
            try:
                catalogue = Catalogue.model_validate(json.loads(texte))
            except ValueError as e:
                raise ErreurCatalogue(f"catalogue.json : {_message(e)}") from e
            cible = home_dir() / DOSSIER_EN_LIGNE
            cible.parent.mkdir(parents=True, exist_ok=True)
            temporaire = Path(tempfile.mkdtemp(prefix="catalogue-", dir=cible.parent))
            try:
                (temporaire / CATALOGUE_PARTAGE).write_text(texte, encoding="utf-8")
                for nom in noms:
                    relatif = PurePosixPath(nom[len(racine):])
                    if (relatif.parts[:1] != ("icons",) or ".." in relatif.parts or relatif.is_absolute()
                            or len(relatif.parts) < 2):
                        continue  # seuls catalogue.json et icons/ sont repris
                    destination = temporaire.joinpath(*relatif.parts)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(z.read(nom))
                ancien = cible.with_name(DOSSIER_EN_LIGNE + ".old")
                shutil.rmtree(ancien, ignore_errors=True)
                if cible.exists():
                    cible.rename(ancien)
                temporaire.rename(cible)
                shutil.rmtree(ancien, ignore_errors=True)
            finally:
                shutil.rmtree(temporaire, ignore_errors=True)
    except zipfile.BadZipFile as e:
        raise ErreurCatalogue("Ce fichier n'est pas un zip valide (téléchargement incomplet ?).") from e
    except OSError as e:
        raise ErreurCatalogue(f"Import impossible : {e}") from e
    return catalogue


def _racine(noms: list[str]) -> str:
    """Dossier racine commun du zip (« Studio Dock/ » si le zip contient un dossier), sinon chaîne vide."""
    if any(PurePosixPath(n).name == CATALOGUE_PARTAGE and "/" not in n for n in noms):
        return ""
    for n in noms:
        if PurePosixPath(n).name == CATALOGUE_PARTAGE and n.count("/") == 1:
            return n.split("/")[0] + "/"
    return ""


# --- Préparer le catalogue (côté administratrice) -----------------------------------------------------------

def preparer(dossier: Path) -> dict:
    """Lit le dossier de préparation (copie locale du dossier en ligne) : catalogue.json, icônes, et la dernière
    version déposée dans le sous-dossier de chaque app et de Studio Dock."""
    from app.recherche import _plus_recent, trouver_dans_partage

    texte = (dossier / CATALOGUE_PARTAGE).read_text(encoding="utf-8")
    catalogue = Catalogue.model_validate(json.loads(texte))
    apps = []
    for app in catalogue.apps:
        trouvee = trouver_dans_partage(app, dossier)
        icone = bool(app.icon.file) and (dossier / app.icon.file).is_file()
        apps.append({"id": app.id, "name": app.name, "source": app.source or app.id, "mode": app.mode,
                     "found": trouvee.chemin.name if trouvee else None,
                     "version": trouvee.version if trouvee else app.version,
                     "size": trouvee.chemin.stat().st_size if trouvee else None,
                     "_chemin": str(trouvee.chemin) if trouvee else None,
                     "link": app.link or "", "icon": icone})
    dock = dossier / catalogue.studiodock.source
    fichiers = [f for f in dock.iterdir() if _commence_par(nom_de_base(f), "StudioDock") and _est_programme(f)] \
        if dock.is_dir() else []
    trouvee = _plus_recent(fichiers)
    return {
        "apps": apps,
        "studiodock": {"source": catalogue.studiodock.source, "found": trouvee.chemin.name if trouvee else None,
                       "version": trouvee.version if trouvee else catalogue.studiodock.version,
                       "size": trouvee.chemin.stat().st_size if trouvee else None,
                       "_chemin": str(trouvee.chemin) if trouvee else None,
                       "link": catalogue.studiodock.link or ""},
        "link": catalogue.link or "",
        "published": catalogue.published,
    }


def fabriquer(dossier: Path, liens: dict[str, str], lien_dock: str, lien_catalogue: str) -> Path:
    """Écrit les versions et les liens dans catalogue.json, puis fabrique studio-dock-catalogue.zip à côté."""
    etat = preparer(dossier)
    donnees = json.loads((dossier / CATALOGUE_PARTAGE).read_text(encoding="utf-8"))
    trouvees = {a["id"]: a for a in etat["apps"]}

    def _publier(cible: dict, info: dict) -> None:
        """Version, taille et empreinte du fichier publié : Studio Dock vérifie ainsi chaque téléchargement."""
        if info.get("version"):
            cible["version"] = info["version"]
        if info.get("_chemin"):
            cible["size"] = info["size"]
            cible["sha256"] = empreinte(Path(info["_chemin"]))
        else:
            cible.pop("size", None)
            cible.pop("sha256", None)

    for app in donnees.get("apps", []):
        if app.get("id") in trouvees:
            _publier(app, trouvees[app["id"]])
        if (lien := (liens.get(app.get("id")) or "").strip()):
            app["link"] = lien
    dock = donnees.setdefault("studiodock", {})
    _publier(dock, etat["studiodock"])
    if lien_dock.strip():
        dock["link"] = lien_dock.strip()
    if lien_catalogue.strip():
        donnees["link"] = lien_catalogue.strip()
    donnees["published"] = time.strftime("%Y-%m-%d %H:%M")
    texte = json.dumps(donnees, ensure_ascii=False, indent=2) + "\n"
    catalogue = Catalogue.model_validate(json.loads(texte))  # refuse un catalogue invalide avant d'écrire
    (dossier / CATALOGUE_PARTAGE).write_text(texte, encoding="utf-8")
    archive = dossier / f"{PREFIXE_CATALOGUE}.zip"
    temporaire = archive.with_suffix(".zip.part")
    with zipfile.ZipFile(temporaire, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(CATALOGUE_PARTAGE, texte)
        icones = {a.icon.file for a in catalogue.apps if a.icon.file}
        for relatif in sorted(icones):
            chemin = dossier / relatif
            if chemin.is_file() and PurePosixPath(relatif).parts[:1] == ("icons",):
                z.write(chemin, relatif)
    temporaire.replace(archive)
    return archive
