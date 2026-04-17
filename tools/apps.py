"""
tools/apps.py — Application and folder discovery, launching, and file search.
Extracted from original assistant.py.
"""

import os
import re
import glob
import json
from difflib import get_close_matches
from logger import setup_logging
from tools.registry import registry

logger = setup_logging()

# ── Safe imports ─────────────────────────────────────────────
REGISTRY_AVAILABLE = False
try:
    import winreg
    REGISTRY_AVAILABLE = True
except ImportError:
    pass

SEARCH_ROOT = os.path.expanduser("~")


# ═══════════════════════════════════════════════════════════════
#  App Cache
# ═══════════════════════════════════════════════════════════════

class AppCache:
    """Cache for discovered apps and folders."""

    def __init__(self, cache_file="app_cache.json", max_age=3600):
        self.cache_file = cache_file
        self.max_age = max_age
        self.cache = self._load()

    def _load(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    import time
                    if time.time() - data.get('timestamp', 0) < self.max_age:
                        return data
        except Exception:
            pass
        return {'timestamp': 0, 'apps': {}, 'folders': {}}

    def save(self, apps, folders):
        import time
        self.cache = {'timestamp': time.time(), 'apps': apps, 'folders': folders}
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception:
            pass

    def is_valid(self):
        import time
        return time.time() - self.cache.get('timestamp', 0) < self.max_age


# Global cache
_cache = AppCache()


# ═══════════════════════════════════════════════════════════════
#  Application Discovery
# ═══════════════════════════════════════════════════════════════

def discover_applications():
    """Discover installed applications with caching."""
    if _cache.is_valid():
        return _cache.cache['apps']

    app_map = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "camera": "camera.exe",
    }

    search_paths = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        os.path.expanduser("~/AppData/Local"),
        os.path.expanduser("~/OneDrive/Desktop"),
        r"C:\Users\Public\Desktop",
    ]

    app_patterns = {
        "chrome": ["chrome.exe", "Google/Chrome/Application/chrome.exe"],
        "firefox": ["firefox.exe"],
        "brave": ["brave.exe", "BraveSoftware/Brave-Browser/Application/brave.exe"],
        "edge": ["msedge.exe"],
        "discord": ["Discord.exe", "Discord.lnk"],
        "whatsapp": ["WhatsApp.exe"],
        "spotify": ["Spotify.exe"],
        "vscode": ["Code.exe", "Microsoft VS Code/Code.exe"],
        "steam": ["steam.exe"],
    }

    builtin = {"notepad.exe", "calc.exe", "mspaint.exe", "camera.exe"}

    for app_name, patterns in app_patterns.items():
        for pattern in patterns:
            for base_path in search_paths:
                full_path = os.path.join(base_path, pattern)
                if os.path.exists(full_path):
                    app_map[app_name] = full_path
                    break
            if app_name in app_map and app_map[app_name] not in builtin:
                break

    return app_map


def discover_folders():
    """Discover common folders with caching."""
    if _cache.is_valid():
        return _cache.cache['folders']

    user_home = os.path.expanduser("~")
    folder_map = {
        "downloads": os.path.join(user_home, "Downloads"),
        "documents": os.path.join(user_home, "Documents"),
        "pictures": os.path.join(user_home, "Pictures"),
        "videos": os.path.join(user_home, "Videos"),
        "music": os.path.join(user_home, "Music"),
        "desktop": os.path.join(user_home, "Desktop"),
    }

    additional_paths = [
        os.path.join(user_home, "OneDrive/Desktop"),
        os.path.join(user_home, "Desktop"),
        "D:\\",
        "E:\\",
    ]

    for base_path in additional_paths:
        if not os.path.exists(base_path):
            continue
        try:
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if os.path.isdir(item_path):
                    folder_key = item.lower().replace(" ", "")
                    if folder_key not in folder_map:
                        folder_map[folder_key] = item_path
        except (PermissionError, FileNotFoundError):
            continue

    return folder_map


# ── Initialize & cache ───────────────────────────────────────

APP_MAP = {}
FOLDER_MAP = {}


def init():
    """Initialize app and folder discovery. Call once at startup."""
    global APP_MAP, FOLDER_MAP
    print("📂 Discovering applications and folders...")
    APP_MAP = discover_applications()
    FOLDER_MAP = discover_folders()
    print(f"   ├── {len(APP_MAP)} applications found")
    print(f"   └── {len(FOLDER_MAP)} folders found\n")

    if not _cache.is_valid():
        _cache.save(APP_MAP, FOLDER_MAP)


# ═══════════════════════════════════════════════════════════════
#  Smart Finders
# ═══════════════════════════════════════════════════════════════

def find_application(app_name):
    """Smart application finder with registry, Start Menu, and path scan fallbacks."""
    app_name_lower = app_name.lower()

    # Check discovered apps first
    if app_name_lower in APP_MAP:
        return APP_MAP[app_name_lower]

    # Fuzzy match
    match = get_close_matches(app_name_lower, APP_MAP.keys(), n=1, cutoff=0.4)
    if match:
        return APP_MAP[match[0]]

    # Registry search
    if REGISTRY_AVAILABLE:
        result = _search_registry(app_name_lower)
        if result:
            return result

    # Start Menu search
    result = _search_start_menu(app_name_lower)
    if result:
        return result

    # Glob search
    result = _search_paths(app_name_lower)
    if result:
        return result

    return None


def find_folder(folder_name):
    """Smart folder finder with multi-strategy search."""
    folder_name_lower = folder_name.lower()

    if folder_name_lower in FOLDER_MAP:
        return FOLDER_MAP[folder_name_lower]

    match = get_close_matches(folder_name_lower, FOLDER_MAP.keys(), n=1, cutoff=0.4)
    if match:
        return FOLDER_MAP[match[0]]

    # Search common locations
    search_locations = [
        os.path.expanduser("~"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/OneDrive/Desktop"),
        os.path.expanduser("~/Documents"),
        "C:\\", "D:\\", "E:\\",
    ]

    for location in search_locations:
        if not os.path.exists(location):
            continue
        try:
            for item in os.listdir(location):
                if os.path.isdir(os.path.join(location, item)):
                    if folder_name_lower in item.lower() or item.lower() in folder_name_lower:
                        return os.path.join(location, item)
        except (PermissionError, FileNotFoundError):
            continue

    return None

@registry.register(
    name="open_app",
    description="Opens an application or software on the user's computer.",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Name of the app (e.g. Chrome, Notepad, Discord, Spotify)."}
        },
        "required": ["app_name"]
    }
)
def open_app_tool(app_name):
    path = find_application(app_name)
    if path:
        if open_path(path):
            return f"Successfully opened {app_name}."
    
    # Fallback to folder
    folder_path = find_folder(app_name)
    if folder_path:
        if open_path(folder_path):
            return f"Couldn't find app {app_name}, but opened folder {app_name} instead."
            
    return f"Failed to find application or folder named {app_name}."

@registry.register(
    name="open_folder",
    description="Opens a folder or directory on the user's computer.",
    parameters={
        "type": "object",
        "properties": {
            "folder_name": {"type": "string", "description": "Name of the folder (e.g. Downloads, Documents)."}
        },
        "required": ["folder_name"]
    }
)
def open_folder_tool(folder_name):
    path = find_folder(folder_name)
    if path and open_path(path):
        return f"Successfully opened folder {folder_name}."
    return f"Failed to find folder named {folder_name}."


# ═══════════════════════════════════════════════════════════════
#  File Operations
# ═══════════════════════════════════════════════════════════════

def search_files(query, search_type="file", extensions=None):
    """Search for files or folders matching a query."""
    matches = []
    for root, dirs, files in os.walk(SEARCH_ROOT):
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue

        items = files if search_type == "file" else dirs
        for item in items:
            if item.startswith('.'):
                continue
            if extensions and not any(item.lower().endswith(ext) for ext in extensions):
                continue
            if query.lower() in item.lower():
                full_path = os.path.join(root, item)
                priority = 2 if "Desktop" in full_path else 1 if "Documents" in full_path else 0
                matches.append((full_path, priority))

    matches.sort(key=lambda x: (-x[1], len(x[0])))
    return [m[0] for m in matches]


@registry.register(
    name="open_file",
    description="Searches for and opens a file or document on the computer.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The name or keywords of the file to search for and open."}
        },
        "required": ["query"]
    }
)
def open_file(query, extensions=None):
    """Search for and open a file. Returns status message."""
    try:
        results = search_files(query, search_type="file", extensions=extensions)
        if not results:
            return f"Couldn't find a file matching '{query}'."

        best = get_close_matches(query, [os.path.basename(r) for r in results], n=1, cutoff=0.6)
        target = None

        if best:
            for r in results:
                if best[0] in r:
                    target = r
                    break
        else:
            target = results[0]

        if target:
            filename = os.path.basename(target)
            file_type = _get_file_type(target)
            location = "Desktop" if "Desktop" in target else "Documents" if "Documents" in target else "your computer"
            os.startfile(target)
            return f"Opening {filename}, a {file_type} from {location}."

        return f"Couldn't find a match for '{query}'."
    except Exception as e:
        logger.error(f"open_file error: {e}")
        return "Something went wrong while searching."


def open_path(path):
    """Open a file or folder by its full path."""
    try:
        os.startfile(path)
        return True
    except Exception as e:
        logger.error(f"Failed to open {path}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
#  Internal Helpers
# ═══════════════════════════════════════════════════════════════

def _search_registry(name):
    """Search Windows registry for an application."""
    if not REGISTRY_AVAILABLE:
        return None
    try:
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hkey, path in registry_paths:
            try:
                with winreg.OpenKey(hkey, path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                display = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                if name in display.lower():
                                    try:
                                        loc = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                        if os.path.exists(loc):
                                            for f in os.listdir(loc):
                                                if f.lower().endswith('.exe') and name in f.lower():
                                                    return os.path.join(loc, f)
                                    except FileNotFoundError:
                                        pass
                        except (OSError, FileNotFoundError):
                            continue
            except (OSError, FileNotFoundError):
                continue
    except Exception:
        pass
    return None


def _search_start_menu(name):
    """Search Start Menu for application shortcuts."""
    start_paths = [
        os.path.expanduser("~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]
    for sp in start_paths:
        if not os.path.exists(sp):
            continue
        try:
            for root, dirs, files in os.walk(sp):
                for f in files:
                    if f.lower().endswith('.lnk') and name in f.lower():
                        return os.path.join(root, f)
        except Exception:
            pass
    return None


def _search_paths(name):
    """Search common installation paths for executables."""
    patterns = [
        rf"C:\Program Files\**\{name}*.exe",
        rf"C:\Program Files (x86)\**\{name}*.exe",
        os.path.expanduser(f"~/AppData/Local/**/{name}*.exe"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]
    return None


def _get_file_type(filename):
    """Get a human-readable file type from extension."""
    ext_map = {
        '.pdf': 'PDF', '.doc': 'Word document', '.docx': 'Word document',
        '.txt': 'text file', '.jpg': 'image', '.jpeg': 'image', '.png': 'image',
        '.xlsx': 'spreadsheet', '.xls': 'spreadsheet',
        '.pptx': 'presentation', '.ppt': 'presentation',
        '.csv': 'CSV file', '.zip': 'archive',
        '.mp3': 'audio file', '.mp4': 'video',
        '.py': 'Python file', '.js': 'JavaScript file',
        '.html': 'HTML file', '.css': 'CSS file',
    }
    ext = os.path.splitext(filename)[1].lower()
    return ext_map.get(ext, 'file')
