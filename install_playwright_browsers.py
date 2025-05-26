#!/usr/bin/env python
"""
Script to install Playwright browsers programmatically.
Can be used in CI/CD environments or locally.

Usage:
    python install_playwright_browsers.py
"""
import subprocess
import sys
import os
from pathlib import Path

def install_playwright_browsers():
    """Install Playwright browsers with all system dependencies."""
    try:
        print("Installing Playwright browsers...")
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--with-deps"], 
            check=True
        )
        print("Successfully installed Playwright browsers!")
        
        # Verify installation by checking browser paths
        browsers_dir = Path.home() / ".cache" / "ms-playwright"
        if browsers_dir.exists():
            print(f"Browsers installed at: {browsers_dir}")
            for item in browsers_dir.iterdir():
                if item.is_dir():
                    print(f" - {item.name}")
        else:
            print(f"Warning: Browser directory not found at {browsers_dir}")
            
    except subprocess.CalledProcessError as e:
        print(f"Error installing Playwright browsers: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Playwright command not found. Make sure it's installed correctly.")
        sys.exit(1)

if __name__ == "__main__":
    install_playwright_browsers()
