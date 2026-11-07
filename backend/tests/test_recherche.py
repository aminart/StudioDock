from app.catalogue import AppEntry
from app.recherche import dossier_web, trouver_native, trouver_web

from conftest import deposer


def _app(**champs):
    return AppEntry(**{"id": "specgen", "name": "SpecGen", "exe": "SpecGenerator", "port": 9010, **champs})


def test_version_la_plus_recente_choisie(maison):
    app = _app()
    assert trouver_web(app) is None
    deposer(maison, "specgen", "SpecGenerator-1.1.0.py")
    deposer(maison, "specgen", "SpecGenerator-1.10.0.py")
    deposer(maison, "specgen", "SpecGenerator-1.9.2.py")
    deposer(maison, "specgen", "SpecGeneratorBeta.py")  # autre programme : ignoré
    trouvee = trouver_web(app)
    assert trouvee.chemin.name == "SpecGenerator-1.10.0.py" and trouvee.version == "1.10.0"


def test_exe_sans_version_et_emplacements(maison):
    app = _app()
    (maison / "SpecGenerator.py").write_text("")
    assert trouver_web(app).chemin == maison / "SpecGenerator.py"
    deposer(maison, "SpecGenerator", "SpecGenerator.py")  # apps\<exe>\ passe avant le dossier racine
    assert trouver_web(app).chemin == maison / "apps" / "SpecGenerator" / "SpecGenerator.py"
    deposer(maison, "specgen", "SpecGenerator.py")  # apps\<id>\ en premier
    assert trouver_web(app).chemin == maison / "apps" / "specgen" / "SpecGenerator.py"
    assert dossier_web(app) == maison / "apps" / "specgen"


def test_emplacement_impose(maison):
    (maison / "ailleurs").mkdir()
    (maison / "ailleurs" / "SpecGenerator-2.0.0.py").write_text("")
    app = _app(path="ailleurs")
    assert trouver_web(app).version == "2.0.0"
    assert dossier_web(app) == maison / "ailleurs"
    assert trouver_web(_app(path="ailleurs/SpecGenerator-2.0.0.py")).chemin.name == "SpecGenerator-2.0.0.py"


def test_app_native_introuvable_ou_imposee(maison):
    app = AppEntry(id="mapline", name="Mapline", kind="native", exe="Mapline")
    assert trouver_native(app) is None
    (maison / "Mapline").mkdir()
    (maison / "Mapline" / "Mapline.exe").write_text("")
    assert trouver_native(AppEntry(id="mapline", name="Mapline", kind="native", exe="Mapline",
                                   path="Mapline")).chemin.name == "Mapline.exe"
