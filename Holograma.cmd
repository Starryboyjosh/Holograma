@echo off
setlocal

cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
  echo No encontre .venv\Scripts\python.exe.
  echo Crea el entorno con: py -3.13 -m venv .venv
  pause
  exit /b 1
)

".venv\Scripts\python.exe" call.py %*
