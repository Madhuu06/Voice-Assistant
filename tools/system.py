"""
tools/system.py — System control tools (volume, brightness, power, screenshots, system info).
Extracted from original assistant.py SystemController.
"""

import os
import subprocess
from datetime import datetime
from logger import setup_logging

logger = setup_logging()

# ── Safe imports with fallbacks ──────────────────────────────
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


# ── Volume Control ───────────────────────────────────────────

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

    # Fallback: nircmd
    try:
        subprocess.run(f"nircmd setsysvolume {int(level * 655.35)}", shell=True, timeout=5)
        return True
    except Exception:
        return False


def get_volume():
    """Get current system volume (0-100), or None."""
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
    except ImportError:
        # Fallback: PowerShell
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshots_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            fallback_path = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")

            cmd = f"""
            Add-Type -AssemblyName System.Windows.Forms
            $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
            $bitmap.Save('{fallback_path}')
            """
            subprocess.run(["powershell", "-Command", cmd], timeout=15)
            return fallback_path
        except Exception:
            return None

    try:
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
    """Shutdown with safety delay."""
    try:
        subprocess.run(
            f'shutdown /s /t {delay} /c "Maya: Shutting down in {delay} seconds — run shutdown /a to cancel"',
            shell=True, timeout=5,
        )
        return True
    except Exception:
        return False


def restart(delay=10):
    """Restart with safety delay."""
    try:
        subprocess.run(
            f'shutdown /r /t {delay} /c "Maya: Restarting in {delay} seconds — run shutdown /a to cancel"',
            shell=True, timeout=5,
        )
        return True
    except Exception:
        return False


def sleep_system():
    """Put system to sleep."""
    try:
        subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return True
    except Exception:
        return False
