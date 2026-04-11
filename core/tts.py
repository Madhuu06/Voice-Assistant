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
import queue
from config import (
    TTS_ENGINE, EDGE_TTS_VOICE, EDGE_TTS_RATE, PYTTSX3_RATE, PYTTSX3_VOLUME, PYTTSX3_VOICES,
    ASSISTANT_NAME
)
from logger import setup_logging

logger = setup_logging()

# ── Engine availability flags ────────────────────────────────
EDGE_TTS_AVAILABLE = False
PYTTSX3_AVAILABLE = False

_pyttsx3_engine = None
_tts_lock = threading.Lock()

# Edge TTS voice and rate from config
EDGE_VOICE = EDGE_TTS_VOICE
EDGE_RATE = EDGE_TTS_RATE

# TTS Pipelining setup
_tts_text_queue = queue.Queue()
_tts_audio_queue = queue.Queue()
_tts_generator_thread = None
_tts_player_thread = None
_tts_stop_event = threading.Event()

def _tts_generator_worker():
    """Generates audio files in the background, piping them to the player thread."""
    while True:
        item = _tts_text_queue.get()
        if item is None:
            break
        text, show_text = item
        
        if _tts_stop_event.is_set():
            _tts_text_queue.task_done()
            continue

        try:
            # Generate Edge TTS file
            if EDGE_TTS_AVAILABLE:
                import edge_tts, asyncio, concurrent.futures
                temp_path = tempfile.mktemp(suffix='.mp3', prefix='maya_tts_')
                async def _generate():
                    communicate = edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATE)
                    await communicate.save(temp_path)
                    
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            pool.submit(lambda: asyncio.run(_generate())).result()
                    else:
                        loop.run_until_complete(_generate())
                except RuntimeError:
                    asyncio.run(_generate())
                    
                _tts_audio_queue.put((temp_path, show_text, text, "edge"))
            else:
                _tts_audio_queue.put((None, show_text, text, "pyttsx3"))
        except Exception:
            _tts_audio_queue.put((None, show_text, text, "pyttsx3"))
            
        _tts_text_queue.task_done()

def _tts_player_worker():
    """Plays generated audio files sequentially."""
    while True:
        item = _tts_audio_queue.get()
        if item is None:
            break
        filepath, show_text, text, engine = item
        
        if _tts_stop_event.is_set():
            if filepath and os.path.exists(filepath):
                try: os.unlink(filepath)
                except OSError: pass
            _tts_audio_queue.task_done()
            continue

        if show_text:
            print(f"    {ASSISTANT_NAME}: {text}")
            
        if engine == "edge" and filepath:
            _play_audio_file(filepath)
            for _ in range(5):
                try:
                    if os.path.exists(filepath): os.unlink(filepath)
                    break
                except OSError: time.sleep(0.2)
        else:
            if PYTTSX3_AVAILABLE:
                _speak_pyttsx3(text)
                
        _tts_audio_queue.task_done()

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

    global _tts_generator_thread, _tts_player_thread
    if _tts_generator_thread is None:
        _tts_generator_thread = threading.Thread(target=_tts_generator_worker, daemon=True)
        _tts_player_thread = threading.Thread(target=_tts_player_worker, daemon=True)
        _tts_generator_thread.start()
        _tts_player_thread.start()


# ── Public API ───────────────────────────────────────────────

def speak(text, show_text=True):
    """
    Queue text to be spoken using the best available TTS engine.
    This does not block, allowing LLM or other tasks to flow instantly.
    """
    if not text or not text.strip():
        return
    _tts_text_queue.put((text, show_text))

# Old synchronous fallback removed to prevent loop lock
def _process_speak(text, show_text=True):
    pass



def stop():
    """Interrupt current TTS playback and clear the queue."""
    _tts_stop_event.set()
    
    # Empty queues
    while not _tts_text_queue.empty():
        try:
            _tts_text_queue.get_nowait()
            _tts_text_queue.task_done()
        except queue.Empty: break
        
    while not _tts_audio_queue.empty():
        try:
            item = _tts_audio_queue.get_nowait()
            if item and item[0] and os.path.exists(item[0]):
                try: os.unlink(item[0])
                except OSError: pass
            _tts_audio_queue.task_done()
        except queue.Empty: break
            
    # Stop pygame playback
    try:
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass


def _speak_edge_tts(text):
    """Fallback legacy direct usage if needed"""
    pass


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
    
    if _tts_text_queue:
        _tts_text_queue.put(None)
    if _tts_audio_queue:
        _tts_audio_queue.put(None)
        
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
