# Voice Assistant Setup Guide

##  Setup Complete!

Your advanced voice assistant with dual Whisper models and local intent parsing is now fully operational!

##  Features
- **Natural Language Understanding**: Supports conversational commands like "could you open notepad" instead of rigid "open app notepad"
- **Dual Whisper Models**: 
  - Tiny model (~40MB) for fast wake word detection
  - Base model (~140MB) for accurate command recognition
- **Offline Operation**: No internet required for speech recognition or intent parsing
- **Better Accent Support**: Whisper models understand various accents and speech patterns
- **Wake Word Support**: Say "Friday" or "Hey Friday" to activate

##  How to Run

1. **Start the Assistant**:
   ```cmd
   python assistant.py
   ```

2. **Wait for Models to Load**:
   - You'll see "Loading Whisper models..." 
   - This takes 30-60 seconds the first time
   - Once you see "Voice Assistant is ready", you can start talking

3. **Use Voice Commands**:
   - Say "Friday" or "Hey Friday" to activate
   - Then speak your command naturally, e.g.:
     - "Could you open notepad?"
     - "Please open the documents folder"
     - "Search google for python tutorials"
     - "Open chrome and search for weather"

##  Project Structure

```
Voice assistant/
├── assistant.py          # Main voice assistant code
├── config.py            # Configuration settings
├── logger.py            # Logging setup
├── requirements.txt     # Python dependencies
├── start_assistant.bat  # Windows startup script
├── SETUP_GUIDE.md      # This guide
├── test_setup.py       # Test script for validation
├── wakewords/
│   └── hey_friday.ppn  # Original Porcupine wake word (not used)
├── logs/               # Application logs
└── __pycache__/        # Python cache files
```

## 🔧 Supported Commands

### File & Folder Operations
- "open notepad" / "could you open notepad"
- "open documents folder" / "please open the documents folder"
- "open chrome" / "launch chrome browser"

### Web Search
- "search google for [query]" / "google search [query]"
- "search youtube for [query]"

### App with Search
- "open chrome and search for [query]"
- "open youtube and search for [query]"

##  Expected Behavior

- **Audio Overflow Warnings**: You may see "Audio callback status: input overflow" messages. This is normal and doesn't affect functionality.
- **FP16 Warning**: "FP16 is not supported on CPU; using FP32 instead" is normal for CPU-based Whisper inference.
- **Model Loading**: First startup takes longer as Whisper downloads and caches models.

##  Dependencies Installed

- `openai-whisper` - Speech recognition models
- `sounddevice` - Audio input/output
- `pyttsx3` - Text-to-speech
- `numpy` - Numerical operations
- `torch` - Machine learning framework

##  Configuration

Main settings in `config.py`:
- `WHISPER_WAKE_MODEL = "tiny"` - Fast wake word detection
- `WHISPER_COMMAND_MODEL = "base"` - Accurate command recognition
- `SAMPLE_RATE = 16000` - Audio sampling rate
- `CHUNK_DURATION = 3.0` - Audio processing chunks

##  Troubleshooting

1. **Import Errors**: Make sure all dependencies are installed:
   ```cmd
   pip install openai-whisper sounddevice pyttsx3 numpy torch
   ```

2. **No Audio Input**: Check your microphone permissions and ensure a microphone is connected.

3. **Slow Response**: This is normal - Whisper models require processing time for accurate transcription.

4. **Wake Word Not Detected**: Speak clearly and ensure "Friday" or "Hey Friday" is pronounced distinctly.

##  Success Indicators

When working properly, you'll see:
-  "Loading Whisper models..." followed by "Whisper models loaded successfully!"
-  "Voice Assistant is ready"
-  "Say 'Friday' or 'Hey Friday' to activate"
-  Audio overflow warnings (these are normal)

Your voice assistant is now ready to use! Enjoy natural conversations with your AI assistant!
