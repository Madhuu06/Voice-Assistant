import os
from pathlib import Path

# Voice Settings
VOICE_RATE = 170
VOICE_VOLUME = 1.0

# Whisper Settings
WHISPER_WAKE_MODEL = "tiny"  # Fast model for wake word detection
WHISPER_COMMAND_MODEL = "base"  # Accurate model for command recognition

# Command Settings
COMMAND_TIMEOUT = 30  # Listen for commands for 30 seconds after wake word
COMMAND_PHRASE_LIMIT = 7

