#!/usr/bin/env python3
import subprocess
import sys
import os

def install_dependencies():
    dependencies = [
        "pyqt6==6.2.2",
        "pyqtgraph==0.13.3", 
        "pandas==2.0.3", 
        "numpy==1.24.3"
    ]
    
    print("Installing dependencies for DSSAT Viewer...")
    for dep in dependencies:
        print(f"Installing {dep}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
    
    print("All dependencies installed successfully.")
    
    if os.name == 'nt':  # Windows
        input("Press Enter to continue...")

if __name__ == "__main__":
    install_dependencies()
