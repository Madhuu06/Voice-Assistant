"""
utils/activation.py — Push-to-Talk (F12) and optional wake word activation.
Handles the user's input trigger for the voice assistant.
"""

import time
import threading
import numpy as np
import sounddevice as sd
from collections import deque
from config import ACTIVATION_MODE, PTT_KEY, SAMPLE_RATE
from logger import setup_logging

logger = setup_logging()

# ── Keyboard library (for Push-to-Talk) ──────────────────────
KEYBOARD_AVAILABLE = False
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    logger.warning("'keyboard' module not installed — Push-to-Talk unavailable. Install with: pip install keyboard")


class PushToTalk:
    """
    Push-to-Talk activation using F12 key.

    Tap F12 → start recording
    Automatic silence detection stops recording
    Tap F12 again to stop manually
    """

    def __init__(self, on_audio_ready=None, silence_threshold=0.005, silence_duration=1.5):
        """
        Args:
            on_audio_ready: Callback(audio_np_array) when recording is complete.
            silence_threshold: RMS energy below this = silence.
            silence_duration: Seconds of silence before auto-stopping.
        """
        self.on_audio_ready = on_audio_ready
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

        self._recording = False
        self._processing = False  # True while STT/LLM is working
        self._audio_buffer = []
        self._stream = None
        self._stop_event = threading.Event()
        self._record_thread = None
        self._last_key_time = 0  # Debounce tracker

    def start_listening(self):
        """Start listening for F12 key presses. Blocks the calling thread."""
        if not KEYBOARD_AVAILABLE:
            print("'keyboard' module required for Push-to-Talk.")
            print("   Install it with: pip install keyboard")
            return

        print(f"[READY] Push-to-Talk -- press [{PTT_KEY.upper()}] to speak")
        print("   Press [Ctrl+C] to quit\n")

        keyboard.on_press_key(PTT_KEY, self._on_key_press)

        try:
            # Keep the main thread alive
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping assistant...")
            keyboard.unhook_all()

    def _on_key_press(self, event):
        """Handle F12 key press with debounce."""
        now = time.time()

        # Debounce: ignore rapid key repeats (within 1 second)
        if now - self._last_key_time < 1.0:
            return
        self._last_key_time = now

        # Don't start recording while processing previous command
        if self._processing:
            return

        if self._recording:
            # Already recording — stop manually
            self._stop_recording()
        else:
            # Start recording
            self._start_recording()

    def _start_recording(self):
        """Begin capturing audio from the microphone."""
        if self._recording:
            return

        self._recording = True
        self._audio_buffer = []
        self._stop_event.clear()

        print("[REC] Recording... (speak now, silence auto-stops)")

        self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()

    def _record_loop(self):
        """Record audio until silence is detected or manual stop."""
        silence_start = None
        has_heard_voice = False

        def audio_callback(indata, frames, time_info, status):
            nonlocal silence_start, has_heard_voice

            if status:
                logger.warning(f"Audio status: {status}")

            self._audio_buffer.append(indata.copy())

            # Calculate energy
            energy = float(np.sqrt(np.mean(indata ** 2)))

            if energy > self.silence_threshold:
                has_heard_voice = True
                silence_start = None
            elif has_heard_voice:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > self.silence_duration:
                    self._stop_event.set()

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                callback=audio_callback,
                dtype='float32',
                blocksize=int(SAMPLE_RATE * 0.1),  # 100ms blocks
            ):
                # Wait for stop signal with a max recording time of 30s
                self._stop_event.wait(timeout=30)

        except Exception as e:
            logger.error(f"Recording error: {e}")

        self._recording = False
        self._process_recording()

    def _stop_recording(self):
        """Manually stop recording."""
        self._stop_event.set()

    def _process_recording(self):
        """Process the recorded audio buffer."""
        if not self._audio_buffer:
            print("  No audio captured.")
            print(f"\n[READY] Press [{PTT_KEY.upper()}] to speak again")
            return

        # Concatenate all audio chunks
        audio_data = np.concatenate(self._audio_buffer, axis=0).flatten()

        # Check if there's meaningful audio
        energy = float(np.sqrt(np.mean(audio_data ** 2)))
        if energy < 0.001:
            print("  Too quiet -- didn't catch anything.")
            print(f"\n[READY] Press [{PTT_KEY.upper()}] to speak again")
            return

        duration = len(audio_data) / SAMPLE_RATE
        print(f"  Recording stopped ({duration:.1f}s captured)")

        # Fire callback — block F12 during processing
        if self.on_audio_ready:
            self._processing = True
            try:
                self.on_audio_ready(audio_data)
            finally:
                self._processing = False

        print(f"\n[READY] Press [{PTT_KEY.upper()}] to speak again")
