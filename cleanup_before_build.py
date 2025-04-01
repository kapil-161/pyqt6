import os
import shutil

def cleanup_before_build():
    # List of patterns to remove
    patterns_to_clean = [
        "*.pyc",
        "__pycache__",
        "*.bak",
        "*.log",
        "*.tmp"
    ]
    
    # Clean current directory
    for pattern in patterns_to_clean:
        os.system(f"del /S /Q {pattern}")
    
    print("Cleanup completed")

if __name__ == "__main__":
    cleanup_before_build()