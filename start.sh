#!/usr/bin/env bash
# One command: bash start.sh
cd "$(dirname "$0")"
if [ ! -d venv ]; then
  python3 -m venv venv 2>/dev/null || { sudo apt update && sudo apt install -y python3-venv python3-pip && python3 -m venv venv; }
fi
source venv/bin/activate
pip install -q -r requirements.txt
python run.py
