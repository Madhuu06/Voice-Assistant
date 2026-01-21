#!/usr/bin/env python3
"""
Voice Assistant Auto-Start Verification Tool
"""
import os
import sys
import subprocess
from pathlib import Path

def check_autostart_status():
    """Check if the voice assistant is properly configured for auto-start"""
    print("=== VOICE ASSISTANT AUTO-START STATUS ===\n")
    
    # Check 1: Startup folder
    startup_folder = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
    startup_link = startup_folder / "Voice Assistant.lnk"
    
    print(f"1. Startup Folder: {startup_folder}")
    print(f"   Voice Assistant Link: {'✅ EXISTS' if startup_link.exists() else '❌ MISSING'}")
    
    # Check 2: Batch files
    project_dir = Path(__file__).parent
    silent_bat = project_dir / "start_assistant_silent.bat"
    regular_bat = project_dir / "start_assistant.bat"
    
    print(f"\n2. Startup Scripts:")
    print(f"   Silent starter: {'✅ EXISTS' if silent_bat.exists() else '❌ MISSING'}")
    print(f"   Regular starter: {'✅ EXISTS' if regular_bat.exists() else '❌ MISSING'}")
    
    # Check 3: Assistant file
    assistant_py = project_dir / "assistant.py"
    print(f"\n3. Assistant File:")
    print(f"   assistant.py: {'✅ EXISTS' if assistant_py.exists() else '❌ MISSING'}")
    
    # Check 4: Dependencies
    try:
        import whisper
        import sounddevice as sd
        from elevenlabs import Voice
        deps_ok = True
    except ImportError as e:
        deps_ok = False
        missing_dep = str(e)
    
    print(f"\n4. Dependencies:")
    print(f"   Core modules: {'✅ LOADED' if deps_ok else f'❌ MISSING: {missing_dep}'}")
    
    # Check 5: Virtual environment
    venv_path = project_dir / ".venv"
    venv_python = venv_path / "Scripts/python.exe"
    
    print(f"\n5. Virtual Environment:")
    print(f"   .venv folder: {'✅ EXISTS' if venv_path.exists() else '❌ MISSING'}")
    print(f"   Python in venv: {'✅ EXISTS' if venv_python.exists() else '❌ MISSING'}")
    
    # Final verdict
    print(f"\n{'='*50}")
    if startup_link.exists() and assistant_py.exists() and deps_ok:
        print("🎯 AUTO-START STATUS: ✅ FULLY CONFIGURED")
        print("\n📋 WHAT HAPPENS WHEN YOU RESTART:")
        print("   1. Windows starts up")
        print("   2. Voice Assistant link in startup folder activates")
        print("   3. start_assistant_silent.bat runs")
        print("   4. Assistant starts in background with virtual environment")
        print("   5. You can say 'Friday' or 'Hey Friday' to activate")
        print("\n🚀 READY TO GO! Restart your laptop to test auto-start.")
    else:
        print("🎯 AUTO-START STATUS: ⚠️ NEEDS ATTENTION")
        print("\n🔧 Issues to fix:")
        if not startup_link.exists():
            print("   - Create startup shortcut")
        if not assistant_py.exists():
            print("   - Assistant file missing")
        if not deps_ok:
            print("   - Install missing dependencies")

if __name__ == "__main__":
    try:
        check_autostart_status()
    except Exception as e:
        print(f"❌ Error checking auto-start status: {e}")
        sys.exit(1)