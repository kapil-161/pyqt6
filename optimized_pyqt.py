
# Add to your code to optimize PyQt5 loading

# Only import essential PyQt5 modules
import PyQt6.QtCore
import PyQt6.QtWidgets
import PyQt6.QtGui

# Prevent loading these modules which aren't needed
sys.modules['PyQt5.QtNetwork'] = None
sys.modules['PyQt5.QtQml'] = None
sys.modules['PyQt5.QtQuick'] = None
sys.modules['PyQt5.QtMultimedia'] = None
sys.modules['PyQt5.QtWebEngine'] = None

# Optimize Qt settings for faster loading
from PyQt6.QtCore import QCoreApplication
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
QCoreApplication.setAttribute(Qt.AA_UseDesktopOpenGL)
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

# Set environment variables
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"

# Disable Qt plugins selectively
os.environ["QT_PLUGIN_PATH"] = ""  # Don't load system plugins
