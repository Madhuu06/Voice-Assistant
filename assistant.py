"""
╔══════════════════════════════════════════════════════════════════════╗
║  E.V.A — Enhanced Voice Assistant                                    ║
║  Push [F12] to talk. She listens, thinks, and responds.              ║
║  Fully offline. Fully private. Powered by Ollama + Whisper + Kokoro. ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import uuid
import atexit

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── Project imports ──────────────────────────────────────────
from config import (
    ASSISTANT_NAME, LLM_MODEL, VISION_ENABLED, MEMORY_LOG_COMMANDS,
)
from logger import setup_logging
from core import stt, tts, llm, vision
from core.memory import Memory
from tools import apps as app_tools

# ── Auto-discover and register all tools ────────────────────
# Import tool modules so their @registry.register decorators fire
import tools.system    # noqa: F401
import tools.web       # noqa: F401
import tools.desktop   # noqa: F401
import tools.apps      # noqa: F401
# Vision is registered in core/vision, import it too
import core.vision     # noqa: F401

from utils.activation import PushToTalk

logger = setup_logging()


# ══════════════════════════════════════════════════════════════
#  Main Pipeline: Audio → STT → LLM (with tools) → TTS
# ══════════════════════════════════════════════════════════════

def process_audio(audio_data, memory, session_id):
    """Main pipeline: transcribe → LLM tool-calling loop → TTS."""
    print("🧠 Processing speech...")
    text = stt.transcribe(audio_data, use_command_model=True)

    if not text or len(text.strip()) < 2:
        tts.speak("Didn't catch that.")
        return

    print(f"📝 You said: \"{text}\"")

    # Handle goodbye
    if any(w in text.lower() for w in ['goodbye', 'bye', 'go to sleep', 'shut up']):
        tts.speak("Goodbye.")
        return

    # Get conversation history and append current message
    history = memory.get_recent_context(session_id, n_turns=5)
    history.append({"role": "user", "content": text})

    print(f"\n💭 {ASSISTANT_NAME}: ", end="", flush=True)

    # LLM call — tool-calling loop handled inside llm.stream_chat
    full_response = llm.stream_chat(
        messages=history,
        on_sentence=lambda s: tts.speak(s, show_text=False),
    )

    if full_response:
        print(full_response)
    print()

    # Store in memory
    memory.add_message(session_id, "user", text)
    memory.add_message(session_id, "assistant", full_response or "")

    if MEMORY_LOG_COMMANDS:
        memory.log_command(command=text, action="llm", target="")


# ══════════════════════════════════════════════════════════════
#  Startup
# ══════════════════════════════════════════════════════════════

def print_banner():
    print()
    print("═" * 62)
    print(f"  🤖  {ASSISTANT_NAME} — Enhanced Voice Assistant")
    print("  Offline • Private • Intelligent")
    print("═" * 62)
    print()


def main():
    print_banner()
    print("⏳ Initializing subsystems...\n")

    # STT
    stt.load_models()

    # TTS (Kokoro → Edge TTS → pyttsx3)
    tts.init()

    # App discovery (for open_app tool)
    app_tools.init()

    # Memory
    memory = Memory()
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    memory.start_session(session_id)
    stats = memory.get_stats()
    if stats.get("total_commands", 0) > 0:
        print(f"📊 Memory: {stats['total_commands']} commands, {stats['total_sessions']} sessions\n")

    # LLM
    print("🧠 Checking Ollama LLM...")
    if llm.is_ollama_available():
        print(f"   └── ✅ Connected to Ollama ({LLM_MODEL})\n")
    else:
        print("   └── ⚠️  Ollama not reachable — start with: ollama serve\n")

    # Vision
    if VISION_ENABLED:
        if vision.is_available():
            from config import VISION_MODEL
            print(f"👁️  Vision: {VISION_MODEL} ready\n")
        else:
            print("👁️  Vision: unavailable (run: ollama pull moondream)\n")

    # Tool registry summary
    from tools.registry import registry
    print(f"🔧 Tools: {len(registry.tools)} registered\n")

    print(f"[READY] Push-to-Talk — press [{('F12').upper()}] to speak")
    print("   Press [Ctrl+C] to quit\n")

    tts.speak(f"{ASSISTANT_NAME} online.")

    ptt = PushToTalk(
        on_audio_ready=lambda audio: process_audio(audio, memory, session_id)
    )

    try:
        ptt.start_listening()
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n🔚 Shutting down {ASSISTANT_NAME}...")
        memory.end_session(session_id)
        memory.close()
        tts.cleanup()
        print(f"   {ASSISTANT_NAME} offline.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
