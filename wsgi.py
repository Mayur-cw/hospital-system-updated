# wsgi.py - Production WSGI entry point for Render, Gunicorn, and cloud deployment
import os
import sys
from pathlib import Path

# Ensure PROJECT directory is in python path
ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR / "PROJECT"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app import app, create_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
