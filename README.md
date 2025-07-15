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
<h3>📋 Prerequisites</h3>
<ul>
  <li>Python 3.8+</li>

<li>pip</li>

<li>API key for wake word (porcupine)</li>
</ul>

<h2>🧪 Usage</h2>
Once started, Friday will begin listening for the wake word (e.g., "Friday").
After activation, speak a command such as:
<ul>
<li>“Open Chrome”</li>

<li>“Launch Downloads folder”</li>

<li>“Find my resume PDF”</li>

<li>You can also predefine mappings or let Friday search dynamically.</li>
</ul>

<h2>🗣️ Wake Word & Commands</h2>
Default Wake Word: “Hey Friday”
You can customize the wake word using Porcupine's SDK or a hotword detector.

Example Commands:
<ul>
<li>Open applications: “Open Spotify”</li>

<li>Navigate folders: “Open Documents”, “Show me Pictures”</li>

<li>Launch files: “Open Budget.xlsx”, “Find project report”</li>
</ul>

<h2>🎨 Customization</h2>
<ul>
<li>Add your own wake word</li>

<li>Modify or add new command mappings</li>

<li>Switch TTS engine between pyttsx3, Google TTS, or ElevenLabs</li>

<li>Adjust sensitivity, hotword settings, or microphone input in config.py</li>
</ul>

<h2>Friday never sleeps. She listens, learns, and helps — so you can focus on what matters.</h2>

