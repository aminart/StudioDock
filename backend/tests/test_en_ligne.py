"""Catalogue en ligne : catalogue et apps téléchargés par le navigateur, récupérés dans Téléchargements."""
import json
import os
import shutil
import time
import zipfile
from pathlib import Path

from conftest import ICI, port_libre

LIEN_CATALOGUE = "https://entreprise.sharepoint.com/sites/ux/Studio%20Dock"


def _catalogue(port: int, version: str = "1.2.0") -> dict:
    return {
        "link": LIEN_CATALOGUE,
        "published": "2026-11-09 10:00",
        "studiodock": {"version": "0.0.1", "link": "https://entreprise.sharepoint.com/StudioDock"},
        "apps": [{
            "id": "proto", "name": "Proto", "kind": "web", "port": port, "exe": "Proto", "mode": "optionnel", "source": "Proto",
            "version": version, "link": "https://entreprise.sharepoint.com/sites/ux/Proto",
            "icon": {"file": "icons/proto.svg", "style": "logo"},
        }],
    }


def _zip(dossier: Path, donnees: dict, nom: str = "studio-dock-catalogue.zip") -> Path:
    archive = dossier / nom
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("catalogue.json", json.dumps(donnees))
        z.writestr("icons/proto.svg", "<svg xmlns='http://www.w3.org/2000/svg'/>")
        z.writestr("../evasion.txt", "non")
    ancien = time.time() - 10  # téléchargement terminé depuis un moment
    os.utime(archive, (ancien, ancien))
    return archive


def _attendre(condition, delai=10.0):
    fin = time.monotonic() + delai
    while time.monotonic() < fin:
        if condition():
            return True
        time.sleep(0.1)
    return False


def test_catalogue_telecharge_importe(client, maison):
    archive = _zip(maison / "Telechargements", _catalogue(port_libre()))
    etat = client.get("/api/apps").json()
    assert etat["source"] == "online"
    assert [a["id"] for a in etat["apps"]] == ["proto"]
    assert etat["online"]["published"] == "2026-11-09 10:00"
    assert etat["online"]["link"] == LIEN_CATALOGUE
    assert not archive.exists()  # retiré des Téléchargements
    assert (maison / "catalogue-en-ligne" / "icons" / "proto.svg").is_file()
    assert not (maison / "evasion.txt").exists()
    assert etat["apps"][0]["iconUrl"]
    assert etat["apps"][0]["availableVersion"] == "1.2.0" and not etat["apps"][0]["installed"]


def test_catalogue_invalide_signale_puis_ignore(client, maison):
    archive = maison / "Telechargements" / "studio-dock-catalogue (1).zip"
    archive.write_bytes(b"pas un zip")
    os.utime(archive, (time.time() - 10, time.time() - 10))
    etat = client.get("/api/apps").json()
    assert etat["source"] == "local"
    assert "Catalogue illisible" in etat["online"]["error"]
    assert archive.exists()  # laissé en place : c'est à la personne de le retélécharger


def test_installer_une_app_depuis_le_navigateur(client, maison):
    _zip(maison / "Telechargements", _catalogue(port_libre()))
    client.get("/api/apps")

    carte = client.post("/api/apps/proto/install").json()
    assert carte["waiting"] is True
    assert client.ouverts == ["https://entreprise.sharepoint.com/sites/ux/Proto"]

    # Téléchargement en cours : pas encore pris
    telech = maison / "Telechargements"
    (telech / "Proto-1.2.0 (1).py.crdownload").write_text("…")
    shutil.copyfile(ICI / "fausse_app.py", telech / "Proto-1.2.0 (1).py")
    client.get("/api/apps")
    assert (telech / "Proto-1.2.0 (1).py").exists()

    # Terminé : copié dans le dossier d'installation (sans le « (1) »), puis retiré des Téléchargements
    (telech / "Proto-1.2.0 (1).py.crdownload").unlink()
    ancien = time.time() - 10
    os.utime(telech / "Proto-1.2.0 (1).py", (ancien, ancien))
    client.get("/api/apps")
    assert _attendre(lambda: (maison / "apps" / "proto" / "Proto-1.2.0.py").is_file()
                     and not (telech / "Proto-1.2.0 (1).py").exists())
    carte = next(a for a in client.get("/api/apps").json()["apps"] if a["id"] == "proto")
    assert carte["installed"] and carte["version"] == "1.2.0" and not carte["waiting"] and not carte["update"]


def test_fichier_ignore_sans_demande(client, maison):
    _zip(maison / "Telechargements", _catalogue(port_libre()))
    client.get("/api/apps")
    fichier = maison / "Telechargements" / "Proto-1.2.0.py"
    shutil.copyfile(ICI / "fausse_app.py", fichier)
    os.utime(fichier, (time.time() - 10, time.time() - 10))
    client.get("/api/apps")
    time.sleep(0.3)
    assert fichier.exists() and not (maison / "apps" / "proto").exists()


def test_mise_a_jour_signalee_par_le_catalogue(client, maison):
    from conftest import deposer

    _zip(maison / "Telechargements", _catalogue(port_libre(), version="2.0.0"))
    deposer(maison, "proto", "Proto-1.2.0.py")
    carte = next(a for a in client.get("/api/apps").json()["apps"] if a["id"] == "proto")
    assert carte["installed"] and carte["update"] and carte["availableVersion"] == "2.0.0"


def test_verifier_les_mises_a_jour_ouvre_le_lien(client, maison):
    assert client.post("/api/catalogue/check").status_code == 409  # aucun lien connu
    client.put("/api/settings", json={"catalogue_link": LIEN_CATALOGUE})
    assert client.post("/api/catalogue/check").status_code == 200
    assert client.ouverts == [LIEN_CATALOGUE]
    assert client.get("/api/apps").json()["online"]["waiting"] is True


def test_preparer_et_fabriquer_le_catalogue(client, maison, tmp_path):
    prep = tmp_path / "preparation"
    (prep / "icons").mkdir(parents=True)
    (prep / "icons" / "proto.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    (prep / "Proto").mkdir()
    shutil.copyfile(ICI / "fausse_app.py", prep / "Proto" / "Proto-3.1.0.py")
    (prep / "StudioDock").mkdir()
    donnees = _catalogue(port_libre())
    del donnees["link"], donnees["apps"][0]["link"], donnees["apps"][0]["version"]
    (prep / "catalogue.json").write_text(json.dumps(donnees), encoding="utf-8")

    etat = client.post("/api/admin/catalogue", json={"folder": str(prep)}).json()
    assert etat["apps"][0]["version"] == "3.1.0" and etat["apps"][0]["found"] == "Proto-3.1.0.py"

    r = client.post("/api/admin/catalogue/build", json={
        "folder": str(prep), "links": {"proto": "https://sp/Proto"}, "catalogueLink": LIEN_CATALOGUE})
    assert r.status_code == 200, r.text
    archive = Path(r.json()["zip"])
    with zipfile.ZipFile(archive) as z:
        assert sorted(z.namelist()) == ["catalogue.json", "icons/proto.svg"]
        publie = json.loads(z.read("catalogue.json"))
    assert publie["apps"][0]["version"] == "3.1.0" and publie["apps"][0]["link"] == "https://sp/Proto"
    assert publie["link"] == LIEN_CATALOGUE and publie["published"]
    import hashlib
    assert publie["apps"][0]["size"] == (prep / "Proto" / "Proto-3.1.0.py").stat().st_size
    assert publie["apps"][0]["sha256"] == hashlib.sha256((prep / "Proto" / "Proto-3.1.0.py").read_bytes()).hexdigest()
    assert "_chemin" not in r.json()["apps"][0]

    # Le zip fabriqué est celui que les membres importent
    shutil.copyfile(archive, maison / "Telechargements" / archive.name)
    os.utime(maison / "Telechargements" / archive.name, (time.time() - 10, time.time() - 10))
    etat = client.get("/api/apps").json()
    assert etat["source"] == "online" and etat["apps"][0]["availableVersion"] == "3.1.0"


def test_telechargement_incomplet_refuse(client, maison):
    donnees = _catalogue(port_libre())
    donnees["apps"][0]["size"] = (ICI / "fausse_app.py").stat().st_size + 1000  # le fichier publié est plus gros
    _zip(maison / "Telechargements", donnees)
    client.get("/api/apps")
    client.post("/api/apps/proto/install")
    fichier = maison / "Telechargements" / "Proto-1.2.0.py"
    shutil.copyfile(ICI / "fausse_app.py", fichier)
    os.utime(fichier, (time.time() - 10, time.time() - 10))
    carte = next(a for a in client.get("/api/apps").json()["apps"] if a["id"] == "proto")
    assert "incomplet" in carte["installError"]
    assert not carte["installed"] and not carte["waiting"]
    assert fichier.exists()  # laissé en place
    assert not (maison / "apps" / "proto").exists()


def test_empreinte_verifiee(client, maison):
    donnees = _catalogue(port_libre())
    donnees["apps"][0]["size"] = (ICI / "fausse_app.py").stat().st_size
    donnees["apps"][0]["sha256"] = "0" * 64
    _zip(maison / "Telechargements", donnees)
    client.get("/api/apps")
    client.post("/api/apps/proto/install")
    fichier = maison / "Telechargements" / "Proto-1.2.0.py"
    shutil.copyfile(ICI / "fausse_app.py", fichier)
    os.utime(fichier, (time.time() - 10, time.time() - 10))
    carte = next(a for a in client.get("/api/apps").json()["apps"] if a["id"] == "proto")
    assert "différent" in carte["installError"]
