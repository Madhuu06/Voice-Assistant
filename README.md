# E.V.A – Enhanced Voice Assistant 🚀

A powerful, entirely offline, highly capable voice assistant built for seamless control over your Windows computer. E.V.A combines local LLM reasoning, highly-accurate speech recognition, fast Edge TTS synthesis, and screen awareness for a true, hands-free Tony Stark-like experience.

## ✨ Key Features

### Local LLM Intelligence (Ollama + Qwen)
- **Extremely Minimalist Identity**: E.V.A defaults to short, concise action-oriented responses.
- **Contextual Memory**: Powered by SQLite (`eva_memory.db`) to naturally remember conversation history (up to 20 turns) across sessions.
- **High Speed**: Integrated model pre-warming ensures zero cold-start delay.

### Dual-Queue Pipelined TTS (Edge TTS)
- **Zero Audio Gaps**: The assistant leverages a custom dual-queue TTS thread pipeline. As soon as the LLM streams the first sentence, it immediately generates and plays the audio while simultaneously piping the *next* sentences in the background, eliminating network buffer pauses.
- **High-Quality Neural Voices**: Uses Microsoft's Edge TTS (`en-US-AriaNeural`) at a tailored `+15%` speaking rate for a natural and incredibly responsive feeling. 
- **Interruptible (F12)**: Need her to stop talking? Press F12 seamlessly midway through a sentence. She will halt playback, clear the audio queue, and immediately start listening again.

### Offline STT (OpenAI Whisper)
- Energy-based voice detection using `sounddevice` to auto-stop recording when you finish speaking.
- Operates totally offline using lightweight Whisper (`tiny`/`base`) models.

### Screen Awareness 👁️ (Moondream Vision)
- Includes the `moondream` model allowing E.V.A to "see" your screen and answer questions about what is currently on your display.

### Deep System Control
- Control Volume up/down or exact percentages.
- Tweak display brightness levels. 
- Fetch detailed system status (CPU, memory, storage, battery percentage).
- Automatically open popular Windows desktop applications and local folders via advanced executable discovery.
- Advanced capabilities: sleep, shutdown, fetch Google searches.

## 🛠️ Installation

### 1. Requirements
Ensure you have Python 3.13 installed. Additionally, you will need Ollama installed with the required models locally pulled.

### 2. Clone & Setup
```bash
git clone https://github.com/Madhuu06/Voice-Assistant.git
cd Voice-Assistant
pip install -r requirements.txt
```

### 3. Pull Required Local Models
E.V.A expects the following models to exist in your Ollama installation:
```bash
ollama serve
ollama pull qwen:7b
ollama pull moondream   # For Screen Awareness feature (Optional)
```

## 🎯 Usage

1. **Start the assistant**: 
   ```bash
   python assistant.py
   ```
2. **Push To Talk**: Press `F12` to speak. The assistant will record until you hit a sustained silence. 
3. **Interrupt**: Press `F12` again mid-speech to interrupt E.V.A, halt the LLM generation, and instantly restart listening.

### Command Examples
- **General Queries**: "What's the capital of France?"
- **System**: "Set volume to 50%", "Decrease brightness", "How much battery do I have?"
- **Vision**: "What am I looking at right now?", "Explain what is on my screen."
- **Apps**: "Open Chrome", "Launch VS Code", "Start Discord" 
- **Folders**: "Open my downloads folder"
- **Web**: "Search Google for Python tutorials"

## 🔧 Configuration

Everything is easily modularized via `config.yaml`:
- Edit **system prompt** properties and **personality settings** to control how verbose or concise E.V.A acts. 
- Edit **activation keys** mappings (default: `F12`).
- Check `logs/eva.log` for any comprehensive error debugging.

---

**E.V.A never sleeps. She listens, learns, and helps — so you can focus on what matters.** 🎯