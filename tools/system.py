"""
tools/system.py — System control tools with LLM tool-call registry.
Handles volume, brightness, screenshots, system info, and power management.
"""

import os
import subprocess
from datetime import datetime
from logger import setup_logging
from config import ASSISTANT_NAME
from tools.registry import registry

logger = setup_logging()

# ── Safe imports ─────────────────────────────────────────────
PSUTIL_AVAILABLE = False
AUDIO_CONTROL_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    pass

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    AUDIO_CONTROL_AVAILABLE = True
except ImportError:
    pass


# ── Volume ───────────────────────────────────────────────────

def set_volume(level):
    """Set system volume (0-100)."""
    level = max(0, min(100, level))
    if AUDIO_CONTROL_AVAILABLE:
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterScalarVolume(level / 100.0, None)
            return True
        except Exception as e:
            logger.warning(f"pycaw volume set failed: {e}")
    try:
        subprocess.run(f"nircmd setsysvolume {int(level * 655.35)}", shell=True, timeout=5)
        return True
    except Exception:
        return False


def get_volume():
    """Get current system volume (0-100)."""
    if not AUDIO_CONTROL_AVAILABLE:
        return None
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return int(volume.GetMasterScalarVolume() * 100)
    except Exception:
        return None


def change_volume(direction="up", step=10):
    """Change volume up or down by step amount."""
    current = get_volume()
    if current is not None:
        new_vol = max(0, min(100, current + (step if direction == "up" else -step)))
        return set_volume(new_vol), new_vol
    return False, None


# ── Brightness ───────────────────────────────────────────────

def set_brightness(level):
    """Set screen brightness (0-100)."""
    level = max(0, min(100, level))
    try:
        cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"
        result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


# ── System Info ──────────────────────────────────────────────

def get_system_info():
    """Get system information (CPU, memory, disk, battery)."""
    if not PSUTIL_AVAILABLE:
        return None
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('C:')
        info = {
            'cpu': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available': round(memory.available / (1024 ** 3), 1),
            'disk_percent': round((disk.used / disk.total) * 100, 1),
            'disk_free': round(disk.free / (1024 ** 3), 1),
        }
        try:
            battery = psutil.sensors_battery()
            if battery:
                info['battery'] = round(battery.percent)
                info['battery_plugged'] = battery.power_plugged
        except Exception:
            pass
        return info
    except Exception:
        return None


def format_system_info(info):
    """Format system info dict into a speakable string."""
    if not info:
        return "Couldn't retrieve system information."
    response = f"CPU at {info['cpu']}%, memory {info['memory_percent']}% used"
    response += f" with {info['memory_available']} gigs free."
    response += f" Disk is {info['disk_percent']}% full, {info['disk_free']} gigs available."
    if 'battery' in info:
        status = "plugged in" if info['battery_plugged'] else "on battery"
        response += f" Battery at {info['battery']}%, {status}."
    return response


# ── Screenshots ──────────────────────────────────────────────

def take_screenshot(filename=None):
    """Take and save a screenshot. Returns file path or None."""
    try:
        from PIL import ImageGrab
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshots_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            filename = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
        screenshot = ImageGrab.grab()
        screenshot.save(filename)
        return filename
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return None


# ── Power Management ─────────────────────────────────────────

def shutdown(delay=10):
    """Shutdown the computer after a delay."""
    try:
        subprocess.run(
            f'shutdown /s /t {delay} /c "{ASSISTANT_NAME}: Shutting down in {delay} seconds — run shutdown /a to cancel"',
            shell=True, timeout=5,
        )
        return True
    except Exception:
        return False


def restart(delay=10):
    """Restart the computer after a delay."""
    try:
        subprocess.run(
            f'shutdown /r /t {delay} /c "{ASSISTANT_NAME}: Restarting in {delay} seconds — run shutdown /a to cancel"',
            shell=True, timeout=5,
        )
        return True
    except Exception:
        return False


def sleep_system():
    """Put the system to sleep."""
    try:
        subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
#  Registered Tool Wrappers
# ══════════════════════════════════════════════════════════════

@registry.register(
    name="set_volume",
    description="Sets the system volume to a specific level.",
    parameters={
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "Volume level from 0 to 100."}
        },
        "required": ["level"]
    }
)
def set_volume_tool(level: int):
    level = int(level)
    ok = set_volume(level)
    return f"Volume set to {level}%." if ok else "Failed to change volume."


@registry.register(
    name="change_volume",
    description="Increases or decreases the system volume.",
    parameters={
        "type": "object",
        "properties": {
            "direction": {"type": "string", "enum": ["up", "down"], "description": "Direction to change volume."}
        },
        "required": ["direction"]
    }
)
def change_volume_tool(direction: str):
    ok, new_vol = change_volume(direction)
    if ok and new_vol is not None:
        return f"Volume now at {new_vol}%."
    return "Couldn't adjust volume."


@registry.register(
    name="get_volume",
    description="Gets the current system volume level.",
    parameters={"type": "object", "properties": {}}
)
def get_volume_tool():
    vol = get_volume()
    return f"Volume is at {vol}%." if vol is not None else "Couldn't read volume."


@registry.register(
    name="set_brightness",
    description="Sets the screen brightness to a specific level.",
    parameters={
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "Brightness level from 0 to 100."}
        },
        "required": ["level"]
    }
)
def set_brightness_tool(level: int):
    ok = set_brightness(int(level))
    return f"Brightness set to {level}%." if ok else "Failed to change brightness."


@registry.register(
    name="get_system_info",
    description="Gets current system status including CPU, RAM, disk usage, and battery.",
    parameters={"type": "object", "properties": {}}
)
def get_system_info_tool():
    info = get_system_info()
    return format_system_info(info)


@registry.register(
    name="take_screenshot",
    description="Takes a screenshot of the current screen and saves it.",
    parameters={"type": "object", "properties": {}}
)
def take_screenshot_tool():
    path = take_screenshot()
    return f"Screenshot saved to {path}." if path else "Failed to take screenshot."


@registry.register(
    name="shutdown_computer",
    description="Shuts down the computer after a short delay.",
    parameters={
        "type": "object",
        "properties": {
            "delay": {"type": "integer", "description": "Delay in seconds before shutdown. Default is 10."}
        }
    }
)
def shutdown_tool(delay: int = 10):
    ok = shutdown(int(delay))
    return f"Shutting down in {delay} seconds." if ok else "Failed to initiate shutdown."


@registry.register(
    name="sleep_computer",
    description="Puts the computer to sleep.",
    parameters={"type": "object", "properties": {}}
)
def sleep_tool():
    ok = sleep_system()
    return "Going to sleep." if ok else "Failed to sleep."
