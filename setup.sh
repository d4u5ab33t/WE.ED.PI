#!/usr/bin/env bash
# Simple Linux/Mac setup

set -euo pipefail

echo "🚀 WE.ED.IT Setup"

# Python venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p clip_pool output temp cache

echo "✅ Setup complete!"
echo "Activate venv: source venv/bin/activate"
echo "Start app: streamlit run app.py"
