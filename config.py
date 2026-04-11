"""
config.py — Central configuration loader for Maya Voice Assistant.
Reads from config.yaml and exposes settings as module-level constants.
"""

import os
import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def _load_config():
    """Load config from YAML file, falling back to defaults."""
    defaults = {
        "assistant": {"name": "Maya", "personality": "friday"},
        "activation": {
            "mode": "push_to_talk",
            "push_to_talk_key": "f12",
            "wake_words": ["maya", "hey maya", "hello maya"],
        },
        "llm": {
            "model": "qwen:7b",
            "base_url": "http://localhost:11434/v1",
            "max_tokens": 512,
            "temperature": 0.7,
            "system_prompt": (
                "You are Maya, a voice assistant inspired by Tony Stark's F.R.I.D.A.Y. "
                "You are professional, concise, and slightly witty. Keep responses short "
                "and spoken-friendly. Two sentences max unless explaining something complex."
            ),
        },
        "stt": {
            "wake_model": "tiny",
            "command_model": "base",
            "sample_rate": 16000,
            "language": "en",
        },
        "tts": {
            "engine": "edge_tts",
            "edge_tts": {"voice": "en-US-AnaNeural"},
            "pyttsx3": {
                "rate": 170,
                "volume": 1.0,
                "preferred_voices": ["Zira", "Hazel", "David"],
            },
        },
        "vision": {"enabled": True, "model": "moondream"},
        "memory": {"db_path": "maya_memory.db", "max_history": 20, "log_commands": True},
        "commands": {"timeout": 30, "phrase_limit": 7},
    }

    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            # Deep merge user config over defaults
            _deep_merge(defaults, user_config)
    except Exception as e:
        print(f"⚠️  Could not load config.yaml, using defaults: {e}")

    return defaults


def _deep_merge(base, override):
    """Recursively merge override dict into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# ── Load config once at import time ──────────────────────────
_cfg = _load_config()

# ── Assistant ────────────────────────────────────────────────
ASSISTANT_NAME = _cfg["assistant"]["name"]
PERSONALITY = _cfg["assistant"]["personality"]

# ── Activation ───────────────────────────────────────────────
ACTIVATION_MODE = _cfg["activation"]["mode"]
PTT_KEY = _cfg["activation"]["push_to_talk_key"]
WAKE_WORDS = _cfg["activation"]["wake_words"]

# ── LLM ──────────────────────────────────────────────────────
LLM_MODEL = _cfg["llm"]["model"]
LLM_BASE_URL = _cfg["llm"]["base_url"]
LLM_MAX_TOKENS = _cfg["llm"]["max_tokens"]
LLM_TEMPERATURE = _cfg["llm"]["temperature"]
LLM_SYSTEM_PROMPT = _cfg["llm"]["system_prompt"]

# ── STT ──────────────────────────────────────────────────────
WHISPER_WAKE_MODEL = _cfg["stt"]["wake_model"]
WHISPER_COMMAND_MODEL = _cfg["stt"]["command_model"]
SAMPLE_RATE = _cfg["stt"]["sample_rate"]
STT_LANGUAGE = _cfg["stt"]["language"]

# ── TTS ──────────────────────────────────────────────────────
TTS_ENGINE = _cfg["tts"]["engine"]
EDGE_TTS_VOICE = _cfg["tts"]["edge_tts"]["voice"]
PYTTSX3_RATE = _cfg["tts"]["pyttsx3"]["rate"]
PYTTSX3_VOLUME = _cfg["tts"]["pyttsx3"]["volume"]
PYTTSX3_VOICES = _cfg["tts"]["pyttsx3"]["preferred_voices"]

# ── Vision ───────────────────────────────────────────────────
VISION_ENABLED = _cfg["vision"]["enabled"]
VISION_MODEL = _cfg["vision"]["model"]

# ── Memory ───────────────────────────────────────────────────
MEMORY_DB_PATH = _cfg["memory"]["db_path"]
MEMORY_MAX_HISTORY = _cfg["memory"]["max_history"]
MEMORY_LOG_COMMANDS = _cfg["memory"]["log_commands"]

# ── Commands ─────────────────────────────────────────────────
COMMAND_TIMEOUT = _cfg["commands"]["timeout"]
COMMAND_PHRASE_LIMIT = _cfg["commands"]["phrase_limit"]

# ── Legacy aliases (backward compatibility) ──────────────────
VOICE_RATE = PYTTSX3_RATE
VOICE_VOLUME = PYTTSX3_VOLUME
