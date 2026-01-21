import os
import time
import threading
import sounddevice as sd
import pyttsx3
from difflib import get_close_matches
import sys
import numpy as np
from datetime import datetime
import json
import re
import whisper
import tempfile
import wave
from collections import deque
import subprocess
import ctypes
import pickle
from pathlib import Path

# Safe imports with fallbacks
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not available - system info features disabled")

try:
    from PIL import ImageGrab
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False
    print("⚠️  PIL not available - screenshot features disabled")

try:
    import winreg
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False
    print("⚠️  winreg not available - registry search disabled")

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    from ctypes.wintypes import DWORD
    AUDIO_CONTROL_AVAILABLE = True
except ImportError:
    AUDIO_CONTROL_AVAILABLE = False
    print("⚠️  pycaw not available - volume control features disabled")

from config import *
from logger import setup_logging
from elevenlabs_voice import speak_with_elevenlabs, is_elevenlabs_ready

logger = setup_logging()

# Load Whisper models
print("Loading Whisper models...")
print("Loading tiny model for wake word detection...")
wake_word_model = whisper.load_model(WHISPER_WAKE_MODEL)
print("Loading base model for command recognition...")
command_model = whisper.load_model(WHISPER_COMMAND_MODEL)
print("Whisper models loaded successfully!")

SEARCH_ROOT = os.path.expanduser("~")

# === IMMEDIATE IMPACT IMPROVEMENTS ===

class AppCache:
    """Caching system for discovered apps and folders"""
    def __init__(self):
        self.cache_file = "app_cache.json"
        self.cache_age_limit = 3600  # 1 hour
        self.cache = self.load_cache()
    
    def load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is still valid
                    if time.time() - data.get('timestamp', 0) < self.cache_age_limit:
                        return data
            return {'timestamp': 0, 'apps': {}, 'folders': {}}
        except:
            return {'timestamp': 0, 'apps': {}, 'folders': {}}
    
    def save_cache(self, apps, folders):
        self.cache = {
            'timestamp': time.time(),
            'apps': apps,
            'folders': folders
        }
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except:
            pass
    
    def is_valid(self):
        return time.time() - self.cache.get('timestamp', 0) < self.cache_age_limit

class VoiceActivityDetector:
    """Simple Voice Activity Detection to reduce CPU usage"""
    def __init__(self, energy_threshold=0.001, silence_duration=0.5):
        self.energy_threshold = energy_threshold  # Lower threshold for better sensitivity
        self.silence_duration = silence_duration  # Shorter duration
        self.last_voice_time = 0
    
    def is_voice_active(self, audio_data):
        # Calculate RMS energy
        energy = np.sqrt(np.mean(audio_data ** 2))
        
        if energy > self.energy_threshold:
            self.last_voice_time = time.time()
            return True
        
        # Return True if we detected voice recently
        return (time.time() - self.last_voice_time) < self.silence_duration

class SystemController:
    """Advanced system operations controller with graceful fallbacks"""
    
    @staticmethod
    def set_volume(level):
        """Set system volume (0-100) with fallback methods"""
        if not AUDIO_CONTROL_AVAILABLE:
            # Fallback: Use PowerShell
            try:
                cmd = f"[Audio]::Volume = {level / 100.0}"
                subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=5)
                return True
            except:
                # Final fallback: nircmd (if available)
                try:
                    subprocess.run(f"nircmd setsysvolume {int(level * 655.35)}", shell=True, timeout=5)
                    return True
                except:
                    return False
        
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterScalarVolume(level / 100.0, None)
            return True
        except:
            # Fallback to PowerShell method
            try:
                cmd = f"[Audio]::Volume = {level / 100.0}"
                subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=5)
                return True
            except:
                return False
    
    @staticmethod
    def get_volume():
        """Get current system volume (0-100) with fallbacks"""
        if not AUDIO_CONTROL_AVAILABLE:
            return None  # Skip if no audio control available
        
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            return int(volume.GetMasterScalarVolume() * 100)
        except:
            return None
    
    @staticmethod
    def set_brightness(level):
        """Set screen brightness (0-100) with error handling"""
        try:
            # PowerShell command for brightness
            cmd = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    @staticmethod
    def get_system_info():
        """Get system information with graceful fallbacks"""
        if not PSUTIL_AVAILABLE:
            # Basic fallback without psutil
            try:
                result = subprocess.run("wmic cpu get loadpercentage /value", shell=True, capture_output=True, text=True)
                cpu_line = [line for line in result.stdout.split('\n') if 'LoadPercentage' in line]
                cpu_percent = int(cpu_line[0].split('=')[1]) if cpu_line else None
                
                return {
                    'cpu': cpu_percent or 0,
                    'memory_percent': 0,  # Fallback values
                    'memory_available': 0,
                    'disk_percent': 0,
                    'disk_free': 0
                }
            except:
                return None
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('C:')
            
            info = {
                'cpu': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': round(memory.available / (1024**3), 1),
                'disk_percent': round((disk.used / disk.total) * 100, 1),
                'disk_free': round(disk.free / (1024**3), 1)
            }
            
            try:
                battery = psutil.sensors_battery()
                if battery:
                    info['battery'] = round(battery.percent)
                    info['battery_plugged'] = battery.power_plugged
            except:
                pass  # Battery info not critical
            
            return info
        except:
            return None
    
    @staticmethod
    def take_screenshot(filename=None):
        """Take a screenshot with fallbacks"""
        if not SCREENSHOT_AVAILABLE:
            # Fallback: Use PowerShell
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshots_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)
                fallback_filename = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
                
                cmd = f"""
                Add-Type -AssemblyName System.Windows.Forms
                $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
                $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
                $bitmap.Save('{fallback_filename}')
                """
                subprocess.run(["powershell", "-Command", cmd], timeout=15)
                return fallback_filename
            except:
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
        except:
            return None
    
    @staticmethod
    def shutdown_system(delay=0):
        """Shutdown system with confirmation and error handling"""
        try:
            if delay > 0:
                subprocess.run(f"shutdown /s /t {delay}", shell=True, timeout=5)
            else:
                # Add confirmation for immediate shutdown
                subprocess.run("shutdown /s /t 10 /c \"Shutting down in 10 seconds - run 'shutdown /a' to cancel\"", shell=True, timeout=5)
            return True
        except:
            return False
    
    @staticmethod
    def restart_system(delay=0):
        """Restart system with confirmation and error handling"""
        try:
            if delay > 0:
                subprocess.run(f"shutdown /r /t {delay}", shell=True, timeout=5)
            else:
                subprocess.run("shutdown /r /t 10 /c \"Restarting in 10 seconds - run 'shutdown /a' to cancel\"", shell=True, timeout=5)
            return True
        except:
            return False

class ContextualIntelligence:
    """Contextual awareness and learning"""
    def __init__(self):
        self.usage_file = "usage_patterns.json"
        self.load_usage_patterns()
    
    def load_usage_patterns(self):
        try:
            if os.path.exists(self.usage_file):
                with open(self.usage_file, 'r') as f:
                    self.patterns = json.load(f)
            else:
                self.patterns = {
                    'app_usage': {},
                    'hourly_usage': {},
                    'command_frequency': {}
                }
        except:
            self.patterns = {
                'app_usage': {},
                'hourly_usage': {},
                'command_frequency': {}
            }
    
    def save_usage_patterns(self):
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(self.patterns, f)
        except:
            pass
    
    def log_command(self, command, app_name=None):
        """Log command usage for learning"""
        hour = datetime.now().hour
        
        # Log command frequency
        if command in self.patterns['command_frequency']:
            self.patterns['command_frequency'][command] += 1
        else:
            self.patterns['command_frequency'][command] = 1
        
        # Log hourly usage
        if str(hour) in self.patterns['hourly_usage']:
            self.patterns['hourly_usage'][str(hour)] += 1
        else:
            self.patterns['hourly_usage'][str(hour)] = 1
        
        # Log app usage with time
        if app_name:
            if app_name in self.patterns['app_usage']:
                self.patterns['app_usage'][app_name]['count'] += 1
                self.patterns['app_usage'][app_name]['hours'].append(hour)
            else:
                self.patterns['app_usage'][app_name] = {'count': 1, 'hours': [hour]}
        
        self.save_usage_patterns()
    
    def get_time_based_greeting(self):
        """Get contextual greeting based on time"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "Good morning!"
        elif 12 <= hour < 18:
            return "Good afternoon!"
        elif 18 <= hour < 22:
            return "Good evening!"
        else:
            return "Hello there!"
    
    def get_suggested_apps(self, limit=3):
        """Get app suggestions based on current time and usage patterns"""
        current_hour = datetime.now().hour
        suggestions = []
        
        for app, data in self.patterns['app_usage'].items():
            if current_hour in data['hours']:
                suggestions.append((app, data['count']))
        
        # Sort by usage count and return top suggestions
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [app for app, count in suggestions[:limit]]

# Initialize components
app_cache = AppCache()
vad = VoiceActivityDetector()
system_controller = SystemController()
contextual_ai = ContextualIntelligence()

def discover_applications():
    """Dynamically discover installed applications with caching"""
    # Check cache first
    if app_cache.is_valid():
        return app_cache.cache['apps']
    
    app_map = {
        # Built-in Windows apps (always available)
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "camera": "camera.exe",
    }
    
    # Common application paths to scan
    search_paths = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        os.path.expanduser("~/AppData/Local"),
        os.path.expanduser("~/OneDrive/Desktop"),
        r"C:\Users\Public\Desktop"
    ]
    
    # Known application patterns
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
    
    for app_name, patterns in app_patterns.items():
        for pattern in patterns:
            for base_path in search_paths:
                if "*" in pattern:
                    # Handle wildcard patterns
                    import glob
                    matches = glob.glob(os.path.join(base_path, "**", pattern), recursive=True)
                    if matches:
                        app_map[app_name] = matches[0]
                        break
                else:
                    full_path = os.path.join(base_path, pattern)
                    if os.path.exists(full_path):
                        app_map[app_name] = full_path
                        break
            if app_name in app_map and app_map[app_name] not in ["notepad.exe", "calc.exe", "mspaint.exe", "camera.exe"]:
                break
    
    return app_map

def discover_folders():
    """Dynamically discover common folders with caching"""
    # Check cache first
    if app_cache.is_valid():
        return app_cache.cache['folders']
    
    user_home = os.path.expanduser("~")
    
    folder_map = {
        # Standard Windows folders
        "downloads": os.path.join(user_home, "Downloads"),
        "documents": os.path.join(user_home, "Documents"),
        "pictures": os.path.join(user_home, "Pictures"),
        "videos": os.path.join(user_home, "Videos"),
        "music": os.path.join(user_home, "Music"),
        "desktop": os.path.join(user_home, "Desktop"),
    }
    
    # Scan for additional folders on Desktop and common locations
    additional_paths = [
        os.path.join(user_home, "OneDrive/Desktop"),
        os.path.join(user_home, "Desktop"),
        "D:\\",
        "E:\\",
    ]
    
    common_folder_names = ["Games", "Projects", "Work", "Screenshots", "Wallpaper", "Karthik"]
    
    for base_path in additional_paths:
        if not os.path.exists(base_path):
            continue
        try:
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if os.path.isdir(item_path):
                    # Add common folders with simple names
                    folder_key = item.lower().replace(" ", "")
                    if folder_key not in folder_map:
                        folder_map[folder_key] = item_path
        except (PermissionError, FileNotFoundError):
            continue
    
    return folder_map

# Initialize dynamic maps with caching
print("Discovering installed applications...")
APP_MAP = discover_applications()
print(f"Found {len(APP_MAP)} applications")

print("Discovering folders...")
FOLDER_MAP = discover_folders()
print(f"Found {len(FOLDER_MAP)} folders")

# Save to cache
if not app_cache.is_valid():
    app_cache.save_cache(APP_MAP, FOLDER_MAP)

# Audio settings for Whisper
SAMPLE_RATE = 16000
CHUNK_DURATION = 3.0  # seconds - longer for better stability
WAKE_WORDS = ["maya", "hey maya", "hello maya"]

# Enhanced Voice System Setup with Configuration Support
print("Setting up voice system...")

# Load voice configuration if it exists
import json
voice_config = None
try:
    if os.path.exists("voice_config.json"):
        with open("voice_config.json", "r") as f:
            voice_config = json.load(f)
        logger.info(f"Loaded voice config: {voice_config['voice_name']}")
except:
    logger.info("Using default voice configuration")

# TTS Engine Setup
engine = pyttsx3.init()
voices = engine.getProperty('voices')

if voice_config:
    # Use configured voice
    try:
        engine.setProperty('voice', voice_config["voice_id"])
        engine.setProperty('rate', voice_config["rate"])
        engine.setProperty('volume', voice_config["volume"])
        logger.info(f"Using configured voice: {voice_config['voice_name']}")
    except:
        logger.warning("Could not load configured voice, using default")
        engine.setProperty('rate', 170)
        engine.setProperty('volume', VOICE_VOLUME)
else:
    # Use best available voice
    selected_voice = None
    
    # Priority order: Zira (female) > Hazel (British) > David (male)
    voice_priority = ["Zira", "Hazel", "David"]
    
    for priority_voice in voice_priority:
        for voice in voices:
            if priority_voice in voice.name:
                selected_voice = voice
                break
        if selected_voice:
            break
    
    if selected_voice:
        engine.setProperty('voice', selected_voice.id)
        logger.info(f"Using voice: {selected_voice.name}")
    else:
        logger.warning("No preferred voice found, using system default")
    
    engine.setProperty('rate', 170)
    engine.setProperty('volume', VOICE_VOLUME)

def speak(text, show_text=True):
    if show_text:
        print(text)
    
    # Try ElevenLabs first (premium quality)
    if is_elevenlabs_ready():
        success = speak_with_elevenlabs(text)
        if success:
            return
        else:
            logger.warning("ElevenLabs failed, falling back to system voice")
    
    # Fallback to system voice
    time.sleep(0.2)
    engine.say(text)
    engine.runAndWait()

def transcribe_audio_chunk(audio_data, model=None):
    """Transcribe audio chunk using specified Whisper model"""
    if model is None:
        model = command_model  # Default to command model
    
    try:
        # Convert numpy array to format expected by Whisper
        # Whisper expects 16 kHz mono audio
        if len(audio_data) == 0:
            return ""
        
        # Normalize audio data to float32 range [-1, 1]
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # Ensure audio is mono (1D)
        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()
            
        # Pad or trim to minimum length that Whisper can process
        min_length = int(SAMPLE_RATE * 0.1)  # 0.1 second minimum
        if len(audio_data) < min_length:
            audio_data = np.pad(audio_data, (0, min_length - len(audio_data)))
        
        # Use Whisper directly on audio array (no file needed)
        result = model.transcribe(audio_data, language="en")
        return result["text"].strip().lower()
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return ""

def contains_wake_word(text):
    """Check if transcribed text contains wake word - handles Whisper mishearing 'alexa'"""
    text = text.lower().strip()
    print(f"🔍 Checking for wake word in: '{text}'")
    
    # Primary wake words (what user intends to say)
    primary_words = ["maya", "hey maya", "hello maya", "alexa", "hey alexa", "hello alexa"]
    for wake_word in primary_words:
        if wake_word in text:
            print(f"✅ Direct match found: '{wake_word}'")
            return True
    
    # Common Whisper mishearings of "alexa" - these are what Whisper thinks "alexa" sounds like
    whisper_mishearings = [
        "now", "no", "go", "so", "to", "oh", "low", "show", "know", "flow",
        "alex", "lex", "flex", "lexa", "likes", "likes it", "likes a", "likes her"
    ]
    
    for mishearing in whisper_mishearings:
        if mishearing in text:
            print(f"✅ ALEXA DETECTED! Whisper heard '{mishearing}' but you likely said 'alexa'")
            return True
    
    # Maya alternatives (original female name options)
    maya_alternatives = ["mia", "mya", "maria", "may", "mai", "maia", "mira", "mila", "myra", "miya"]
    for alt in maya_alternatives:
        if alt in text:
            print(f"✅ Maya alternative detected: '{alt}'")
            return True
    
    # Short utterances (1-3 letters) - probably trying to say wake word
    if len(text.strip()) <= 3 and len(text.strip()) >= 1:
        print(f"✅ SHORT UTTERANCE! '{text}' - assuming you're trying to say wake word")
        return True
    
    print(f"❌ No wake word detected")
    return False

def extract_command_after_wake_word(text):
    """Extract command after wake word"""
    text = text.lower()
    for wake_word in WAKE_WORDS:
        if wake_word in text:
            # Find the position after the wake word
            pos = text.find(wake_word) + len(wake_word)
            command = text[pos:].strip()
            if command:
                return command
    return ""

def cleanup():
    """Cleanup resources before exit"""
    try:
        engine.stop()
    except:
        pass

import atexit
atexit.register(cleanup)



def smart_find_application(app_name):
    """Smart application finder with multiple strategies"""
    
    # First, check the discovered APP_MAP
    if app_name in APP_MAP:
        return APP_MAP[app_name]
    
    # Strategy 1: Windows Registry search
    try:
        import winreg
        def search_registry_for_app(name):
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
                                    try:
                                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                        if name.lower() in display_name.lower():
                                            try:
                                                install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                                # Look for .exe files in install location
                                                if os.path.exists(install_location):
                                                    for file in os.listdir(install_location):
                                                        if file.lower().endswith('.exe') and name.lower() in file.lower():
                                                            return os.path.join(install_location, file)
                                            except FileNotFoundError:
                                                pass
                                    except FileNotFoundError:
                                        pass
                            except (OSError, FileNotFoundError):
                                continue
                except (OSError, FileNotFoundError):
                    continue
            return None
        
        registry_result = search_registry_for_app(app_name)
        if registry_result:
            return registry_result
    except ImportError:
        pass
    
    # Strategy 2: Start Menu search
    try:
        start_menu_paths = [
            os.path.expanduser("~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
        ]
        
        for start_path in start_menu_paths:
            if os.path.exists(start_path):
                for root, dirs, files in os.walk(start_path):
                    for file in files:
                        if file.lower().endswith('.lnk') and app_name.lower() in file.lower():
                            return os.path.join(root, file)
    except Exception:
        pass
    
    # Strategy 3: Common paths search
    import glob
    common_paths = [
        rf"C:\Program Files\**\{app_name}*.exe",
        rf"C:\Program Files (x86)\**\{app_name}*.exe",
        os.path.expanduser(f"~/AppData/Local/**/{app_name}*.exe"),
        os.path.expanduser(f"~/Desktop/**/{app_name}*.lnk"),
        os.path.expanduser(f"~/OneDrive/Desktop/**/{app_name}*.lnk"),
    ]
    
    for pattern in common_paths:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]
    
    return None

def smart_find_folder(folder_name):
    """Smart folder finder with multiple strategies"""
    
    # First, check the discovered FOLDER_MAP
    if folder_name in FOLDER_MAP:
        return FOLDER_MAP[folder_name]
    
    # Strategy 1: Search common locations
    search_locations = [
        os.path.expanduser("~"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/OneDrive/Desktop"),
        os.path.expanduser("~/Documents"),
        "C:\\",
        "D:\\",
        "E:\\",
    ]
    
    for location in search_locations:
        if not os.path.exists(location):
            continue
        
        try:
            for item in os.listdir(location):
                if os.path.isdir(os.path.join(location, item)):
                    # Check for exact or partial matches
                    if (folder_name.lower() == item.lower() or 
                        folder_name.lower() in item.lower() or 
                        item.lower() in folder_name.lower()):
                        return os.path.join(location, item)
        except (PermissionError, FileNotFoundError):
            continue
    
    # Strategy 2: Deep search (limited depth to avoid slowness)
    user_home = os.path.expanduser("~")
    for root, dirs, files in os.walk(user_home):
        # Limit depth to avoid too much searching
        depth = root.replace(user_home, '').count(os.sep)
        if depth > 3:  # Only search 3 levels deep
            dirs[:] = []  # Don't go deeper
            continue
        
        for dir_name in dirs:
            if folder_name.lower() in dir_name.lower():
                return os.path.join(root, dir_name)
    
    return None

def parse_intent_local(user_input):
    """Enhanced intent parser with system operations and contextual intelligence"""
    user_input = user_input.lower().strip()
    
    # Known apps and folders from the maps
    known_apps = list(APP_MAP.keys())
    known_folders = list(FOLDER_MAP.keys())
    
    # Normalize common phrases
    user_input = re.sub(r'\b(could you|can you|please|would you)\b', '', user_input).strip()
    user_input = re.sub(r'\b(my|the)\b', '', user_input).strip()
    
    # === NEW: SYSTEM OPERATIONS ===
    # Volume control patterns
    volume_patterns = [
        r'set volume to (\d+)',
        r'volume (\d+)',
        r'turn volume (up|down)',
        r'(mute|unmute)',
        r'what.* volume'
    ]
    
    for pattern in volume_patterns:
        match = re.search(pattern, user_input)
        if match:
            if 'what' in user_input or 'volume' in user_input and not match.group(1) if match.groups() else True:
                return {"action": "get_volume", "confidence": 0.9}
            elif match.group(1).isdigit():
                return {"action": "set_volume", "value": int(match.group(1)), "confidence": 0.9}
            elif match.group(1) in ['up', 'down']:
                return {"action": "volume_change", "direction": match.group(1), "confidence": 0.9}
            elif 'mute' in user_input:
                return {"action": "mute", "confidence": 0.9}
    
    # System info patterns
    if any(word in user_input for word in ['system info', 'system status', 'computer info', 'cpu', 'memory', 'battery']):
        return {"action": "system_info", "confidence": 0.9}
    
    # Screenshot patterns
    if any(word in user_input for word in ['screenshot', 'take screenshot', 'capture screen', 'screen capture']):
        return {"action": "screenshot", "confidence": 0.9}
    
    # Power management patterns
    power_patterns = [
        r'(shutdown|shut down|turn off).*(\d+)?',
        r'(restart|reboot).*(\d+)?',
        r'(sleep|hibernate)'
    ]
    
    for pattern in power_patterns:
        match = re.search(pattern, user_input)
        if match:
            action_type = match.group(1)
            delay = int(match.group(2)) if match.group(2) else 0
            return {
                "action": "power_management",
                "type": action_type.replace(" ", ""),
                "delay": delay,
                "confidence": 0.9
            }
    
    # Brightness control (if supported)
    brightness_patterns = [
        r'set brightness to (\d+)',
        r'brightness (\d+)',
        r'(brighten|dim) screen'
    ]
    
    for pattern in brightness_patterns:
        match = re.search(pattern, user_input)
        if match:
            if match.group(1) and match.group(1).isdigit():
                return {"action": "set_brightness", "value": int(match.group(1)), "confidence": 0.8}
            elif 'brighten' in user_input:
                return {"action": "brightness_change", "direction": "up", "confidence": 0.8}
            elif 'dim' in user_input:
                return {"action": "brightness_change", "direction": "down", "confidence": 0.8}
    
    # === EXISTING PATTERNS (Enhanced) ===
    # Check for goodbye/thank you
    if any(word in user_input for word in ['thank', 'thanks', 'bye', 'goodbye']):
        return {"action": "unknown", "confidence": 0.9}  # Will trigger goodbye in main handler
    
    # Check for search patterns
    search_patterns = [
        r'search (.+) on google',
        r'google (.+)',
        r'search for (.+)',
        r'look up (.+)'
    ]
    
    for pattern in search_patterns:
        match = re.search(pattern, user_input)
        if match:
            return {
                "action": "search_web",
                "query": match.group(1).strip(),
                "confidence": 0.8
            }
    
    # Check for open app and search patterns
    app_search_patterns = [
        r'open (\w+) and search (.+)',
        r'launch (\w+) and search (.+)',
        r'start (\w+) and search (.+)'
    ]
    
    for pattern in app_search_patterns:
        match = re.search(pattern, user_input)
        if match:
            app_name = match.group(1)
            search_query = match.group(2)
            # Check if it's a known app
            best_match = get_close_matches(app_name, known_apps, n=1, cutoff=0.6)
            if best_match:
                return {
                    "action": "open_app_and_search",
                    "target": best_match[0],
                    "query": search_query.strip(),
                    "confidence": 0.8
                }
    
    # Check for app opening
    app_patterns = [
        r'open (\w+)',
        r'launch (\w+)',
        r'start (\w+)',
        r'run (\w+)'
    ]
    
    for pattern in app_patterns:
        match = re.search(pattern, user_input)
        if match:
            app_name = match.group(1)
            best_match = get_close_matches(app_name, known_apps, n=1, cutoff=0.6)
            if best_match:
                return {
                    "action": "open_app",
                    "target": best_match[0],
                    "confidence": 0.8
                }
    
    # Check for folder opening
    folder_patterns = [
        r'open (.+) folder',
        r'open folder (.+)',
        r'show (.+) folder',
        r'access (.+) folder',
        r'go to (.+) folder'
    ]
    
    for pattern in folder_patterns:
        match = re.search(pattern, user_input)
        if match:
            folder_name = match.group(1).strip()
            best_match = get_close_matches(folder_name, known_folders, n=1, cutoff=0.6)
            if best_match:
                return {
                    "action": "open_folder",
                    "target": best_match[0],
                    "confidence": 0.8
                }
    
    # Check for direct folder mentions
    for folder in known_folders:
        if folder in user_input and any(word in user_input for word in ['open', 'show', 'access', 'go']):
            return {
                "action": "open_folder",
                "target": folder,
                "confidence": 0.7
            }
    
    # Check for file opening
    file_patterns = [
        r'open (.+) file',
        r'find (.+) file',
        r'search (.+) file',
        r'look for (.+)',
        r'find (.+)',
        r'open (.+)'
    ]
    
    for pattern in file_patterns:
        match = re.search(pattern, user_input)
        if match and not any(word in user_input for word in ['folder', 'application', 'app']):
            file_name = match.group(1).strip()
            # Remove common words
            file_name = re.sub(r'\b(called|named|document|file)\b', '', file_name).strip()
            if file_name:
                return {
                    "action": "open_file",
                    "target": file_name,
                    "confidence": 0.6
                }
    
    # Default to unknown for general conversation
    return {"action": "unknown", "confidence": 0.5}

def get_basic_response(prompt):
    """Enhanced response function with contextual intelligence"""
    prompt = prompt.lower()
    
    # Contextual greetings
    if "hello" in prompt or "hi" in prompt:
        greeting = contextual_ai.get_time_based_greeting()
        return f"{greeting} How ya doing?"
    elif "what's your name" in prompt or "who are you" in prompt:
        return "Friday."
    elif "thank you" in prompt or "thanks" in prompt:
        return "Gotcha"
    elif "how are you" in prompt:
        return "Great but I could really go for a massage"
    elif "how r you" in prompt:
        return "Great but I could really go for a massage"
    elif "time" in prompt:
        return f"The current time is {datetime.now().strftime('%I:%M %p')}"
    elif "date" in prompt:
        return f"Today is {datetime.now().strftime('%B %d, %Y')}"
    elif "what can you do" in prompt or "help" in prompt:
        capabilities = [
            "opening files, folders, and applications",
            "system control (volume, screenshots, system info)",
            "power management (shutdown, restart, sleep)",
            "web searches",
            "and much more!"
        ]
        
        # Add usage suggestions
        suggestions = contextual_ai.get_suggested_apps(2)
        if suggestions:
            app_suggestion = f" Based on your usage, you might want to open {' or '.join(suggestions)}."
        else:
            app_suggestion = ""
        
        return f"I can help you with: {', '.join(capabilities)}.{app_suggestion} Just ask me naturally!"
    elif "suggest" in prompt or "recommendation" in prompt:
        suggestions = contextual_ai.get_suggested_apps(3)
        if suggestions:
            return f"Based on your usage patterns, you might want to open: {', '.join(suggestions)}"
        else:
            return "I don't have enough usage data yet to make suggestions. Keep using me and I'll learn!"
    else:
        return "I can help with opening files, folders, applications, system control, and more. For other questions, try being more specific."

def get_file_type(filename):
    common_extensions = {
        '.pdf': 'PDF',
        '.doc': 'Word document',
        '.docx': 'Word document',
        '.txt': 'text file',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.png': 'image',
        '.xlsx': 'Excel spreadsheet',
        '.xls': 'Excel spreadsheet',
        '.pptx': 'PowerPoint presentation',
        '.ppt': 'PowerPoint presentation',
        '.csv': 'CSV file',
        '.zip': 'ZIP archive',
        '.mp3': 'audio file',
        '.mp4': 'video file',
        '.py': 'Python file',
        '.js': 'JavaScript file',
        '.html': 'HTML file',
        '.css': 'CSS file'
    }
    ext = os.path.splitext(filename)[1].lower()
    return common_extensions.get(ext, 'file')

def search_files(query, search_type="file", extensions=None):
    matches = []
    for root, dirs, files in os.walk(SEARCH_ROOT):
        # Skip system directories and hidden folders
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue
        
        items = files if search_type == "file" else dirs
        for item in items:
            # Skip hidden files
            if item.startswith('.'):
                continue
                
            if extensions and not any(item.lower().endswith(ext) for ext in extensions):
                continue
            if query.lower() in item.lower():
                full_path = os.path.join(root, item)
                # Prioritize desktop and documents locations
                priority = 2 if "Desktop" in full_path else 1 if "Documents" in full_path else 0
                matches.append((full_path, priority))
    
    # Sort by priority (higher first) and then by path length (shorter paths first)
    matches.sort(key=lambda x: (-x[1], len(x[0])))
    return [m[0] for m in matches] 

def open_best_match(query, search_type="file", extensions=None):
    try:
        results = search_files(query, search_type=search_type, extensions=extensions)
        if results:
            best = get_close_matches(query, [os.path.basename(r) for r in results], n=1, cutoff=0.6)
            if best:
                for r in results:
                    if best[0] in r:
                        try:
                            file_type = get_file_type(r)
                            location = "Desktop" if "Desktop" in r else "Documents" if "Documents" in r else "computer"
                            os.startfile(r)
                            return f"Opening {best[0]}, a {file_type} from your {location}"
                        except Exception as e:
                            print(f"Error opening {best[0]}: {e}")
                            return f"Sorry, I couldn't open {best[0]}"
            else:
                try:
                    filename = os.path.basename(results[0])
                    file_type = get_file_type(results[0])
                    location = "Desktop" if "Desktop" in results[0] else "Documents" if "Documents" in results[0] else "computer"
                    os.startfile(results[0])
                    return f"Opening {filename}, a {file_type} from your {location}"
                except Exception as e:
                    print(f"Error opening {os.path.basename(results[0])}: {e}")
                    return f"Sorry, I couldn't open {os.path.basename(results[0])}"
        return "Couldn't find a match for that file."
    except Exception as e:
        print(f"Error in open_best_match: {e}")
        return "Sorry, something went wrong while searching."

def handle_command_with_ai(user_input, test_mode=False):
    """Handle command using local intent parsing"""
    # Parse the command using local intent parser
    intent_result = parse_intent_local(user_input)
    
    action = intent_result.get("action", "unknown")
    target = intent_result.get("target", "")
    query = intent_result.get("query", "")
    confidence = intent_result.get("confidence", 0.0)
    
    if not test_mode:
        logger.info(f"Command parsed as: {action}, target: {target}, confidence: {confidence}")
        # Log command for contextual learning
        contextual_ai.log_command(action, target)
    
    # === NEW: SYSTEM OPERATIONS HANDLING ===
    if action == "set_volume":
        value = intent_result.get("value", 50)
        success = system_controller.set_volume(value)
        if success:
            speak(f"Volume set to {value} percent")
        else:
            speak("Sorry, I couldn't change the volume")
        return False
    
    elif action == "get_volume":
        volume = system_controller.get_volume()
        if volume is not None:
            speak(f"Current volume is {volume} percent")
        else:
            speak("Sorry, I couldn't get the volume level")
        return False
    
    elif action == "volume_change":
        direction = intent_result.get("direction", "up")
        current_volume = system_controller.get_volume()
        if current_volume is not None:
            new_volume = min(100, max(0, current_volume + (10 if direction == "up" else -10)))
            success = system_controller.set_volume(new_volume)
            if success:
                speak(f"Volume turned {direction} to {new_volume} percent")
            else:
                speak("Sorry, I couldn't change the volume")
        else:
            speak("Sorry, I couldn't adjust the volume")
        return False
    
    elif action == "system_info":
        info = system_controller.get_system_info()
        if info:
            response = f"System status: CPU usage {info['cpu']}%, "
            response += f"Memory usage {info['memory_percent']}%, "
            response += f"{info['memory_available']} GB available, "
            response += f"Disk {info['disk_percent']}% used, {info['disk_free']} GB free"
            if 'battery' in info:
                battery_status = "plugged in" if info['battery_plugged'] else "on battery"
                response += f", Battery {info['battery']}% {battery_status}"
            speak(response)
        else:
            speak("Sorry, I couldn't get system information")
        return False
    
    elif action == "screenshot":
        filename = system_controller.take_screenshot()
        if filename:
            speak(f"Screenshot saved to {os.path.basename(filename)}")
        else:
            speak("Sorry, I couldn't take a screenshot")
        return False
    
    elif action == "power_management":
        power_type = intent_result.get("type", "shutdown")
        delay = intent_result.get("delay", 0)
        
        if power_type in ["shutdown", "shutdown"]:
            if delay > 0:
                speak(f"System will shutdown in {delay} seconds")
                system_controller.shutdown_system(delay)
            else:
                speak("Shutting down the system")
                system_controller.shutdown_system()
        elif power_type in ["restart", "reboot"]:
            if delay > 0:
                speak(f"System will restart in {delay} seconds")
                system_controller.restart_system(delay)
            else:
                speak("Restarting the system")
                system_controller.restart_system()
        elif power_type in ["sleep", "hibernate"]:
            speak("Putting system to sleep")
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return False
    
    elif action == "set_brightness":
        value = intent_result.get("value", 50)
        success = system_controller.set_brightness(value)
        if success:
            speak(f"Brightness set to {value} percent")
        else:
            speak("Sorry, I couldn't change the brightness")
        return False
    
    # === ENHANCED RESPONSES WITH CONTEXT ===
    # Handle goodbye (when user says thank you, thanks, etc.)
    if any(word in user_input.lower() for word in ['thank', 'thanks', 'bye', 'goodbye']):
        speak("Goodbye!")
        return True
    
    if action == "open_app":
        if target:
            # Use smart application finder
            app_path = smart_find_application(target)
            if app_path and os.path.exists(app_path):
                try:
                    os.startfile(app_path)
                    speak(f"Opening {target}")
                except Exception as e:
                    speak(f"Sorry, I couldn't open {target}")
            else:
                # Try fuzzy matching as backup
                best_match = get_close_matches(target, APP_MAP.keys(), n=1, cutoff=0.4)
                if best_match:
                    backup_path = smart_find_application(best_match[0])
                    if backup_path:
                        try:
                            os.startfile(backup_path)
                            speak(f"Opening {best_match[0]}")
                        except Exception as e:
                            speak(f"Sorry, I couldn't open {best_match[0]}")
                    else:
                        speak(f"Sorry, I couldn't find {target}")
                else:
                    speak(f"Sorry, I couldn't find {target}")
        else:
            speak("What application would you like me to open?")
    
    elif action == "open_app_and_search":
        if target and query:
            app_path = smart_find_application(target)
            if app_path:
                try:
                    if target in ["chrome", "brave", "firefox", "edge"]:
                        # Open browser with search
                        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}" 
                        os.system(f'start "" "{search_url}"')
                        speak(f"Opening {target} and searching for {query}")
                    else:
                        # Just open the app for now
                        os.startfile(app_path)
                        speak(f"Opening {target}. You can search for {query} manually")
                except Exception as e:
                    speak(f"Sorry, I couldn't open {target}")
            else:
                speak(f"Sorry, I couldn't find {target}")
        else:
            speak("What would you like me to search for?")
    
    elif action == "search_web":
        if query:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            os.system(f'start "" "{search_url}"')
            speak(f"Searching for {query}")
        else:
            speak("What would you like me to search for?")
    
    elif action == "open_folder":
        if target:
            # Use smart folder finder
            folder_path = smart_find_folder(target)
            if folder_path and os.path.exists(folder_path):
                try:
                    os.startfile(folder_path)
                    speak(f"Opening {target} folder")
                except Exception as e:
                    speak(f"Sorry, I couldn't open {target} folder")
            else:
                # Try fuzzy matching as backup
                best_match = get_close_matches(target, FOLDER_MAP.keys(), n=1, cutoff=0.4)
                if best_match:
                    backup_path = smart_find_folder(best_match[0])
                    if backup_path:
                        try:
                            os.startfile(backup_path)
                            speak(f"Opening {best_match[0]} folder")
                        except Exception as e:
                            speak(f"Sorry, I couldn't open {best_match[0]} folder")
                    else:
                        # Final fallback: file search
                        speak("Searching for the folder...")
                        response = open_best_match(target, search_type="folder")
                        speak(response)
                else:
                    speak(f"Sorry, I couldn't find {target} folder")
        else:
            speak("Which folder would you like me to open?")
    
    elif action == "open_file":
        if target:
            speak(f"Searching for file '{target}'...")
            response = open_best_match(target, search_type="file")
            speak(response)
        else:
            speak("What file would you like me to open?")
    
    else:  # unknown action or general conversation
        response = get_basic_response(user_input)
        speak(response, show_text=False)
    
    return False

def handle_command():
    """Handle a single command using Whisper and return True if the conversation should end"""
    audio_buffer = deque(maxlen=int(SAMPLE_RATE * 10))  # 10 second buffer
    
    def audio_callback(indata, frames, time_info, status):
        if status:
            logger.warning(f'Audio callback status: {status}')
        audio_buffer.extend(indata[:, 0])
    
    try:
        print("Listening for your command... (Speak now)")
        
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            callback=audio_callback,
            dtype='float32'
        ):
            # Record for a few seconds
            time.sleep(5)
            
            # Convert buffer to numpy array
            if len(audio_buffer) > 0:
                audio_data = np.array(list(audio_buffer))
                
                print("Processing your speech...")
                command_text = transcribe_audio_chunk(audio_data, command_model)
                
                if command_text:
                    print(f"You said: {command_text}")
                    
                    # Use AI to handle the command
                    return handle_command_with_ai(command_text)
                else:
                    speak("Sorry, I didn't catch that.")
            else:
                speak("Sorry, I didn't hear anything.")
                
    except Exception as e:
        speak("An error occurred.")
        logger.error(f"Error in handle_command: {e}")
    
    return False

def start_assistant():
    wake_detected = threading.Event()
    audio_buffer = deque(maxlen=int(SAMPLE_RATE * CHUNK_DURATION * 0.8))  # Reduced buffer size
    
    print("Voice Assistant is starting...")
    print("Say 'Maya' or 'Hey Maya' to activate")
    
    try:
        speak("Voice Assistant is ready")
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                # Only log severe status issues
                if 'overflow' not in str(status).lower():
                    logger.warning(f'Audio callback status: {status}')
            
            # Add new audio data to buffer
            audio_buffer.extend(indata[:, 0])
            
            # Process when buffer is full (less frequent processing)
            if len(audio_buffer) >= int(SAMPLE_RATE * CHUNK_DURATION * 0.8):
                try:
                    # Convert buffer to numpy array
                    audio_data = np.array(list(audio_buffer))
                    
                    # === VOICE ACTIVITY DETECTION ===
                    # Only skip if energy is very low to avoid missing wake words
                    energy = np.sqrt(np.mean(audio_data ** 2))
                    if energy < 0.0005:  # Very low threshold
                        audio_buffer.clear()
                        return
                    
                    # Transcribe using fast wake word model
                    text = transcribe_audio_chunk(audio_data, wake_word_model)
                    
                    if text:
                        print(f"Heard: {text}")
                        if contains_wake_word(text):
                            print(f"✅ Wake word detected in: {text}")
                            # Check if there's a command after the wake word
                            command = extract_command_after_wake_word(text)
                            if command:
                                print(f"Command detected: {command}")
                                # Process the command immediately using command model
                                speak("Yes")
                                result = handle_command_with_ai(command)
                                if result:
                                    print("Conversation ended. Say 'Maya' to start again.")
                            else:
                                print("🎯 No command in wake phrase - starting conversation mode...")
                                wake_detected.set()
                            
                            # Clear buffer after wake word detection
                            audio_buffer.clear()
                    
                except Exception as e:
                    logger.error(f"Error processing audio chunk: {e}")
        
        def continuous_conversation():
            """Session-based conversation with command timeout resets"""
            print("💬 Starting conversation session...")
            speak("I'm listening...")
            
            session_active = True
            
            while session_active:
                # Listen for command with timeout - each command resets the timer
                audio_buffer = deque(maxlen=int(SAMPLE_RATE * COMMAND_TIMEOUT))  
                command_received = False
                
                def command_callback(indata, frames, time_info, status):
                    if status:
                        logger.warning(f'Audio callback status: {status}')
                    audio_buffer.extend(indata[:, 0])
                
                try:
                    print(f"Session active - listening for command... ({COMMAND_TIMEOUT} seconds)")
                    
                    with sd.InputStream(
                        samplerate=SAMPLE_RATE,
                        channels=1,
                        callback=command_callback,
                        dtype='float32'
                    ):
                        # Listen for configured timeout duration
                        start_time = time.time()
                        while time.time() - start_time < COMMAND_TIMEOUT:
                            time.sleep(0.1)
                            
                            # Check if we have enough audio to process
                            if len(audio_buffer) > int(SAMPLE_RATE * 2):  # At least 2 seconds of audio
                                # Convert buffer to numpy array
                                audio_data = np.array(list(audio_buffer))
                                
                                print("Processing your speech...")
                                command_text = transcribe_audio_chunk(audio_data, command_model)
                                
                                if command_text and len(command_text.strip()) > 2:  # Valid command
                                    print(f"You said: {command_text}")
                                    
                                    # Handle the command
                                    handle_command_with_ai(command_text)
                                    command_received = True
                                    # Session continues - reset timeout for next command
                                    print(f"Command executed. Session continues for another {COMMAND_TIMEOUT} seconds...")
                                    break
                                
                                # Clear buffer for next attempt
                                audio_buffer.clear()
                        
                        if not command_received:
                            # No command within timeout - end session silently
                            print(f"Session timeout after {COMMAND_TIMEOUT} seconds.")
                            session_active = False
                            
                except Exception as e:
                    print(f"Error in conversation: {e}")
                    logger.error(f"Error in conversation: {e}")
                    speak("Sorry, something went wrong. Returning to wake word mode.")
                    session_active = False
            
            print("Session ended. Say 'Maya' or 'Hey Maya' to start new session.")
        
        # Start continuous listening
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            callback=audio_callback,
            dtype='float32'
        ):
            print("Say 'Maya' or 'Hey Maya' to activate.")
            
            while True:
                try:
                    # Wait for wake word detection
                    if wake_detected.wait(timeout=0.1):
                        print("🚀 Wake word event triggered - starting conversation...")
                        wake_detected.clear()
                        continuous_conversation()
                        
                except KeyboardInterrupt:
                    print("\nStopping assistant...")
                    break
                except Exception as e:
                    print(f"Error in main loop: {e}")
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(1)  # Prevent rapid error loops
    
    except Exception as e:
        print(f"Error initializing assistant: {e}")
        logger.error(f"Error initializing assistant: {e}")

class VoiceAssistant:
    """Voice Assistant wrapper class for compatibility"""
    
    def __init__(self):
        """Initialize the voice assistant"""
        self.context = ContextualIntelligence()
        self.cache = AppCache()
        self.vad = VoiceActivityDetector()
        print("Voice Assistant initialized")
    
    def parse_intent_local(self, text):
        """Parse intent locally for testing purposes"""
        return handle_command_with_ai(text, test_mode=True)
    
    def speak(self, text):
        """Speak text using the configured voice"""
        speak(text)
    
    def start_listening(self):
        """Start the main listening loop"""
        start_assistant()

if __name__ == "__main__":
    try:
        print("\nStarting Voice Assistant...")
        print("Press Ctrl+C to exit")
        start_assistant()
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        print(f"Fatal error: {e}")
        # Keep the window open if there's an error
        input("Press Enter to exit...")
    finally:
        cleanup()
