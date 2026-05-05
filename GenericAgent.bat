@echo off
cd /d "%~dp0"
if not exist "temp" mkdir "temp"
if not exist "memory" mkdir "memory"
start "" "%~dp0.venv\Scripts\python.exe" "%~dp0launch.pyw"
