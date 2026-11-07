# Recette PyInstaller de StudioDock.exe (workflow « Build Windows exe », ou : pyinstaller --noconfirm StudioDock.spec).
# Prérequis : l'interface compilée (cd frontend && npm ci && npm run build).
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
