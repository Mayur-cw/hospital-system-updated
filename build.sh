#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Initialize database schema and synthetic seed data if not present
python scripts/seed_synthetic.py
