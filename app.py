"""Compatibility launcher for the documented Streamlit entrypoint: app/app.py."""

from pathlib import Path
import runpy
import sys

APP_DIRECTORY = Path(__file__).resolve().parent / "app"
sys.path.insert(0, str(APP_DIRECTORY))
runpy.run_path(str(APP_DIRECTORY / "app.py"), run_name="__main__")
