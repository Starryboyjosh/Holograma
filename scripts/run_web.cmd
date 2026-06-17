@echo off
echo Iniciando Servidor Web del Holograma...
cd /d "%~dp0"
call .venv\Scripts\activate
python main.py
pause
