@echo off
cd /d "C:\Users\madhu\OneDrive\Desktop\Karthik\Project\Voice assistant"

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo Using virtual environment...
    REM Start with virtual environment activated
    start /min cmd /c "call .venv\Scripts\activate.bat && python assistant.py"
) else (
    echo Using system Python...
    start /min cmd /c "python assistant.py"
)

echo Voice Assistant startup initiated.
timeout /t 2 /nobreak >nul
exit