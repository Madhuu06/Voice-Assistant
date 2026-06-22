# E.V.A – Enhanced Voice Assistant 

A fast, fully offline voice assistant that controls your Windows PC using natural language. Powered by a local LLM, Whisper STT, and Kokoro TTS — no cloud required.

##  What Makes Eva Different

| Feature | Eva | Cloud Assistants |
|--------|-----|-----------------|
| Offline |  100% local |  Needs internet |
| Private |  Nothing leaves your PC |  Data sent to servers |
| Tool Calling |  Dynamic LLM-driven dispatch |  Rigid voice commands |
| Interruptible |  Press F12 mid-sentence |  Have to wait |
| Extensible |  Add tools in one file |  Locked ecosystem |

---

##  Architecture

```
You (F12) → Whisper STT → qwen:7b LLM (with tools) → Tool Execution → Kokoro TTS → Speakers
                                       ↑
                          Tool Registry (auto-discovered)
```

### Key Design Decisions
- **Prompt-based tool dispatch** — Tools are described in the system prompt as JSON schemas. qwen:7b emits `{"tool": "...", "args": {...}}` JSON inline, which Eva intercepts and executes. No native tool-calling API required.
- **Dual-queue pipelined TTS** — Generator thread builds audio while player thread is still playing the previous sentence. Zero inter-sentence pauses.
- **Kokoro offline TTS** — 88MB int8 ONNX model, auto-downloaded on first launch. Falls back to Edge TTS (cloud) then pyttsx3.

---

##  Project Structure

```
Voice-Assistant/
├── assistant.py          # Main entry point — clean, no regex glue
├── config.py / config.yaml
├── core/
│   ├── llm.py            # Streaming LLM + tool dispatch loop
│   ├── tts.py            # Kokoro → Edge TTS → pyttsx3 pipeline
│   ├── stt.py            # Whisper STT (tiny + base)
│   ├── memory.py         # SQLite session memory
│   └── vision.py         # Moondream screen awareness
└── tools/
    ├── registry.py       # @registry.register decorator + auto-discovery
    ├── system.py         # Volume, brightness, system info, screenshots, power
    ├── web.py            # Google search, URL open
    ├── apps.py           # Open apps, folders, files
    └── desktop.py        # Spotify media control, window mgmt, clipboard, typing
```

---

##  Setup

### 1. Clone & Install
```bash
git clone https://github.com/Madhuu06/Voice-Assistant.git
cd Voice-Assistant
pip install -r requirements.txt
```

### 2. Pull Required Ollama Models
```bash
ollama serve
ollama pull qwen:7b
ollama pull moondream   # Optional — enables screen awareness
```

### 3. Run Eva
```bash
python assistant.py
```

> On first run, Eva auto-downloads the **Kokoro TTS int8 model** (~88MB). After that, TTS is 100% offline.

---

## Usage

- **Press `F12`** to start recording. Eva listens until silence.
- **Press `F12` again** mid-response to interrupt — stops LLM generation and TTS instantly.
- Speak naturally. The LLM figures out what tool to call.

### Example Commands
| What you say | What Eva does |
|---|---|
| "Open Chrome and search for Python docs" | Calls `open_app` + `search_web` |
| "Set volume to 60" | Calls `set_volume` |
| "What's on my screen?" | Calls `describe_screen` (moondream) |
| "Pause the music" | Calls `media_control(play_pause)` |
| "Copy 'hello world' to clipboard" | Calls `write_clipboard` |
| "Minimize Chrome" | Calls `window_control(minimize)` |
| "Type hello into the search bar" | Calls `type_text` |
| "How much RAM am I using?" | Calls `get_system_info` |

---

## 🔧 Adding New Tools

Create or edit any file in `tools/` and use the `@registry.register` decorator:

```python
from tools.registry import registry

@registry.register(
    name="my_tool",
    description="Does something useful.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Input text."}
        },
        "required": ["text"]
    }
)
def my_tool(text: str):
    return f"Did something with: {text}"
```

Then import the module in `assistant.py` (one line). That's it — Eva's LLM will automatically use it.

---

##  Configuration

All settings in `config.yaml`:
- **LLM model**: change `llm.model` (default: `qwen:7b`)
- **Voice**: change `tts.kokoro.voice` (default: `af_sarah`)
- **Speed**: change `tts.kokoro.speed` (default: `1.15` = +15%)
- **System prompt**: tune Eva's personality under `llm.system_prompt`
- **Logs**: `logs/eva.log`
- **Memory**: `eva_memory.db` (SQLite)

---

**Eva never sleeps. She listens, thinks, and acts — so you don't have to.** 🎯
