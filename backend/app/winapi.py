"""Ce qui dépend de Windows : groupe de processus, ouverture de liens, premier plan, versions, registre.

Hors Windows (développement, tests), chaque fonction a un équivalent simple ou ne fait rien.
"""
from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path

IS_WIN = sys.platform == "win32"

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000

_job = None  # garde le groupe ouvert tant que Studio Dock tourne


def rattacher_au_groupe() -> bool:
    """Place Studio Dock dans un « job » Windows fermé avec lui : les apps web qu'il lance s'arrêtent
    même s'il est tué ou plante. Les apps natives et le navigateur sont lancés hors de ce groupe."""
    global _job
    if not IS_WIN or _job is not None:
        return False
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class BASIC_LIMIT(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD),
        ]

    class EXTENDED_LIMIT(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BASIC_LIMIT), ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return False
    infos = EXTENDED_LIMIT()
    # KILL_ON_JOB_CLOSE | BREAKAWAY_OK : tout s'arrête avec Studio Dock, sauf ce qui demande à sortir du groupe
    infos.BasicLimitInformation.LimitFlags = 0x2000 | 0x0800
    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(infos), ctypes.sizeof(infos)):
        return False
    if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
        return False
    _job = job
    return True


def options_processus(detache: bool = False) -> dict:
    """Arguments de subprocess.Popen : sans fenêtre noire ; détaché (hors groupe) pour une app native."""
    if not IS_WIN:
        return {"start_new_session": True} if detache else {}
    if detache:
        return {"creationflags": DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB}
    return {"creationflags": CREATE_NO_WINDOW}


def lancer_detache(commande: list[str], **kwargs) -> subprocess.Popen:
    """Lance un programme qui doit survivre à Studio Dock (app native)."""
    try:
        return subprocess.Popen(commande, **options_processus(detache=True), **kwargs)
    except OSError:
        if not IS_WIN:
            raise
        # Groupe sans autorisation de sortie (Studio Dock lancé dans un autre job) : lancement simple
        return subprocess.Popen(commande, creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP, **kwargs)


def ouvrir(cible: str) -> None:
    """Ouvre une adresse dans le navigateur par défaut, ou un dossier dans l'Explorateur, hors du groupe :
    fermer Studio Dock ne ferme pas le navigateur."""
    if IS_WIN:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", cible],
                             creationflags=CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB)
            return
        except OSError:
            subprocess.Popen(["cmd", "/c", "start", "", cible], creationflags=CREATE_NO_WINDOW)
            return
    if cible.startswith(("http://", "https://")):
        webbrowser.open(cible)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", cible])


def autoriser_programme(chemin: Path) -> None:
    """Mac et Linux : rend le programme d'une app exécutable ; sur Mac, retire la « quarantaine » posée sur
    les fichiers téléchargés, qui ferait refuser le lancement d'un programme non signé par Gatekeeper."""
    if IS_WIN or chemin.suffix.lower() == ".py":
        return
    try:
        mode = chemin.stat().st_mode
        if not mode & 0o100:
            chemin.chmod(mode | 0o755)
    except OSError:
        pass
    if sys.platform == "darwin":
        subprocess.run(["xattr", "-d", "com.apple.quarantine", str(chemin)], capture_output=True, check=False)


def message(titre: str, texte: str) -> None:
    """Boîte de message Windows (bloquante) ; ailleurs, attente d'Entrée dans le terminal."""
    if IS_WIN:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, texte, titre, 0x40)  # MB_ICONINFORMATION
        return
    print(texte)
    try:
        input()
    except EOFError:
        pass


def premier_plan(pids: set[int]) -> bool:
    """Ramène au premier plan une fenêtre de l'un de ces processus (restaurée si elle était réduite)."""
    if not IS_WIN or not pids:
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    trouvees: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _chaque(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            trouvees.append(hwnd)
            return False
        return True

    user32.EnumWindows(_chaque, 0)
    if not trouvees:
        return False
    hwnd = trouvees[0]
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    return bool(user32.SetForegroundWindow(hwnd))


def version_fichier(chemin: Path) -> str | None:
    """Version inscrite dans les propriétés d'un exe Windows (onglet Détails)."""
    if not IS_WIN:
        return None
    import ctypes
    from ctypes import wintypes

    version = ctypes.WinDLL("version")
    taille = version.GetFileVersionInfoSizeW(str(chemin), None)
    if not taille:
        return None
    tampon = ctypes.create_string_buffer(taille)
    if not version.GetFileVersionInfoW(str(chemin), 0, taille, tampon):
        return None

    class FIXED(ctypes.Structure):
        _fields_ = [(n, wintypes.DWORD) for n in (
            "dwSignature", "dwStrucVersion", "dwFileVersionMS", "dwFileVersionLS", "dwProductVersionMS",
            "dwProductVersionLS", "dwFileFlagsMask", "dwFileFlags", "dwFileOS", "dwFileType", "dwFileSubtype",
            "dwFileDateMS", "dwFileDateLS")]

    pointeur = ctypes.c_void_p()
    longueur = wintypes.UINT()
    if not version.VerQueryValueW(tampon, "\\", ctypes.byref(pointeur), ctypes.byref(longueur)) or not pointeur:
        return None
    infos = ctypes.cast(pointeur, ctypes.POINTER(FIXED)).contents
    a, b = infos.dwFileVersionMS >> 16, infos.dwFileVersionMS & 0xFFFF
    c = infos.dwFileVersionLS >> 16
    return f"{a}.{b}.{c}" if (a, b, c) != (0, 0, 0) else None


def applications_installees() -> list[dict[str, str]]:
    """Programmes de « Applications installées » (registre Uninstall, compte courant et machine)."""
    if not IS_WIN:
        return []
    import winreg

    resultats = []
    racines = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for racine, chemin in racines:
        try:
            cle = winreg.OpenKey(racine, chemin)
        except OSError:
            continue
        with cle:
            for i in range(winreg.QueryInfoKey(cle)[0]):
                try:
                    with winreg.OpenKey(cle, winreg.EnumKey(cle, i)) as sous_cle:
                        valeurs = {}
                        for nom in ("DisplayName", "DisplayVersion", "InstallLocation", "DisplayIcon"):
                            try:
                                valeurs[nom] = str(winreg.QueryValueEx(sous_cle, nom)[0])
                            except OSError:
                                pass
                        if valeurs.get("DisplayName"):
                            resultats.append(valeurs)
                except OSError:
                    continue
    return resultats
