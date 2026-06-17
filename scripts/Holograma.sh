#!/bin/bash
# Re-enable virtual environment and run the main entrypoint
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/.. && pwd )"
cd "$BASE_DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d ".env" ]; then
    source .env/bin/activate
fi

export PYTHONIOENCODING=utf-8
python3 main.py
