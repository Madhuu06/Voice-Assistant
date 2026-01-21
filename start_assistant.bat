@echo off
echo Starting Voice Assistant...
cd /d "C:\Users\madhu\OneDrive\Desktop\Karthik\Project\Voice assistant"
echo Current directory: %CD%

REM Check if virtual environment exists and activate it
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo Using Python: 
    where python
    echo Checking if assistant.py exists...
    if exist assistant.py (
        echo Found assistant.py, starting...
        python assistant.py
    ) else (
        echo ERROR: assistant.py not found!
        pause
    )
) else (
    echo Virtual environment not found, using system Python...
    echo Checking if assistant.py exists...
    if exist assistant.py (
        echo Found assistant.py, starting...
        python assistant.py
    ) else (
        echo ERROR: assistant.py not found!
        pause
    )
)
echo Script ended.
pause
