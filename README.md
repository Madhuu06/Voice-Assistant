# Friday Voice Assistant with Whisper AI 🚀

Enhanced voice assistant with superior speech recognition powered by OpenAI Whisper.

## ✨ Key Features

### OpenAI Whisper Integration
- **Superior Accuracy**: Much better than traditional speech recognition
- **Accent Support**: Handles various accents and speech patterns
- **Offline Operation**: Works completely offline after initial setup
- **Multilingual**: Supports multiple languages (configured for English)

### Natural Language Commands
Instead of rigid commands like "open folder downloads", you can now use natural language:

**Before (Rigid):**
- "open file report.pdf"
- "open folder downloads"
- "open chrome"

**Now (Natural):**
- "Could you open my report document?"
- "Please open downloads folder"
- "Can you launch Chrome for me?"
- "Find my presentation called quarterly review"
- "I need to access my videos folder"

### Smart Intent Recognition
The assistant now understands:
- **Polite requests**: "Could you...", "Please...", "Can you..."
- **Context clues**: "my document", "that folder", "the file"
- **File types**: Automatically detects if you want PDF, Word, Excel, etc.
- **Natural variations**: Multiple ways to say the same thing

## 🛠️ Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note**: First run will download the Whisper model (~140MB for base model). This only happens once.

### 2. Run the Assistant
```bash
python assistant.py
```

### Model Options
You can change the Whisper model in `config.py`:
- `tiny`: Fastest, least accurate (~40MB)
- `base`: Good balance (default, ~140MB)
- `small`: Better accuracy (~460MB)
- `medium`: High accuracy (~1.4GB)
- `large`: Best accuracy (~2.9GB)

## 🎯 Usage Examples

### Opening Applications
- "Could you open Chrome?"
- "Please launch VS Code"
- "Can you start Discord?"
- "I need WhatsApp"

### Opening Folders
- "Please open my downloads folder"
- "Could you show me the documents directory?"
- "I need to access my games folder"
- "Open the wallpaper folder"

### Finding Files
- "Find my document called report"
- "Could you open that PDF about quarterly results?"
- "Look for my presentation on machine learning"
- "I need the Excel file with sales data"

### General Conversation
- "Hello" / "Hi"
- "How are you?"
- "What's the time?"
- "What's today's date?"
- "What can you do?"
- "Thank you" (ends conversation)

## 🔧 Technical Details

### Whisper-Powered Speech Recognition
- Uses OpenAI Whisper model for both wake word detection and command recognition
- Continuous listening with 3-second audio chunks
- Real-time transcription and intent parsing
- Handles accents, background noise, and speech variations

### Local Intent Parsing
- Pattern-based command classification
- No external API dependencies
- Supports fuzzy matching for app/folder names
- Confidence scoring for better accuracy

### Supported Intents
- `open_app`: Launch applications
- `open_folder`: Open directories
- `open_file`: Find and open files
- `open_app_and_search`: Open browser with search
- `search_web`: Google search
- `unknown`: General conversation

### Wake Words
- "Friday"
- "Hey Friday"
- "Friday please"

## 🚨 Troubleshooting

### First Run Issues
1. **Model Download**: First run downloads Whisper model (~140MB)
2. **CUDA Support**: For GPU acceleration, install `torch` with CUDA support
3. **Audio Issues**: Ensure microphone permissions are granted

### Performance Tips
- Use `tiny` model for faster response (less accurate)
- Use `base` model for good balance (recommended)
- Use larger models for better accuracy (slower)

### Common Issues
- **"No module named whisper"**: Run `pip install openai-whisper`
- **Audio not detected**: Check microphone settings and permissions
- **Slow processing**: Consider using a smaller Whisper model

## 📝 Configuration

Key settings in `config.py`:
```python
WHISPER_MODEL = "base"          # Whisper model size
VOICE_RATE = 170                # Speech speed
VOICE_VOLUME = 1.0              # Speech volume
```

## 🎉 Benefits

1. **Superior Accuracy**: Whisper handles accents and variations much better
2. **Completely Offline**: No API keys or internet required after setup
3. **Natural Language**: Speak normally instead of memorizing commands
4. **Flexible**: Multiple ways to ask for the same thing
5. **Fast**: Local processing with no network delays
6. **Reliable**: No external API dependencies

## 🔮 Future Enhancements

- Multi-step task execution
- Calendar and email integration
- Web search capabilities
- Smart home device control
- Learning from user patterns

---

**Enjoy your enhanced Friday assistant! 🎯**