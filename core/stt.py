"""
core/stt.py — Speech-to-Text module using OpenAI Whisper.
Handles model loading, audio transcription, and voice activity detection.
"""

import numpy as np
import whisper
from config import WHISPER_WAKE_MODEL, WHISPER_COMMAND_MODEL, SAMPLE_RATE
from logger import setup_logging

logger = setup_logging()

# ── Model Loading ────────────────────────────────────────────
_wake_model = None
_command_model = None


def load_models():
    """Load Whisper models (called once at startup)."""
    global _wake_model, _command_model
    print("🔊 Loading Whisper STT models...")
    print("   ├── tiny model (wake word detection)...")
    _wake_model = whisper.load_model(WHISPER_WAKE_MODEL)
    print("   └── base model (command recognition)...")
    _command_model = whisper.load_model(WHISPER_COMMAND_MODEL)
    print("   ✅ Whisper models loaded.\n")


def get_wake_model():
    if _wake_model is None:
        load_models()
    return _wake_model


def get_command_model():
    if _command_model is None:
        load_models()
    return _command_model


# ── Transcription ────────────────────────────────────────────

def transcribe(audio_data, use_command_model=True):
    """
    Transcribe a numpy audio array to text.

    Args:
        audio_data: numpy float32 array of audio samples at 16kHz
        use_command_model: If True, use the accurate base model.
                          If False, use the fast tiny model.

    Returns:
        Lowercase stripped transcription string, or empty string on failure.
    """
    model = get_command_model() if use_command_model else get_wake_model()

    try:
        if len(audio_data) == 0:
            return ""

        # Normalize to float32 range [-1, 1]
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Ensure mono (1D)
        if len(audio_data.shape) > 1:
            audio_data = audio_data.flatten()

        # Pad to minimum processable length (0.1s)
        min_length = int(SAMPLE_RATE * 0.1)
        if len(audio_data) < min_length:
            audio_data = np.pad(audio_data, (0, min_length - len(audio_data)))

        result = model.transcribe(audio_data, language="en")
        return result["text"].strip().lower()

    except Exception as e:
        logger.error(f"STT transcription error: {e}")
        return ""


# ── Voice Activity Detection ────────────────────────────────

class VoiceActivityDetector:
    """Simple energy-based Voice Activity Detection."""

    def __init__(self, energy_threshold=0.001, silence_duration=0.5):
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self._last_voice_time = 0

    def is_voice_active(self, audio_data):
        """Check if the audio chunk contains voice activity."""
        import time
        energy = np.sqrt(np.mean(audio_data ** 2))

        if energy > self.energy_threshold:
            self._last_voice_time = time.time()
            return True

        return (time.time() - self._last_voice_time) < self.silence_duration

    def get_energy(self, audio_data):
        """Get RMS energy of an audio chunk."""
        return float(np.sqrt(np.mean(audio_data ** 2)))
