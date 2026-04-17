"""
core/tts.py — Multi-engine TTS with dual-queue pipelined playback.

Engine priority: Kokoro (offline, local) → Edge TTS (neural, cloud) → pyttsx3 (system)

Architecture:
  Generator thread: text → audio (Kokoro numpy array or Edge TTS mp3)
  Player thread:    audio → speakers (sounddevice or pygame)

This means generation of next sentence overlaps with playback of current,
eliminating inter-sentence pauses completely.
"""

import os
import io
import time
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
KOKORO_AVAILABLE = False
EDGE_TTS_AVAILABLE = False
PYTTSX3_AVAILABLE = False

_pyttsx3_engine = None
_tts_lock = threading.Lock()
_kokoro = None

# Config
EDGE_VOICE = EDGE_TTS_VOICE
EDGE_RATE = EDGE_TTS_RATE
KOKORO_VOICE = "af_sarah"   # Best quality female voice
KOKORO_SPEED = 1.15         # +15% speed

# ── Dual-queue pipeline ──────────────────────────────────────
_tts_text_queue = queue.Queue()
_tts_audio_queue = queue.Queue()
_tts_generator_thread = None
_tts_player_thread = None
_tts_stop_event = threading.Event()


def _tts_generator_worker():
    """Generates audio in background, feeds player thread."""
    while True:
        item = _tts_text_queue.get()
        if item is None:
            break
        text, show_text = item

        if _tts_stop_event.is_set():
            _tts_text_queue.task_done()
            continue

        try:
            if KOKORO_AVAILABLE and _kokoro is not None:
                samples, sample_rate = _kokoro.create(
                    text, voice=KOKORO_VOICE, speed=KOKORO_SPEED, lang="en-us"
                )
                _tts_audio_queue.put(("kokoro", samples, sample_rate, show_text, text))

            elif EDGE_TTS_AVAILABLE:
                import edge_tts, asyncio, concurrent.futures
                temp_path = tempfile.mktemp(suffix='.mp3', prefix='eva_tts_')

                async def _gen():
                    communicate = edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATE)
                    await communicate.save(temp_path)

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            pool.submit(lambda: asyncio.run(_gen())).result()
                    else:
                        loop.run_until_complete(_gen())
                except RuntimeError:
                    asyncio.run(_gen())

                _tts_audio_queue.put(("edge", temp_path, None, show_text, text))

            else:
                _tts_audio_queue.put(("pyttsx3", None, None, show_text, text))

        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            _tts_audio_queue.put(("pyttsx3", None, None, show_text, text))

        _tts_text_queue.task_done()


def _tts_player_worker():
    """Plays generated audio sequentially."""
    while True:
        item = _tts_audio_queue.get()
        if item is None:
            break
        engine, data, sample_rate, show_text, text = item

        if _tts_stop_event.is_set():
            if engine == "edge" and data and os.path.exists(data):
                try:
                    os.unlink(data)
                except OSError:
                    pass
            _tts_audio_queue.task_done()
            continue

        if show_text:
            print(f"    {ASSISTANT_NAME}: {text}")

        try:
            if engine == "kokoro" and data is not None:
                _play_numpy_audio(data, sample_rate)

            elif engine == "edge" and data:
                _play_audio_file(data)
                for _ in range(5):
                    try:
                        if os.path.exists(data):
                            os.unlink(data)
                        break
                    except OSError:
                        time.sleep(0.2)

            elif PYTTSX3_AVAILABLE:
                _speak_pyttsx3(text)

        except Exception as e:
            logger.error(f"TTS playback error: {e}")

        _tts_audio_queue.task_done()


# ── Engine Init ──────────────────────────────────────────────

def _init_kokoro():
    """Try to initialize Kokoro local TTS."""
    global KOKORO_AVAILABLE, _kokoro
    # Use int8 model for 16GB RAM — 88MB vs 310MB, negligible quality difference
    model_path = "kokoro-v1.0.int8.onnx"
    voices_path = "voices-v1.0.bin"

    if not (os.path.exists(model_path) and os.path.exists(voices_path)):
        logger.info("Kokoro model files not found — will attempt download")
        if _download_kokoro_models(model_path, voices_path):
            logger.info("Kokoro models downloaded successfully")
        else:
            return

    try:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(model_path, voices_path)
        KOKORO_AVAILABLE = True
        logger.info("Kokoro TTS ready (offline, local)")
    except Exception as e:
        logger.warning(f"Kokoro init failed: {e}")


def _download_kokoro_models(model_path, voices_path):
    """Download Kokoro model files from GitHub releases if missing."""
    try:
        import requests
        BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
        files = {
            model_path: BASE + "kokoro-v1.0.int8.onnx",
            voices_path: BASE + "voices-v1.0.bin",
        }
        for dest, url in files.items():
            if os.path.exists(dest):
                continue
            print(f"   ├── Downloading Kokoro model: {os.path.basename(dest)} ...")
            r = requests.get(url, stream=True, timeout=120)
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        logger.warning(f"Kokoro download failed: {e}")
        return False



def _init_edge_tts():
    """Check if edge-tts is available."""
    global EDGE_TTS_AVAILABLE
    try:
        import edge_tts
        EDGE_TTS_AVAILABLE = True
        logger.info(f"Edge TTS available (voice: {EDGE_VOICE})")
    except ImportError:
        EDGE_TTS_AVAILABLE = False


def _init_pyttsx3():
    """Initialize pyttsx3 as last-resort fallback."""
    global PYTTSX3_AVAILABLE, _pyttsx3_engine
    try:
        import pyttsx3
        _pyttsx3_engine = pyttsx3.init()
        voices = _pyttsx3_engine.getProperty('voices')
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
        _pyttsx3_engine.setProperty('rate', PYTTSX3_RATE)
        _pyttsx3_engine.setProperty('volume', PYTTSX3_VOLUME)
        PYTTSX3_AVAILABLE = True
    except Exception as e:
        logger.error(f"pyttsx3 init failed: {e}")
        PYTTSX3_AVAILABLE = False


def init():
    """Initialize TTS engines. Call once at startup."""
    print("🔈 Initializing TTS engines...")

    _init_kokoro()
    if not KOKORO_AVAILABLE:
        _init_edge_tts()
    if not KOKORO_AVAILABLE and not EDGE_TTS_AVAILABLE:
        print("   ├── Kokoro + Edge TTS unavailable, falling back to pyttsx3...")
    _init_pyttsx3()  # Always init as final fallback

    if KOKORO_AVAILABLE:
        engine_label = "Kokoro (offline)"
    elif EDGE_TTS_AVAILABLE:
        engine_label = f"Edge TTS ({EDGE_VOICE})"
    elif PYTTSX3_AVAILABLE:
        engine_label = "pyttsx3 (system)"
    else:
        engine_label = "NONE"

    print(f"   └── Active TTS engine: {engine_label}\n")

    global _tts_generator_thread, _tts_player_thread
    if _tts_generator_thread is None:
        _tts_generator_thread = threading.Thread(target=_tts_generator_worker, daemon=True)
        _tts_player_thread = threading.Thread(target=_tts_player_worker, daemon=True)
        _tts_generator_thread.start()
        _tts_player_thread.start()


# ── Public API ───────────────────────────────────────────────

def speak(text, show_text=True):
    """Queue text to be spoken. Non-blocking."""
    if not text or not text.strip():
        return
    _tts_text_queue.put((text.strip(), show_text))


def stop():
    """Stop all active and queued TTS playback."""
    _tts_stop_event.set()

    # Drain queues
    for q in (_tts_text_queue, _tts_audio_queue):
        while not q.empty():
            try:
                item = q.get_nowait()
                # Clean up any edge TTS temp files
                if isinstance(item, tuple) and len(item) > 1:
                    if item[0] == "edge" and item[1] and os.path.exists(str(item[1])):
                        try:
                            os.unlink(item[1])
                        except OSError:
                            pass
                q.task_done()
            except queue.Empty:
                break

    # Stop sounddevice
    try:
        import sounddevice as sd
        sd.stop()
    except Exception:
        pass

    # Stop pygame
    try:
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:
        pass


# ── Playback Helpers ─────────────────────────────────────────

def _play_numpy_audio(samples, sample_rate):
    """Play a numpy audio array via sounddevice (zero file I/O)."""
    try:
        import sounddevice as sd
        sd.play(samples, sample_rate)
        sd.wait()
    except Exception as e:
        logger.error(f"sounddevice playback error: {e}")


def _play_audio_file(filepath):
    """Play an audio file using pygame."""
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    except ImportError:
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


def _speak_pyttsx3(text):
    """Speak using pyttsx3."""
    try:
        time.sleep(0.05)
        _pyttsx3_engine.say(text)
        _pyttsx3_engine.runAndWait()
    except Exception as e:
        logger.error(f"pyttsx3 error: {e}")


# ── Cleanup ──────────────────────────────────────────────────

def cleanup():
    """Shut down TTS threads and clean up resources."""
    global _pyttsx3_engine
    _tts_text_queue.put(None)
    _tts_audio_queue.put(None)
    try:
        if _pyttsx3_engine:
            _pyttsx3_engine.stop()
    except Exception:
        pass
    import glob
    for f in glob.glob(os.path.join(tempfile.gettempdir(), 'eva_tts_*.mp3')):
        try:
            os.unlink(f)
        except OSError:
            pass
