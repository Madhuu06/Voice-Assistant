"""
core/tts.py — Text-to-Speech module with multiple engine support.
Priority: Edge TTS (neural, high quality) → ElevenLabs (cloud) → pyttsx3 (system)

Edge TTS uses Microsoft's neural voices — same quality as Azure,
no API key required, and far superior to pyttsx3.
"""

import os
import time
import asyncio
import threading
import tempfile
from config import (
    TTS_ENGINE, EDGE_TTS_VOICE, PYTTSX3_RATE, PYTTSX3_VOLUME, PYTTSX3_VOICES,
)
from logger import setup_logging

logger = setup_logging()

# ── Engine availability flags ────────────────────────────────
EDGE_TTS_AVAILABLE = False
PYTTSX3_AVAILABLE = False

_pyttsx3_engine = None
_tts_lock = threading.Lock()

# Edge TTS voice from config
EDGE_VOICE = EDGE_TTS_VOICE
# Other great options (can be set in config.yaml):
#   "en-US-JennyNeural"     — warm, professional female
#   "en-US-AriaNeural"      — expressive female
#   "en-GB-SoniaNeural"     — British female
#   "en-US-GuyNeural"       — male voice


# ── Edge TTS Setup ───────────────────────────────────────────

def _init_edge_tts():
    """Check if edge-tts is available."""
    global EDGE_TTS_AVAILABLE
    try:
        import edge_tts
        EDGE_TTS_AVAILABLE = True
        logger.info(f"Edge TTS available (voice: {EDGE_VOICE})")
    except ImportError:
        logger.warning("edge-tts not installed -- run: pip install edge-tts")
        EDGE_TTS_AVAILABLE = False


def _init_pyttsx3():
    """Initialize pyttsx3 as fallback TTS."""
    global PYTTSX3_AVAILABLE, _pyttsx3_engine
    try:
        import pyttsx3
        _pyttsx3_engine = pyttsx3.init()
        voices = _pyttsx3_engine.getProperty('voices')

        # Select preferred voice
        selected = None
        for pref in PYTTSX3_VOICES:
            for v in voices:
                if pref in v.name:
                    selected = v
                    break
            if selected:
                break

        if selected:
            _pyttsx3_engine.setProperty('voice', selected.id)
            logger.info(f"pyttsx3 voice: {selected.name}")
        else:
            logger.info("pyttsx3 using system default voice")

        _pyttsx3_engine.setProperty('rate', PYTTSX3_RATE)
        _pyttsx3_engine.setProperty('volume', PYTTSX3_VOLUME)
        PYTTSX3_AVAILABLE = True
    except Exception as e:
        logger.error(f"pyttsx3 init failed: {e}")
        PYTTSX3_AVAILABLE = False


# ── Initialize on import ────────────────────────────────────

def init():
    """Initialize TTS engines. Call once at startup."""
    print("🔈 Initializing TTS engines...")

    _init_edge_tts()
    if not EDGE_TTS_AVAILABLE:
        print("   ├── Edge TTS unavailable, trying pyttsx3...")

    _init_pyttsx3()  # Always init as fallback

    engine_name = (
        f"Edge TTS ({EDGE_VOICE})" if EDGE_TTS_AVAILABLE else
        "pyttsx3" if PYTTSX3_AVAILABLE else
        "NONE"
    )
    print(f"   └── Active TTS engine: {engine_name}\n")


# ── Public API ───────────────────────────────────────────────

def speak(text, show_text=True):
    """
    Speak text using the best available TTS engine.

    Args:
        text: The string to speak.
        show_text: If True, also print the text to console.
    """
    if not text or not text.strip():
        return

    if show_text:
        print(f"    Maya: {text}")

    with _tts_lock:
        # Try ElevenLabs first (if configured)
        try:
            from elevenlabs_voice import speak_with_elevenlabs, is_elevenlabs_ready
            if is_elevenlabs_ready():
                if speak_with_elevenlabs(text):
                    return
                logger.warning("ElevenLabs failed, falling back")
        except ImportError:
            pass

        # Try Edge TTS
        if EDGE_TTS_AVAILABLE:
            if _speak_edge_tts(text):
                return

        # Fallback to pyttsx3
        if PYTTSX3_AVAILABLE:
            _speak_pyttsx3(text)
            return

        # Nothing available
        logger.error("No TTS engine available!")


def speak_streaming(text, show_text=True):
    """
    Speak text optimized for streaming — called per-sentence
    during LLM streaming output.
    """
    speak(text, show_text=show_text)


# ── Edge TTS Engine ─────────────────────────────────────────

def _speak_edge_tts(text):
    """Generate and play speech using Edge TTS (Microsoft neural voices)."""
    try:
        import edge_tts
        import sounddevice as sd
        import soundfile as sf
        import io

        # Use unique temp file to avoid permission conflicts
        temp_path = tempfile.mktemp(suffix='.mp3', prefix='maya_tts_')

        # Run async edge-tts in a sync context
        async def _generate():
            communicate = edge_tts.Communicate(text, EDGE_VOICE)
            await communicate.save(temp_path)

        # Create new event loop if needed (avoid issues in threaded contexts)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context, use a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(lambda: asyncio.run(_generate())).result()
            else:
                loop.run_until_complete(_generate())
        except RuntimeError:
            asyncio.run(_generate())

        # Play the generated audio
        _play_audio_file(temp_path)

        # Cleanup — retry if file is still locked by pygame
        for _ in range(5):
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                break
            except OSError:
                time.sleep(0.2)

        return True

    except Exception as e:
        logger.error(f"Edge TTS error: {e}")
        return False


def _play_audio_file(filepath):
    """Play an audio file using pygame (reliable for mp3)."""
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

    except ImportError:
        # Fallback: use built-in Windows player
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-Command",
                 f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"],
                timeout=30, capture_output=True
            )
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
    except Exception as e:
        logger.error(f"pygame playback error: {e}")


# ── pyttsx3 Engine ───────────────────────────────────────────

def _speak_pyttsx3(text):
    """Speak using system pyttsx3 engine."""
    try:
        time.sleep(0.1)
        _pyttsx3_engine.say(text)
        _pyttsx3_engine.runAndWait()
    except Exception as e:
        logger.error(f"pyttsx3 TTS error: {e}")


# ── Cleanup ──────────────────────────────────────────────────

def cleanup():
    """Clean up TTS resources."""
    global _pyttsx3_engine
    try:
        if _pyttsx3_engine:
            _pyttsx3_engine.stop()
    except Exception:
        pass

    # Clean up any leftover temp files
    import glob
    for f in glob.glob(os.path.join(tempfile.gettempdir(), 'maya_tts_*.mp3')):
        try:
            os.unlink(f)
        except OSError:
            pass
