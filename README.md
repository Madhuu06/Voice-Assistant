<h1>Friday – Your PC’s Voice Assistant</h1>
A powerful, always-listening assistant built for hands-free control over your computer. Open apps, folders, and files just by speaking. Whether you're working, studying, or relaxing, Friday is just a wake word away.

<h2>🚀 Table of Contents</h2>
<ul>
<li>Introduction</li>

<li>Features</li>

<li>Tech Stack</li>

<li>Installation</li>

<li>Usage</li>

<li>Wake Word & Commands</li>

<li>Customization</li>

<li>Contributing</li>
</ul>

<h2>📖 Introduction</h2>
Welcome to Friday, your personal desktop voice assistant inspired by sci-fi AI. Built with Python and designed for flexibility, Friday lets you interact with your PC naturally using voice commands. Whether it’s opening software, searching files, or accessing folders buried deep in your system, Friday is always there in the background — ready to help.

<h2>🌟 Features</h2>
<ul>
<li>🔊 Voice-Activated Commands – Open any app, file, or folder hands-free</li>

<li>🧠 Smart Path Detection – Can search and locate items dynamically if not pre-mapped</li>

<li>👂 Always Listening – Runs in the background and responds instantly to your wake word</li>

<li>💬 Natural Speech Recognition – No rigid syntax; understands intent</li>
</ul>

<h2>💻 Tech Stack</h2>
<ul>
<li>Core Language: Python 3</li>

<li>Speech Recognition: speech_recognition, pyaudio</li>

<li>Text-to-Speech: pyttsx3 (offline)</li>

<li>Wake Word Detection: porcupine or custom-trained wake word</li>

<li>Packaging: PyInstaller for executable bundling</li>

<li>File Access: os, subprocess, glob, and fuzzywuzzy for smart matching</li>
</ul>

<h2>🛠 Installation</h2>
📋 Prerequisites
Python 3.8+

pip

API key for wake word (porcupine)

📥 Steps
Clone the repository:

bash
Copy
Edit
git clone https://github.com/your-username/friday-voice-assistant
cd friday-voice-assistant
Install dependencies:

bash
Copy
Edit
pip install -r requirements.txt
(Optional) Add your TTS API key in a .env file:

env
Copy
Edit
ELEVENLABS_API_KEY=your_key_here
Run the assistant:

bash
Copy
Edit
python assistant.py
🧪 Usage
Once started, Friday will begin listening for the wake word (e.g., "Hey Friday").
After activation, speak a command such as:

“Open Chrome”

“Launch Downloads folder”

“Find my resume PDF”

You can also predefine mappings or let Friday search dynamically.

🗣️ Wake Word & Commands
Default Wake Word: “Hey Friday”
You can customize the wake word using Porcupine's SDK or a hotword detector.

Example Commands:

Open applications: “Open Spotify”

Navigate folders: “Open Documents”, “Show me Pictures”

Launch files: “Open Budget.xlsx”, “Find project report”

🎨 Customization
Add your own avatar image in the assets/ folder

Modify or add new command mappings in commands.json

Switch TTS engine between pyttsx3, Google TTS, or ElevenLabs

Adjust sensitivity, hotword settings, or microphone input in config.py

🤝 Contributing
Contributions are welcome! Here's how to get started:

Fork the repo

Create a new branch:

bash
Copy
Edit
git checkout -b feature/MyFeature
Commit your changes:

bash
Copy
Edit
git commit -m "Add MyFeature"
Push to your branch:

bash
Copy
Edit
git push origin feature/MyFeature
Open a Pull Request
