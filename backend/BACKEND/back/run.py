"""
Start CityPulse Jaipur: backend API (port 8000) + frontend (port 8501).

    python3 run.py

Press Ctrl+C in this terminal to stop both.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
PY = sys.executable

print("\n  Starting CityPulse Jaipur...\n")
api = subprocess.Popen([PY, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"])
time.sleep(2.5)
ui = subprocess.Popen([PY, "-m", "streamlit", "run", "app.py"])
print("\n  Dashboard:  http://localhost:8501"
      "\n  API docs:   http://127.0.0.1:8000/docs"
      "\n  Stop:       press Ctrl+C here\n")

warned = False
try:
    while ui.poll() is None:
        if api.poll() is not None and not warned:
            print("\n  The backend stopped (is something else using port 8000?)."
                  "\n  The dashboard keeps working with its built-in replay.\n")
            warned = True
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    for p in (ui, api):
        if p.poll() is None:
            p.terminate()
    for p in (ui, api):
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()
    print("\n  CityPulse stopped. Bye!\n")
