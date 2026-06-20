#!/bin/bash
echo "Iniciando Servidor Web del Holograma..."
cd "$(dirname "$0")"/..
source .venv/bin/activate
python3 main.py
