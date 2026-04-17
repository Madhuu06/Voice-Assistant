"""
tools/desktop.py — Phase 3 PC control tools.
Spotify/media control, window management, clipboard, and keyboard typing.
"""

import time
from logger import setup_logging
from tools.registry import registry

logger = setup_logging()

# ── Safe imports ─────────────────────────────────────────────
PYAUTOGUI_AVAILABLE = False
PYGETWINDOW_AVAILABLE = False
PYPERCLIP_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pass

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    pass

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    pass


# ══════════════════════════════════════════════════════════════
#  Registered Tool Wrappers
# ══════════════════════════════════════════════════════════════

@registry.register(
    name="media_control",
    description="Controls media playback — play, pause, next track, previous track, or mute.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["play_pause", "next", "previous", "mute"],
                "description": "The media action to perform."
            }
        },
        "required": ["action"]
    }
)
def media_control_tool(action: str):
    if not PYAUTOGUI_AVAILABLE:
        return "pyautogui is not installed. Media control unavailable."
    key_map = {
        "play_pause": "playpause",
        "next": "nexttrack",
        "previous": "prevtrack",
        "mute": "volumemute"
    }
    key = key_map.get(action)
    if not key:
        return f"Unknown media action: {action}"
    pyautogui.press(key)
    return f"Media: {action} triggered."


@registry.register(
    name="window_control",
    description="Minimizes, maximizes, closes, or focuses an application window by name.",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Partial name of the window to control (e.g. 'chrome', 'notepad')."},
            "action": {
                "type": "string",
                "enum": ["minimize", "maximize", "close", "focus"],
                "description": "Action to perform on the window."
            }
        },
        "required": ["app_name", "action"]
    }
)
def window_control_tool(app_name: str, action: str):
    if not PYGETWINDOW_AVAILABLE:
        return "pygetwindow is not installed. Window control unavailable."
    try:
        windows = gw.getWindowsWithTitle(app_name)
        if not windows:
            # Try case-insensitive partial match
            all_windows = gw.getAllWindows()
            windows = [w for w in all_windows if app_name.lower() in w.title.lower()]
        if not windows:
            return f"No window found matching '{app_name}'."
        win = windows[0]
        if action == "minimize":
            win.minimize()
        elif action == "maximize":
            win.maximize()
        elif action == "close":
            win.close()
        elif action == "focus":
            win.activate()
        return f"Window '{win.title}' — {action} done."
    except Exception as e:
        return f"Window control failed: {e}"


@registry.register(
    name="read_clipboard",
    description="Reads and returns the current contents of the system clipboard.",
    parameters={"type": "object", "properties": {}}
)
def read_clipboard_tool():
    if not PYPERCLIP_AVAILABLE:
        return "pyperclip is not installed. Clipboard access unavailable."
    try:
        content = pyperclip.paste()
        if content:
            return f"Clipboard contains: {content[:500]}"
        return "Clipboard is empty."
    except Exception as e:
        return f"Failed to read clipboard: {e}"


@registry.register(
    name="write_clipboard",
    description="Writes text to the system clipboard.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to copy to clipboard."}
        },
        "required": ["text"]
    }
)
def write_clipboard_tool(text: str):
    if not PYPERCLIP_AVAILABLE:
        return "pyperclip is not installed. Clipboard access unavailable."
    try:
        pyperclip.copy(text)
        return f"Copied to clipboard: {text[:100]}"
    except Exception as e:
        return f"Failed to write clipboard: {e}"


@registry.register(
    name="type_text",
    description="Types text using the keyboard, as if the user typed it.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to type."},
            "delay": {"type": "number", "description": "Optional delay in seconds before typing. Default 0.5."}
        },
        "required": ["text"]
    }
)
def type_text_tool(text: str, delay: float = 0.5):
    if not PYAUTOGUI_AVAILABLE:
        return "pyautogui is not installed. Typing unavailable."
    try:
        time.sleep(float(delay))
        pyautogui.write(text, interval=0.03)
        return f"Typed: {text[:100]}"
    except Exception as e:
        return f"Failed to type text: {e}"


@registry.register(
    name="press_key",
    description="Presses a specific keyboard key (e.g. enter, escape, tab, ctrl+c).",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key or key combo to press (e.g. 'enter', 'escape', 'ctrl+c')."}
        },
        "required": ["key"]
    }
)
def press_key_tool(key: str):
    if not PYAUTOGUI_AVAILABLE:
        return "pyautogui is not installed. Key press unavailable."
    try:
        if '+' in key:
            keys = [k.strip() for k in key.split('+')]
            pyautogui.hotkey(*keys)
        else:
            pyautogui.press(key)
        return f"Pressed: {key}"
    except Exception as e:
        return f"Failed to press key: {e}"
