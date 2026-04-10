"""
setup.py — One-time environment setup script.
Run this before using the project for the first time.

Usage:
  python setup.py
"""

import subprocess
import sys
import urllib.request
from pathlib import Path


def run(cmd, check=True):
    print(f"  > {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def check_python():
    v = sys.version_info
    if v.major < 3 or v.minor < 10:
        print(f"✗ Python 3.10+ required. You have {v.major}.{v.minor}")
        sys.exit(1)
    print(f"✓ Python {v.major}.{v.minor}.{v.micro}")


def check_ollama():
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=3)
        print("✓ Ollama is running")
        return True
    except Exception:
        print("✗ Ollama is not running.")
        print("  → Download from: https://ollama.com")
        print("  → Then run:      ollama serve")
        return False


def install_requirements():
    print("\nInstalling Python dependencies...")
    result = run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=False)
    if result.returncode == 0:
        print("✓ Dependencies installed")
    else:
        print(f"✗ pip install failed:\n{result.stderr}")
        sys.exit(1)


def pull_models():
    print("\nPulling Ollama models...")
    for model in ["nomic-embed-text", "llama3"]:
        print(f"  Pulling '{model}'...")
        result = run(["ollama", "pull", model], check=False)
        if result.returncode == 0:
            print(f"  ✓ {model} ready")
        else:
            print(f"  ✗ Failed to pull {model}: {result.stderr.strip()}")


def create_folders():
    for folder in ["data", "vectorstore", "output"]:
        Path(folder).mkdir(exist_ok=True)
    print("✓ Folders ready: data/, vectorstore/, output/")


if __name__ == "__main__":
    print("=" * 50)
    print("  Metadata RAG — Environment Setup")
    print("=" * 50)

    print("\n[1/4] Checking Python...")
    check_python()

    print("\n[2/4] Creating folders...")
    create_folders()

    print("\n[3/4] Installing Python packages...")
    install_requirements()

    print("\n[4/4] Checking Ollama + pulling models...")
    if check_ollama():
        pull_models()
    else:
        print("\n  Skipping model pull — start Ollama first, then re-run setup.py")

    print("\n" + "=" * 50)
    print("  Setup complete!")
    print("  Next steps:")
    print("  1. Make sure Ollama is running: ollama serve")
    print("  2. Drop your CSV files into data/")
    print("  3. Run: python main.py")
    print("=" * 50)
