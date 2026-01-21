"""
ElevenLabs Voice Integration for Friday Assistant
Provides ultra-realistic AI voices
"""

import os
import tempfile
import pygame
from elevenlabs import ElevenLabs, VoiceSettings
import json
from pathlib import Path

class ElevenLabsVoice:
    def __init__(self):
        self.api_key = None
        self.voice_id = None
        self.voice_name = "Aria (Default)"
        self.client = None
        self.load_config()
        
        # Initialize pygame for audio playback
        try:
            pygame.mixer.init()
        except:
            print("⚠️ Could not initialize audio playback")
        
    def load_config(self):
        """Load ElevenLabs configuration"""
        try:
            if os.path.exists("elevenlabs_config.json"):
                with open("elevenlabs_config.json", "r") as f:
                    config = json.load(f)
                    self.api_key = config.get("api_key")
                    self.voice_id = config.get("voice_id") 
                    self.voice_name = config.get("voice_name", "Aria")
                    
                if self.api_key:
                    self.client = ElevenLabs(api_key=self.api_key)
                    return True
        except Exception as e:
            print(f"Error loading ElevenLabs config: {e}")
        return False
    
    def save_config(self, api_key, voice_id, voice_name):
        """Save ElevenLabs configuration"""
        config = {
            "api_key": api_key,
            "voice_id": voice_id,
            "voice_name": voice_name
        }
        
        with open("elevenlabs_config.json", "w") as f:
            json.dump(config, f, indent=2)
            
        self.api_key = api_key
        self.voice_id = voice_id
        self.voice_name = voice_name
        self.client = ElevenLabs(api_key=api_key)
        
    def setup_api_key(self):
        """Interactive API key setup"""
        print("🎙️ ElevenLabs Voice Setup")
        print("=" * 40)
        print("1. Go to: https://elevenlabs.io")
        print("2. Sign up for FREE account")
        print("3. Go to Profile Settings → API Keys")
        print("4. Copy your API key")
        print("5. Paste it below")
        print()
        
        api_key = input("Enter your ElevenLabs API key: ").strip()
        
        if not api_key:
            print("❌ No API key provided")
            return False
            
        # Test the API key
        try:
            client = ElevenLabs(api_key=api_key)
            available_voices = client.voices.get_all()
            
            if available_voices.voices:
                print(f"✅ API key valid! Found {len(available_voices.voices)} voices")
                return self.select_voice(api_key, available_voices.voices)
            else:
                print("❌ No voices found. Check your API key.")
                return False
                
        except Exception as e:
            print(f"❌ API key test failed: {e}")
            return False
    
    def select_voice(self, api_key, available_voices):
        """Let user select a voice"""
        print("\\n🎙️ Available ElevenLabs Voices:")
        print("=" * 40)
        
        for i, voice in enumerate(available_voices[:10]):  # Show first 10
            print(f"{i+1}. {voice.name}")
            if hasattr(voice, 'category'):
                print(f"   Category: {voice.category}")
            print(f"   ID: {voice.voice_id}")
            print()
        
        while True:
            try:
                choice = input(f"\\nSelect voice (1-{min(len(available_voices), 10)}) or 'q' to quit: ").strip()
                
                if choice.lower() == 'q':
                    return False
                    
                voice_index = int(choice) - 1
                if 0 <= voice_index < min(len(available_voices), 10):
                    selected_voice = available_voices[voice_index]
                    
                    # Test the voice
                    print(f"\\n🔊 Testing voice: {selected_voice.name}")
                    success = self.test_voice(selected_voice.voice_id, "Hello! I'm Friday, your advanced AI assistant. How does this voice sound?")
                    
                    if success:
                        confirm = input("\\nUse this voice for Friday? (y/n): ").lower()
                        if confirm == 'y':
                            self.save_config(api_key, selected_voice.voice_id, selected_voice.name)
                            print(f"✅ Voice configured: {selected_voice.name}")
                            return True
                    else:
                        print("❌ Could not test voice")
                        
                else:
                    print("❌ Invalid selection")
                    
            except (ValueError, IndexError):
                print("❌ Please enter a valid number")
                
        return False
    
    def test_voice(self, voice_id, text):
        """Test a voice by generating and playing sample audio"""
        try:
            if not self.client:
                return False
                
            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice_id,
                optimize_streaming_latency="0",
                output_format="mp3_22050_32",
                text=text,
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.8,
                    style=0.0,
                    use_speaker_boost=True
                )
            )
            
            # Convert generator to bytes
            audio_bytes = b"".join(audio_generator)
            
            # Save to temporary file and play
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            # Play the audio
            try:
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()
                
                # Wait for playback to complete
                import time
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Audio playback error: {e}")
            
            # Clean up
            try:
                os.unlink(temp_path)
            except:
                pass
                
            return True
            
        except Exception as e:
            print(f"Voice test error: {e}")
            return False
    
    def speak(self, text):
        """Generate speech using ElevenLabs"""
        if not self.client or not self.api_key or not self.voice_id:
            return False
            
        try:
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                optimize_streaming_latency="0",
                output_format="mp3_22050_32",
                text=text,
                voice_settings=VoiceSettings(
                    stability=0.6,
                    similarity_boost=0.8,
                    style=0.0,
                    use_speaker_boost=True
                )
            )
            
            # Convert generator to bytes
            audio_bytes = b"".join(audio_generator)
            
            # Play the audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            try:
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()
                
                # Wait for playback to complete
                import time
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    
            finally:
                # Clean up
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
            return True
            
        except Exception as e:
            print(f"ElevenLabs speech error: {e}")
            return False
    
    def is_configured(self):
        """Check if ElevenLabs is properly configured"""
        return bool(self.api_key and self.voice_id and self.client)

# Global instance
elevenlabs_voice = ElevenLabsVoice()

def setup_elevenlabs():
    """Setup ElevenLabs voice"""
    return elevenlabs_voice.setup_api_key()

def speak_with_elevenlabs(text):
    """Speak using ElevenLabs voice"""
    return elevenlabs_voice.speak(text)

def is_elevenlabs_ready():
    """Check if ElevenLabs is configured and ready"""
    return elevenlabs_voice.is_configured()

if __name__ == "__main__":
    print("🎙️ ElevenLabs Voice Setup for Friday")
    print("=" * 40)
    
    if elevenlabs_voice.is_configured():
        print(f"✅ Already configured with voice: {elevenlabs_voice.voice_name}")
        test = input("\\nTest current voice? (y/n): ").lower()
        if test == 'y':
            elevenlabs_voice.speak("Hello! I'm Friday, your advanced AI assistant with ElevenLabs voice!")
    else:
        print("Setting up ElevenLabs for the first time...")
        success = elevenlabs_voice.setup_api_key()
        
        if success:
            print("\\n🎉 ElevenLabs setup complete!")
            print("Your Friday assistant will now use AI voice!")
        else:
            print("\\n⚠️ Setup cancelled or failed.")