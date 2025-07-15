import os
import time
import threading
import pvporcupine
import sounddevice as sd
import speech_recognition as sr
import pyttsx3
from difflib import get_close_matches
import sys
import numpy
import pyaudio
from datetime import datetime
import time

from config import *
from logger import setup_logging

logger = setup_logging()

SEARCH_ROOT = os.path.expanduser("~")

APP_MAP = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "whatsapp": r"C:\Users\madhu\AppData\Local\WhatsApp\WhatsApp.exe",
    "notepad": "notepad.exe",
    "vscode": r"C:\Users\madhu\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "valorant": r"C:\Users\Public\Desktop\VALORANT.lnk",
    "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "discord": r"C:\Users\madhu\OneDrive\Desktop\Discord.lnk",
    "camera": "camera.exe",
    "forza": r"C:\Users\madhu\OneDrive\Desktop\Forza Horizon 4.lnk"
}

FOLDER_MAP = {
    "downloads": os.path.join(SEARCH_ROOT, "Downloads"),
    "screenshots": os.path.join(SEARCH_ROOT, "Screenshots"),
    "videos": os.path.join(SEARCH_ROOT, "Videos"),
    "documents": os.path.join(SEARCH_ROOT, "Documents"),
    "karthik": r"C:\Users\madhu\OneDrive\Desktop\Karthik",
    "wallpaper": r"C:\Users\madhu\OneDrive\Desktop\Karthik\WallPaper",
    "games": r"D:\Games"
}

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

wakeword_path = os.path.join(base_path, "wakewords", "hey_friday.ppn")

# Initialize text-to-speech engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')

# Set Microsoft Zira voice if available
selected_voice = None
for voice in voices:
    if "Zira" in voice.name:
        selected_voice = voice
        break

if selected_voice:
    engine.setProperty('voice', selected_voice.id)
    logger.info(f"Using voice: {selected_voice.name}")
else:
    logger.warning("Microsoft Zira voice not found, using default voice")

engine.setProperty('rate', 170)
engine.setProperty('volume', VOICE_VOLUME)

def cleanup():
    """Cleanup resources before exit"""
    try:
        engine.stop()
    except:
        pass

import atexit
atexit.register(cleanup)

def speak(text, show_text=True):
    if show_text:
        print(text)
    time.sleep(0.3)
    engine.say(text)
    engine.runAndWait()

def get_basic_response(prompt):
    prompt = prompt.lower()
    if "hello" in prompt or "hi" in prompt:
        return "How ya doing?"
    elif "what's your name" in prompt or "who are you" in prompt:
        return "Friday."
    elif "thank you" in prompt or "thanks" in prompt:
        return "Gotcha"
    elif "how are you" in prompt:
        return "Great but I could really go for a massage"
    elif "how r you" in prompt:
        return "Great but I could really go for a massage"
    elif "time" in prompt:
        return f"The current time is {datetime.now().strftime('%I:%M %p')}"
    elif "date" in prompt:
        return f"Today is {datetime.now().strftime('%B %d, %Y')}"
    elif "what can you do" in prompt or "help" in prompt:
        return "I can help you with: opening files, folders, and applications. Just ask me to open something!"
    else:
        return "I can only help with opening files, folders, and applications. For other questions, try being more specific."

def get_file_type(filename):
    common_extensions = {
        '.pdf': 'PDF',
        '.doc': 'Word document',
        '.docx': 'Word document',
        '.txt': 'text file',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.png': 'image',
        '.xlsx': 'Excel spreadsheet',
        '.xls': 'Excel spreadsheet',
        '.pptx': 'PowerPoint presentation',
        '.ppt': 'PowerPoint presentation',
        '.csv': 'CSV file',
        '.zip': 'ZIP archive',
        '.mp3': 'audio file',
        '.mp4': 'video file',
        '.py': 'Python file',
        '.js': 'JavaScript file',
        '.html': 'HTML file',
        '.css': 'CSS file'
    }
    ext = os.path.splitext(filename)[1].lower()
    return common_extensions.get(ext, 'file')

def search_files(query, search_type="file", extensions=None):
    matches = []
    for root, dirs, files in os.walk(SEARCH_ROOT):
        # Skip system directories and hidden folders
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue
        
        items = files if search_type == "file" else dirs
        for item in items:
            # Skip hidden files
            if item.startswith('.'):
                continue
                
            if extensions and not any(item.lower().endswith(ext) for ext in extensions):
                continue
            if query.lower() in item.lower():
                full_path = os.path.join(root, item)
                # Prioritize desktop and documents locations
                priority = 2 if "Desktop" in full_path else 1 if "Documents" in full_path else 0
                matches.append((full_path, priority))
    
    # Sort by priority (higher first) and then by path length (shorter paths first)
    matches.sort(key=lambda x: (-x[1], len(x[0])))
    return [m[0] for m in matches] 

def open_best_match(query, search_type="file", extensions=None):
    try:
        results = search_files(query, search_type=search_type, extensions=extensions)
        if results:
            best = get_close_matches(query, [os.path.basename(r) for r in results], n=1, cutoff=0.6)
            if best:
                for r in results:
                    if best[0] in r:
                        try:
                            file_type = get_file_type(r)
                            location = "Desktop" if "Desktop" in r else "Documents" if "Documents" in r else "computer"
                            os.startfile(r)
                            return f"Opening {best[0]}, a {file_type} from your {location}"
                        except Exception as e:
                            print(f"Error opening {best[0]}: {e}")
                            return f"Sorry, I couldn't open {best[0]}"
            else:
                try:
                    filename = os.path.basename(results[0])
                    file_type = get_file_type(results[0])
                    location = "Desktop" if "Desktop" in results[0] else "Documents" if "Documents" in results[0] else "computer"
                    os.startfile(results[0])
                    return f"Opening {filename}, a {file_type} from your {location}"
                except Exception as e:
                    print(f"Error opening {os.path.basename(results[0])}: {e}")
                    return f"Sorry, I couldn't open {os.path.basename(results[0])}"
        return "Couldn't find a match for that file."
    except Exception as e:
        print(f"Error in open_best_match: {e}")
        return "Sorry, something went wrong while searching."

def handle_command(first_command=True):
    """Handle a single command and return True if the conversation should end"""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        # Shorter noise adjustment for faster response
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        recognizer.energy_threshold = 4000 
        recognizer.dynamic_energy_threshold = True
        
        try:
            print("Listening for your command... (Speak now)")
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
            print("Processing your speech...")
            command = recognizer.recognize_google(audio).lower()
            print(f"You said: {command}")
            
            # Check if user wants to end conversation
            if "thank you" in command or "thank" in command:
                speak("Goodbye!")
                return True

            if any(phrase in command for phrase in ["open file", "find file", "search file", "look for file"]):
                # If only the trigger phrase is detected, listen for the filename
                if command.strip() in ["open file", "find file", "search file", "look for file"]:
                    speak("What file would you like me to open?")
                    try:
                        print("Listening for filename... (Speak now)")
                        audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                        print("Processing filename...")
                        filename = recognizer.recognize_google(audio).lower()
                        print(f"Filename: {filename}")
                        command = f"{command} {filename}"  # Combine the command with the filename
                    except sr.UnknownValueError:
                        speak("Sorry, I didn't catch the filename.")
                        return
                    except Exception as e:
                        speak("An error occurred while getting the filename.")
                        print(e)
                        return
                
                # File type keywords and their extensions
                file_types = {
                    'pdf': {'extensions': ['.pdf'], 'keywords': ['pdf', 'pdf file', 'pdf document']},
                    'word': {'extensions': ['.doc', '.docx'], 'keywords': ['word', 'word file', 'word document', 'doc', 'docx']},
                    'excel': {'extensions': ['.xlsx', '.xls'], 'keywords': ['excel', 'excel file', 'spreadsheet', 'xlsx', 'xls']},
                    'powerpoint': {'extensions': ['.ppt', '.pptx'], 'keywords': ['powerpoint', 'presentation', 'ppt', 'pptx']},
                    'text': {'extensions': ['.txt'], 'keywords': ['text', 'text file', 'txt']},
                    'image': {'extensions': ['.jpg', '.jpeg', '.png'], 'keywords': ['image', 'picture', 'photo', 'jpg', 'jpeg', 'png']},
                    'video': {'extensions': ['.mp4', '.avi', '.mkv'], 'keywords': ['video', 'movie', 'mp4', 'avi']},
                    'audio': {'extensions': ['.mp3', '.wav'], 'keywords': ['audio', 'music', 'song', 'mp3', 'wav']},
                    'document': {'extensions': ['.pdf', '.doc', '.docx', '.txt'], 'keywords': ['document']}
                }
                
                # Clean up the command
                for phrase in ["open file", "find file", "search file", "look for file"]:
                    command = command.replace(phrase, "").strip()
                query = command

                # Try to identify file type
                extensions = None
                for file_type, info in file_types.items():
                    if any(keyword in command.lower() for keyword in info['keywords']):
                        extensions = info['extensions']
                        # Remove the file type keyword from the query
                        for keyword in info['keywords']:
                            query = query.replace(keyword, "").strip()
                        break
                
                # Remove common words that might interfere with the search
                query = query.replace("called", "").replace("named", "").strip()
                
                if not query:
                    speak("What's the name of the file you're looking for?")
                    return

                speak(f"Searching for{' ' + file_type if extensions else ''} file with name '{query}'...")
                response = open_best_match(query, search_type="file", extensions=extensions)
                speak(response)

            elif "open folder" in command:
                query = command.replace("open folder", "").strip()
                best = get_close_matches(query, FOLDER_MAP.keys(), n=1, cutoff=0.6)
                if best:
                    os.startfile(FOLDER_MAP[best[0]])
                    speak(f"Opening {best[0]} folder")
                else:
                    speak("Searching for the folder...")
                    response = open_best_match(query, search_type="folder")
                    speak(response)

            elif "open" in command:
                app = command.replace("open", "").strip()
                best_match = get_close_matches(app, APP_MAP.keys(), n=1, cutoff=0.6)
                if best_match:
                    os.startfile(APP_MAP[best_match[0]])
                    speak(f"Opening {best_match[0]}")
                else:
                    try:
                        os.system(f"start {app}")
                        speak(f"Opening {app}")
                    except:
                        speak("Couldn't open that application.")

            else:
                response = get_basic_response(command)
                speak(response, show_text=False)
        except sr.UnknownValueError:
            speak("Sorry, I didn't catch that.")
        except Exception as e:
            speak("An error occurred.")
            print(e)

def start_assistant():
    wake_detected = threading.Event()
    porcupine = None
    stream = None

    print("Voice Assistant is starting...")
    print("Say 'Friday' to activate")
    
    try:
        # Optional: Play a startup sound
        speak("Voice Assistant is ready")
        
        porcupine = pvporcupine.create(
            access_key=PORCUPINE_KEY,
            keyword_paths=[wakeword_path],
            sensitivities=[WAKE_WORD_SENSITIVITY]
        )

        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f'Audio callback status: {status}')
            pcm = indata[:, 0].flatten().tolist()
            try:
                result = porcupine.process(pcm)
                if result >= 0:
                    print("Wake word detected!")
                    wake_detected.set()
            except Exception as e:
                print(f"Error processing audio: {e}")

        def listen_for_wake():
            nonlocal stream
            try:
                with sd.InputStream(
                    samplerate=porcupine.sample_rate,
                    blocksize=porcupine.frame_length,
                    dtype='int16',
                    channels=1,
                    callback=audio_callback
                ) as stream:
                    print("Say 'Friday' to activate.")
                    while not wake_detected.is_set():
                        time.sleep(0.1)
            except Exception as e:
                print(f"Error in audio stream: {e}")
                raise

        def continuous_conversation():
            """Handle multiple commands until user says thank you"""
            speak("Yes") 
            while True:
                try:
                    command_result = handle_command(first_command=False)  # Pass flag to indicate it's not the first command
                    # If handle_command returns True, it means user said thank you/thanks
                    if command_result:
                        print("Conversation ended. Say 'Hey Friday' to start again.")
                        return
                except Exception as e:
                    print(f"Error in conversation: {e}")
                    return

        while True:
            try:
                wake_detected.clear()   
                listen_for_wake()
                continuous_conversation()
            except KeyboardInterrupt:
                print("\nStopping assistant...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)  # Prevent rapid error loops

    except Exception as e:
        print(f"Error initializing assistant: {e}")
    finally:
        if porcupine is not None:
            porcupine.delete()
        if stream is not None and hasattr(stream, 'close'):
            stream.close()

if __name__ == "__main__":
    try:
        print("\nStarting Voice Assistant...")
        print("Press Ctrl+C to exit")
        start_assistant()
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
    except Exception as e:
        print(f"Fatal error: {e}")
        # Keep the window open if there's an error
        input("Press Enter to exit...")
    finally:
        cleanup()
