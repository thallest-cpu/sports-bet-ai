import subprocess
import sys
import os
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent
    venv_python = base_dir / ".venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        python_cmd = sys.executable
    else:
        python_cmd = str(venv_python)

    print(f"Iniciando BetAI Analytics com {python_cmd}...")
    cmd = [python_cmd, "-m", "streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"]
    subprocess.run(cmd, cwd=base_dir)

if __name__ == "__main__":
    main()
