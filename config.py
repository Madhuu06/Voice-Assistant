import os
from pathlib import Path

# API Keys
PORCUPINE_KEY = os.getenv('PORCUPINE_KEY', "Enter your Porcupine key here") #get your Porcupine key from https://console.porcupine.ai/

# Paths
BASE_DIR = Path(__file__).parent
WAKEWORDS_DIR = BASE_DIR / "wakewords"
WAKEWORD_PATH = WAKEWORDS_DIR / "hey_friday.ppn"

# Voice Settings
VOICE_RATE = 170
VOICE_VOLUME = 1.0

# Porcupine Settings
WAKE_WORD_SENSITIVITY = 0.7

# Command Settings
COMMAND_TIMEOUT = 5
COMMAND_PHRASE_LIMIT = 7

