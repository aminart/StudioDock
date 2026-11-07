import json

from app.catalogue import Source, fichier_icone

from conftest import ecrire_catalogue


def test_catalogue_par_defaut_cree_au_premier_lancement(maison):
    source = Source()
    apps = source.lire().apps
    assert (maison / "apps.json").is_file()
    assert [a.id for a in apps] == ["specgen", "audit-ergo", "docanalyser", "mapline"]
    assert source.erreur is None
    # Identifiants = ceux renvoyés par /health de chaque app (contrat commun)
    assert {a.id: a.port for a in apps if a.kind == "web"} == {"specgen": 8010, "audit-ergo": 8501, "docanalyser": 8020}
    assert all(fichier_icone(a) for a in apps)  # icônes livrées
    assert apps[3].icon.style == "logo"


def test_fichier_invalide_garde_la_derniere_version_valide(maison):
    source = Source()
    source.lire()
    (maison / "apps.json").write_text('{"apps": [ {"id": "x", ', encoding="utf-8")
    apps = source.lire().apps
    assert len(apps) == 4
    assert "JSON invalide" in source.erreur

    ecrire_catalogue(maison, [{"id": "a", "name": "A", "exe": "A", "port": 9001},
                              {"id": "b", "name": "B", "exe": "B", "port": 9001}])
    assert len(source.lire().apps) == 4
    assert "port 9001" in source.erreur

    ecrire_catalogue(maison, [{"id": "a", "name": "A", "exe": "A.exe", "port": 9001}])
    apps = source.lire().apps
    assert source.erreur is None and [a.exe for a in apps] == ["A"]


def test_app_web_sans_port_refusee(maison):
    ecrire_catalogue(maison, [{"id": "a", "name": "A", "exe": "A"}])
    source = Source()
    source.lire()
    assert "port" in source.erreur


def test_icone_personnalisee_prioritaire_et_chemins_hors_dossier_refuses(maison):
    (maison / "icons").mkdir()
    (maison / "icons" / "specgen.svg").write_text("<svg/>")
    (maison / "secret.svg").write_text("<svg/>")
    ecrire_catalogue(maison, [
        {"id": "specgen", "name": "S", "exe": "S", "port": 9002, "icon": {"file": "icons/specgen.svg"}},
        {"id": "x", "name": "X", "exe": "X", "port": 9003, "icon": {"file": "../secret.svg"}},
    ])
    apps = Source().lire().apps
    assert fichier_icone(apps[0]) == maison / "icons" / "specgen.svg"
    assert fichier_icone(apps[1]) is None
