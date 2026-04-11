"""
╔═══════════════════════════════════════════════════════════════════════╗
║  M.A.Y.A — Modular Adaptive Your Assistant                          ║
║  Inspired by Tony Stark's F.R.I.D.A.Y.                              ║
║                                                                       ║
║  Push [F12] to talk. She listens, thinks, and responds.             ║
║  Fully offline. Fully private. Powered by Ollama + Whisper + Kokoro.║
╚═══════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import sys
import time
import uuid
import atexit
from datetime import datetime

# Force UTF-8 output on Windows (prevents cp1252 encoding crashes)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── Project imports ──────────────────────────────────────────
from config import (
    ASSISTANT_NAME, LLM_SYSTEM_PROMPT, ACTIVATION_MODE, PTT_KEY,
    COMMAND_TIMEOUT, VISION_ENABLED, MEMORY_LOG_COMMANDS,
)
from logger import setup_logging
from core import stt, tts, llm
from core.memory import Memory
from core import vision
from tools import system as sys_tools
from tools import apps as app_tools
from tools import web as web_tools
from utils.activation import PushToTalk

logger = setup_logging()


# ═══════════════════════════════════════════════════════════════
#  Intent Parser — deterministic actions before LLM fallback
# ═══════════════════════════════════════════════════════════════

def parse_intent(user_input):
    """
    Parse user input for deterministic actions (open app, volume, etc.).
    Returns an intent dict, or None if the LLM should handle it.
    """
    text = user_input.lower().strip()
    # Strip filler words
    text = re.sub(r'\b(could you|can you|please|would you|my|the)\b', '', text).strip()

    # ── Volume ───────────────────────────────────────────────
    m = re.search(r'(?:set\s+)?volume\s+(?:to\s+)?(\d+)', text)
    if m:
        return {"action": "set_volume", "value": int(m.group(1))}

    # Catch: "turn volume up/down", "turn the voice down", "lower the volume", "increase volume"
    if re.search(r'(?:turn|volume|voice|sound)\s+(?:the\s+)?(?:volume\s+|voice\s+|sound\s+)?(up|down)', text):
        direction = "up" if "up" in text else "down"
        return {"action": "volume_change", "direction": direction}

    if re.search(r'\b(lower|reduce|decrease|softer|quieter)\b.*\b(volume|voice|sound)\b', text):
        return {"action": "volume_change", "direction": "down"}

    if re.search(r'\b(raise|increase|higher|louder)\b.*\b(volume|voice|sound)\b', text):
        return {"action": "volume_change", "direction": "up"}

    if re.search(r'\b(mute|unmute)\b', text):
        return {"action": "mute"}

    if re.search(r'what.*volume|volume.*what|current volume', text):
        return {"action": "get_volume"}

    # ── System Info ──────────────────────────────────────────
    if any(w in text for w in ['system info', 'system status', 'cpu', 'ram', 'memory usage', 'battery']):
        return {"action": "system_info"}

    # ── Screenshot ───────────────────────────────────────────
    if any(w in text for w in ['screenshot', 'capture screen', 'screen capture', 'take a screenshot']):
        return {"action": "screenshot"}

    # ── Screen Awareness ─────────────────────────────────────
    screen_patterns = [
        r"what(?:'s| is) on (?:my |the )?screen",
        r"(?:read|describe|summarize|explain|look at) (?:my |the )?screen",
        r"what does this (?:say|mean|show)",
        r"what(?:'s| is) this (?:error|message|window)",
        r"summarize (?:this|what's here)",
    ]
    for pattern in screen_patterns:
        if re.search(pattern, text):
            return {"action": "describe_screen", "prompt": user_input}

    # ── Power Management ─────────────────────────────────────
    m = re.search(r'\b(shutdown|shut down|turn off)\b', text)
    if m:
        delay_m = re.search(r'(\d+)\s*(?:seconds?|secs?|minutes?|mins?)', text)
        delay = int(delay_m.group(1)) if delay_m else 10
        return {"action": "shutdown", "delay": delay}

    m = re.search(r'\b(restart|reboot)\b', text)
    if m:
        return {"action": "restart"}

    if re.search(r'\b(sleep|hibernate)\b', text):
        return {"action": "sleep"}

    # ── Brightness ───────────────────────────────────────────
    m = re.search(r'(?:set\s+)?brightness\s+(?:to\s+)?(\d+)', text)
    if m:
        return {"action": "set_brightness", "value": int(m.group(1))}

    if re.search(r'\b(lower|reduce|decrease|dim)\b.*\bbrightness\b', text) or re.search(r'\bdim\b.*\bscreen\b', text):
        return {"action": "set_brightness", "value": 30}

    if re.search(r'\b(raise|increase|higher|brighten)\b.*\bbrightness\b', text) or re.search(r'\bbrighten\b', text):
        return {"action": "set_brightness", "value": 80}

    # ── Web Search ───────────────────────────────────────────
    for pattern in [r'search (?:for )?(.+?)(?:\s+on google)?$', r'google (.+)', r'look up (.+)']:
        m = re.search(pattern, text)
        if m:
            return {"action": "search_web", "query": m.group(1).strip()}

    # ── Open App ─────────────────────────────────────────────
    for pattern in [r'(?:open|launch|start|run)\s+(.+?)(?:\s+and\s+search\s+(.+))?$']:
        m = re.search(pattern, text)
        if m:
            target = m.group(1).strip()
            search_query = m.group(2).strip() if m.group(2) else None

            # Check if it's a known app
            known_apps = list(app_tools.APP_MAP.keys())
            from difflib import get_close_matches
            app_match = get_close_matches(target, known_apps, n=1, cutoff=0.5)

            if app_match:
                if search_query:
                    return {"action": "open_app_search", "target": app_match[0], "query": search_query}
                return {"action": "open_app", "target": app_match[0]}

            # Check if it's a folder
            known_folders = list(app_tools.FOLDER_MAP.keys())
            folder_match = get_close_matches(target, known_folders, n=1, cutoff=0.5)
            if folder_match:
                return {"action": "open_folder", "target": folder_match[0]}

            # Check for folder keyword
            if 'folder' in target:
                folder_name = target.replace('folder', '').strip()
                return {"action": "open_folder", "target": folder_name}

            # Check for file keyword
            if any(w in target for w in ['file', 'document']):
                file_name = re.sub(r'\b(file|document|called|named)\b', '', target).strip()
                return {"action": "open_file", "target": file_name}

            # Default: try as app, then file
            return {"action": "open_app", "target": target}

    # ── Find / Open File ─────────────────────────────────────
    m = re.search(r'(?:find|locate|where is)\s+(.+)', text)
    if m:
        return {"action": "open_file", "target": m.group(1).strip()}

    # No deterministic match — let LLM handle it
    return None


# ═══════════════════════════════════════════════════════════════
#  Action Executor
# ═══════════════════════════════════════════════════════════════

def execute_action(intent, memory, session_id):
    """Execute a parsed intent and speak the result."""
    action = intent["action"]

    if action == "set_volume":
        val = intent["value"]
        if sys_tools.set_volume(val):
            tts.speak(f"Volume set to {val} percent.")
        else:
            tts.speak("Couldn't change the volume.")

    elif action == "get_volume":
        vol = sys_tools.get_volume()
        if vol is not None:
            tts.speak(f"Volume is at {vol} percent.")
        else:
            tts.speak("Couldn't read the volume level.")

    elif action == "volume_change":
        success, new_vol = sys_tools.change_volume(intent.get("direction", "up"))
        if success and new_vol is not None:
            tts.speak(f"Volume now at {new_vol} percent.")
        else:
            tts.speak("Couldn't adjust the volume.")

    elif action == "mute":
        sys_tools.set_volume(0)
        tts.speak("Muted.")

    elif action == "system_info":
        info = sys_tools.get_system_info()
        tts.speak(sys_tools.format_system_info(info))

    elif action == "screenshot":
        path = sys_tools.take_screenshot()
        if path:
            tts.speak(f"Screenshot saved to {os.path.basename(path)}.")
        else:
            tts.speak("Screenshot failed.")

    elif action == "describe_screen":
        tts.speak("Analyzing the screen...")
        prompt = intent.get("prompt", None)
        description = vision.describe_screen(prompt)
        tts.speak(description)

    elif action == "shutdown":
        delay = intent.get("delay", 10)
        tts.speak(f"Shutting down in {delay} seconds. Run shutdown /a to cancel.")
        sys_tools.shutdown(delay)

    elif action == "restart":
        tts.speak("Restarting in 10 seconds. Run shutdown /a to cancel.")
        sys_tools.restart()

    elif action == "sleep":
        tts.speak("Putting the system to sleep.")
        sys_tools.sleep_system()

    elif action == "set_brightness":
        val = intent["value"]
        if sys_tools.set_brightness(val):
            tts.speak(f"Brightness set to {val} percent.")
        else:
            tts.speak("Couldn't adjust brightness.")

    elif action == "search_web":
        query = intent["query"]
        result = web_tools.search_google(query)
        tts.speak(result)

    elif action == "open_app":
        target = intent["target"]
        path = app_tools.find_application(target)
        if path:
            app_tools.open_path(path)
            tts.speak(f"Opening {target}.")
        else:
            tts.speak(f"Couldn't find {target}.")

    elif action == "open_app_search":
        target = intent["target"]
        query = intent["query"]
        browsers = ["chrome", "brave", "firefox", "edge"]
        if target in browsers:
            web_tools.search_google(query)
            tts.speak(f"Searching for {query}.")
        else:
            path = app_tools.find_application(target)
            if path:
                app_tools.open_path(path)
                tts.speak(f"Opening {target}.")

    elif action == "open_folder":
        target = intent["target"]
        path = app_tools.find_folder(target)
        if path and os.path.exists(path):
            app_tools.open_path(path)
            tts.speak(f"Opening {target} folder.")
        else:
            tts.speak(f"Couldn't find {target} folder.")

    elif action == "open_file":
        target = intent["target"]
        tts.speak(f"Searching for {target}...")
        result = app_tools.open_file(target)
        tts.speak(result)

    # Log the command
    if MEMORY_LOG_COMMANDS:
        memory.log_command(
            command=str(intent),
            action=action,
            target=intent.get("target", intent.get("query", "")),
        )


# ═══════════════════════════════════════════════════════════════
#  LLM Handler (for non-action queries)
# ═══════════════════════════════════════════════════════════════

def handle_with_llm(user_input, memory, session_id):
    """Send user input to the LLM with conversation context and stream the response."""
    # Get conversation history
    history = memory.get_recent_context(session_id, n_turns=5)

    # Add current user message
    history.append({"role": "user", "content": user_input})

    # Stream response with sentence-level TTS
    print(f"\n💭 {ASSISTANT_NAME}: ", end="", flush=True)

    full_response = llm.stream_chat(
        messages=history,
        on_sentence=lambda s: tts.speak_streaming(s, show_text=False),
    )

    # Print the full response (if streaming didn't already)
    if full_response:
        print(full_response)
    print()

    # Save to memory
    memory.add_message(session_id, "user", user_input)
    memory.add_message(session_id, "assistant", full_response)

    return full_response


# ═══════════════════════════════════════════════════════════════
#  Main Pipeline: Audio → STT → Intent/LLM → TTS
# ═══════════════════════════════════════════════════════════════

def process_audio(audio_data, memory, session_id):
    """Main pipeline: transcribe audio, parse intent, execute or query LLM."""
    # Step 1: Transcribe
    print("🧠 Processing speech...")
    text = stt.transcribe(audio_data, use_command_model=True)

    if not text or len(text.strip()) < 2:
        tts.speak("Didn't catch that. Try again.")
        return

    print(f"📝 You said: \"{text}\"")

    # Check for goodbye
    if any(w in text.lower() for w in ['goodbye', 'bye', 'go to sleep', 'shut up']):
        tts.speak("Goodbye. I'll be here when you need me.")
        return

    # Step 2: Parse intent (deterministic actions)
    intent = parse_intent(text)

    if intent:
        logger.info(f"Action: {intent['action']} | {intent}")
        execute_action(intent, memory, session_id)
    else:
        # Step 3: No action match — use LLM
        handle_with_llm(text, memory, session_id)


# ═══════════════════════════════════════════════════════════════
#  Startup
# ═══════════════════════════════════════════════════════════════

def print_banner():
    """Print the startup banner."""
    print()
    print("═" * 60)
    print(f"  🤖 {ASSISTANT_NAME} — Voice Assistant")
    print( "  Inspired by Tony Stark's F.R.I.D.A.Y.")
    print( "  Offline • Private • Intelligent")
    print("═" * 60)
    print()


def main():
    """Entry point for Maya Voice Assistant."""
    print_banner()

    # ── Initialize all subsystems ────────────────────────────
    print("⏳ Initializing subsystems...\n")

    # STT
    stt.load_models()

    # TTS
    tts.init()

    # Apps & folders
    app_tools.init()

    # Memory
    memory = Memory()
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    memory.start_session(session_id)
    stats = memory.get_stats()
    if stats.get("total_commands", 0) > 0:
        print(f"📊 Memory: {stats['total_commands']} commands, {stats['total_sessions']} sessions stored\n")

    # LLM check
    print("🧠 Checking Ollama LLM...")
    if llm.is_ollama_available():
        from config import LLM_MODEL
        print(f"   └── ✅ Connected to Ollama ({LLM_MODEL})\n")
    else:
        print("   └── ⚠️  Ollama not reachable — LLM features limited")
        print("         Start Ollama with: ollama serve\n")

    # Vision check
    if VISION_ENABLED:
        if vision.is_available():
            from config import VISION_MODEL
            print(f"👁️  Vision: {VISION_MODEL} ready\n")
        else:
            print("👁️  Vision: not available (moondream model may not be pulled)\n")

    # ── Greeting ─────────────────────────────────────────────
    hour = datetime.now().hour
    if 5 <= hour < 12:
        greeting = "Good morning."
    elif 12 <= hour < 18:
        greeting = "Good afternoon."
    elif 18 <= hour < 22:
        greeting = "Good evening."
    else:
        greeting = "Hello."

    tts.speak(f"{greeting} {ASSISTANT_NAME} online. Press F12 when you need me.")

    # ── Push-to-Talk loop ────────────────────────────────────
    ptt = PushToTalk(
        on_audio_ready=lambda audio: process_audio(audio, memory, session_id)
    )

    try:
        ptt.start_listening()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n🔚 Shutting down...")
        memory.end_session(session_id)
        memory.close()
        tts.cleanup()
        print(f"   {ASSISTANT_NAME} offline. Goodbye.\n")


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
