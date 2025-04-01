"""
DSSAT Viewer - Main entry point
Updated with pure PyQt6 implementation (no Dash)
Updated with pure PyQt6 implementation (no Dash)
Optimized for performance and fast tab switching
"""
import sys
import os
import warnings

import logging
import gc
from pathlib import Path
from PyQt6.QtCore import  QSize, QCoreApplication
from PyQt6.QtWidgets import QApplication, QMessageBox

# Configure logging first - use INFO level to avoid excessive logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Setup performance monitoring
import time
start_time = time.time()
logger = logging.getLogger(__name__)
logger.info("Starting DSSAT Viewer application...")

# Add constants for window dimensions and positioning
WINDOW_CONFIG = {
    'width': 1400,
    'height': 800,
    'min_width': 1000,
    'min_height': 600
}

# Apply startup optimizations before creating any Qt objects
try:
    from optimized_startup import (
        optimize_qt_settings, 
        optimize_qtgraph_settings, 
        set_memory_optimizations,
        optimize_application
    )
    # Apply Qt optimizations before creating QApplication
    logger.info("Applying Qt optimizations...")
    optimize_qt_settings()
    
    # Configure memory optimizations
    logger.info("Applying memory optimizations...")
    set_memory_optimizations()
    
except ImportError:
    logging.warning("Optimization module not found, running without optimizations")

# Suppress warnings for performance
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Add the project root directory to the Python path
project_dir = Path(__file__).parent
sys.path.append(str(project_dir))

# OPTIMIZATION: Remove direct import of numpy and pandas since they're not used in this file
# Let the modules that need them import them directly

def center_window(window):
    """Center window on screen"""
    screen = QApplication.primaryScreen().geometry()
    window.move(
        (screen.width() - window.width()) // 2,
        (screen.height() - window.height()) // 2
    )
def create_application():
    """Create and configure the QApplication instance with optimizations."""
    if not QApplication.instance():
        # Create application first
        app = QApplication(sys.argv)
        
        # Set application name and organization
        QCoreApplication.setApplicationName("DSSAT Viewer")
        QCoreApplication.setOrganizationName("DSSAT")
        
        # Apply more optimizations if available
        try:
            app = optimize_application(app)
        except Exception as e:
            logger.warning(f"Error applying optimizations: {e}")
            # Note: In PyQt6, setStyle requires a QStyle instance, not a string
            try:
                from PyQt6.QtWidgets import QStyleFactory
                app.setStyle(QStyleFactory.create('Fusion'))
            except Exception as e2:
                logger.warning(f"Error setting style: {e2}")
            
        return app
    return QApplication.instance()

# Import splash screen after optimizations
from splash_screen import show_splash

def main():
    """Main application entry point with error handling and optimizations."""
    try:
        # Apply Qt optimizations first
        try:
            from optimized_startup import optimize_qt_settings
            optimize_qt_settings()
        except ImportError:
            pass
            
        # Create application instance
        app = QApplication(sys.argv)
        
        # Apply application optimizations
        try:
            from optimized_startup import optimize_application
            app = optimize_application(app)
        except:
            # Use QStyleFactory to create a Fusion style instance
            from PyQt6.QtWidgets import QStyleFactory
            app.setStyle(QStyleFactory.create('Fusion'))
            
        # Show splash screen
        splash = show_splash(app)
        app.processEvents()  # Ensure splash is displayed
        
        # Apply PyQtGraph optimizations
        try:
            from optimized_startup import optimize_qtgraph_settings
            optimize_qtgraph_settings()
        except:
            pass
        
        # Import and initialize main application
        try:
            logger.info("Initializing main window...")
            from ui.main_window import MainWindow
            main_window = MainWindow()
            
            # Configure window
            main_window.resize(WINDOW_CONFIG['width'], WINDOW_CONFIG['height'])
            main_window.setMinimumSize(
                QSize(WINDOW_CONFIG['min_width'], WINDOW_CONFIG['min_height'])
            )
            
            # Center window
            center_window(main_window)
            
            # Log startup time
            init_time = time.time() - start_time
            logger.info(f"Application initialized in {init_time:.2f} seconds")
            
            # Run garbage collection before showing window
            gc.collect()
            
            # Show main window and close splash
            main_window.show()
            splash.finish(main_window)
            
            # Start event loop
            return app.exec()  # In PyQt6, exec() doesn't have parentheses
            
        except Exception as e:
            splash.close()
            raise
            
    except Exception as e:
        logging.error(f"Error during startup: {e}", exc_info=True)
        
        if QApplication.instance():
            QMessageBox.critical(
                None,
                "Startup Error",
                f"Failed to start DSSAT Viewer:\n{str(e)}"
            )
        return 1

if __name__ == "__main__":
    # Use return code from main function
    exit_code = main()
    
    # Force cleanup before exit
    gc.collect()
    sys.exit(exit_code)