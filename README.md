# Friday – Your PC's Voice Assistant 🚀

A powerful, always-listening assistant built for hands-free control over your computer. Enhanced with OpenAI Whisper for superior speech recognition and natural language understanding.

## ✨ Key Features

### OpenAI Whisper Integration
- **Superior Accuracy**: Much better than traditional speech recognition
- **Accent Support**: Handles various accents and speech patterns  
- **Offline Operation**: Works completely offline after initial setup
- **Wake Word Detection**: Smart wake word recognition with multiple options

### Natural Language Commands
Instead of rigid commands, use natural language:

**Examples:**
- "Could you open Chrome for me?"
- "Please launch my downloads folder"
- "Find my document called report"
- "Can you start Discord?"

### Smart Wake Word Detection
- **Multiple Wake Words**: "Maya", "Alexa", or variations like "Mia", "Alex"
- **Mishearing Tolerance**: Works even if speech recognition mishears the wake word
- **Sensitive Detection**: Triggers reliably on various pronunciations

## 🛠️ Installation

### 1. Clone & Install
```bash
git clone https://github.com/Madhuu06/Voice-Assistant.git
cd Voice-Assistant
pip install -r requirements.txt
```

### 2. Run the Assistant
```bash
python assistant.py
```

**Note**: First run downloads Whisper model (~140MB). This only happens once.

## 🎯 Usage

1. **Start the assistant**: Run `python assistant.py`
2. **Activate with wake word**: Say "Maya", "Alexa", or "Alex"
3. **Give commands**: Speak naturally after you hear "I'm listening..."

### Command Examples
- **Apps**: "Open Chrome", "Launch VS Code", "Start Discord" 
- **Folders**: "Open downloads", "Show me documents"
- **Files**: "Find my resume", "Open that PDF report"
- **Web**: "Search for Python tutorials"

## 🔧 Configuration

### Whisper Model Options (config.py)
- `tiny`: Fastest (~40MB)
- `base`: Balanced (default, ~140MB) 
- `small`: Better accuracy (~460MB)

### Wake Word Options
- Primary: "Maya", "Alexa", "Alex"
- Alternatives: "Mia", "May", "Lexa" (automatically detected)

## 🚀 Startup Options

### Manual Start
```bash
python assistant.py
```

### Auto-Start with Windows
```bash
python create_startup_shortcut.py
```

This creates a Windows startup shortcut for automatic launching.

## 🔍 Troubleshooting

### Wake Word Not Detected
- Speak clearly and directly into microphone
- Try alternative wake words: "Alex", "Mia", "Maya"
- Check microphone permissions and levels

### Performance Issues
- Use `tiny` model for faster response
- Ensure microphone quality is good
- Check for background noise interference

### Dependencies
- **Missing modules**: Run `pip install -r requirements.txt`
- **Audio issues**: Verify microphone permissions
- **Model loading**: Wait for initial Whisper model download

## 📝 Technical Details

- **Speech Engine**: OpenAI Whisper (offline)
- **Wake Word**: Multi-pattern detection with mishearing tolerance
- **Voice Output**: pyttsx3 + ElevenLabs support
- **Platform**: Windows (primary), cross-platform compatible

## 🎉 Recent Improvements

- ✅ Enhanced wake word detection with multiple options
- ✅ Improved speech recognition mishearing tolerance  
- ✅ Better startup scripts and auto-launch support
- ✅ Reduced false negatives for wake word detection
- ✅ Added comprehensive debugging and testing tools

---

**Friday never sleeps. She listens, learns, and helps — so you can focus on what matters.** 🎯