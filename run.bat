@echo off
cd /d "%~dp0"
echo Starting ABOS...
py -3 main.py
if errorlevel 1 (
  echo.
  echo ABOS exited with an error. Try: py -3 -m pip install -r requirements.txt
  pause
)
