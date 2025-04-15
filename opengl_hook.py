
# PyInstaller runtime hook to fix OpenGL platform detection on macOS
import os
import sys

def patch_opengl():
    try:
        import OpenGL
        # Manually set platform to GLUT for macOS
        OpenGL.USE_ACCELERATE = False
        
        # Patch the platform selection logic
        def _replacement_load(name=None):
            return OpenGL.platform.baseplatform.BasePlatform()
            
        # Apply the patch only on macOS
        if sys.platform == 'darwin':
            OpenGL.platform._load = _replacement_load
            print("Successfully patched OpenGL platform detection for macOS")
    except Exception as e:
        print(f"Error patching OpenGL: {e}")
        
# Apply the patch
patch_opengl()
