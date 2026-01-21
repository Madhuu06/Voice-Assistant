import os
import winshell
from win32com.client import Dispatch
import sys
from pathlib import Path

def create_startup_shortcut():
    """Create a startup shortcut for the voice assistant"""
    try:
        # Get the script directory
        script_dir = Path(__file__).parent
        assistant_bat = script_dir / "start_assistant_silent.bat"
        
        # Get startup folder
        startup_folder = winshell.startup()
        
        # Create shortcut path
        shortcut_path = os.path.join(startup_folder, "Voice Assistant.lnk")
        
        # Create the shortcut
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = str(assistant_bat)
        shortcut.WorkingDirectory = str(script_dir)
        shortcut.IconLocation = str(assistant_bat)
        shortcut.Description = "Voice Assistant Auto-Start"
        shortcut.save()
        
        print(f"✅ Startup shortcut created: {shortcut_path}")
        print("Voice Assistant will now start automatically when Windows starts!")
        
    except Exception as e:
        print(f"❌ Error creating startup shortcut: {e}")
        print("You may need to manually add the shortcut to your startup folder.")
        print(f"Startup folder: {winshell.startup()}")
        print(f"Target file: {assistant_bat}")

def remove_startup_shortcut():
    """Remove the startup shortcut"""
    try:
        startup_folder = winshell.startup()
        shortcut_path = os.path.join(startup_folder, "Voice Assistant.lnk")
        
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            print("✅ Startup shortcut removed")
        else:
            print("❌ Startup shortcut not found")
            
    except Exception as e:
        print(f"❌ Error removing startup shortcut: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove_startup_shortcut()
    else:
        create_startup_shortcut()