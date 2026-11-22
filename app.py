# app.py - Root entry point for Render default start command (gunicorn app:app)
import os
import sys
import importlib.util
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR / "PROJECT"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Load the actual application from PROJECT/app.py avoiding circular import
project_app_path = PROJECT_DIR / "app.py"
spec = importlib.util.spec_from_file_location("project_app", project_app_path)
project_app_module = importlib.util.module_from_spec(spec)
sys.modules["project_app"] = project_app_module
spec.loader.exec_module(project_app_module)

app = project_app_module.app
create_app = project_app_module.create_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
