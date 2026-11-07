# Recette PyInstaller de Studio Dock (workflows « Build Windows exe » et « Build Mac app »,
# ou : pyinstaller --noconfirm StudioDock.spec) : StudioDock.exe sous Windows, « Studio Dock.app » sur Mac.
# Prérequis : l'interface compilée (cd frontend && npm ci && npm run build).
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# Version : fichier VERSION (source unique), embarqué et affiché dans Propriétés > Détails sous Windows.
VERSION = Path("VERSION").read_text(encoding="utf-8").strip()
try:
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct, VSVersionInfo,
    )
except ImportError:  # hors Windows : pas de ressource de version, la fabrication continue
    version_info = None
else:
    _nombres = tuple(int(partie) for partie in VERSION.split("-")[0].split(".")) + (0,)
    version_info = VSVersionInfo(
        ffi=FixedFileInfo(filevers=_nombres[:4], prodvers=_nombres[:4]),
        kids=[
            StringFileInfo([StringTable("040C04B0", [
                StringStruct("ProductName", "Studio Dock"),
                StringStruct("FileDescription", "Studio Dock - lanceur des applications UX"),
                StringStruct("ProductVersion", VERSION),
                StringStruct("FileVersion", VERSION),
                StringStruct("OriginalFilename", "StudioDock.exe"),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x040C, 1200])]),
        ],
    )

if not Path("frontend/dist/index.html").is_file():
    raise SystemExit("Interface absente : lancer d'abord « npm ci && npm run build » dans frontend/.")

datas = [
    ("VERSION", "."),
    ("frontend/dist", "frontend_dist"),
    ("resources/apps.default.json", "resources"),
    ("resources/icons", "resources/icons"),
]
hiddenimports = collect_submodules("uvicorn") + collect_submodules("app")
try:
    hiddenimports += collect_submodules("webview")
except Exception:  # noqa: BLE001 : pywebview absent (fabrication hors Windows)
    pass

a = Analysis(
    ["backend/launcher.py"],
    pathex=["backend"],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "pytest"],
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    # Mac : application « Studio Dock.app » (dossier, démarrage rapide), pour Intel ou puce Apple selon la machine
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="StudioDock",
        console=False,
        upx=False,
    )
    coll = COLLECT(exe, a.binaries, a.datas, name="StudioDock", upx=False)
    app = BUNDLE(
        coll,
        name="Studio Dock.app",
        icon="resources/studiodock.icns",
        bundle_identifier="fr.aminart.studiodock",
        version=VERSION,
        info_plist={
            "CFBundleName": "Studio Dock",
            "CFBundleDisplayName": "Studio Dock",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "LSMinimumSystemVersion": "12.0",
            "NSHighResolutionCapable": True,
            # Interface servie en local (http://127.0.0.1) : autorisée dans la fenêtre WebKit
            "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="StudioDock",
        version=version_info,
        icon="resources/studiodock.ico",
        console=False,  # une fenêtre, pas de console noire
        upx=False,
    )
