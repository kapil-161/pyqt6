# Set Qt attributes before ANY Qt imports or initialization
from PyQt6.QtCore import Qt, QCoreApplication
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL, True)

"""
DSSAT Viewer - Main entry point
Updated with pure PyQt6 implementation (no Dash)
Optimized for performance and fast tab switching
"""
import sys
import os
import warnings
import logging
import gc
from pathlib import Path
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QMessageBox, QStyleFactory
from utils.performance_monitor import PerformanceMonitor, function_timer
from ui.main_window import MainWindow  # Import MainWindow at the top level

# Initialize performance monitor
perf_monitor = PerformanceMonitor()

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
    'min_height': 700
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
    screen = window.screen().availableGeometry()
    window_size = window.geometry()
    x = (screen.width() - window_size.width()) // 2
    y = (screen.height() - window_size.height()) // 2
    window.move(x, y)

# Import splash screen after optimizations
from splash_screen import show_splash

@function_timer("startup")
def initialize_app():
    """Initialize Qt application with monitoring"""
    timer_id = perf_monitor.start_timer("startup", "qt_init")
    app = QApplication(sys.argv)
    perf_monitor.stop_timer(timer_id)
    return app

@function_timer("startup")
def create_main_window():
    """Create and set up main window with monitoring"""
    timer_id = perf_monitor.start_timer("startup", "window_creation")
    window = MainWindow()
    window.show()
    center_window(window)
    perf_monitor.stop_timer(timer_id)
    return window

@function_timer("startup")
def main():
    """Main application entry point with error handling and optimizations."""
    startup_timer = perf_monitor.start_timer("application", "total_startup")
    
    try:
        app = initialize_app()
        
        # Apply Qt optimizations
        try:
            from optimized_startup import optimize_qt_settings
            optimize_qt_settings()
        except ImportError:
            pass
            
        # Apply application optimizations
        try:
            from optimized_startup import optimize_application
            app = optimize_application(app)
        except:
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
            
            # Start timing main window creation
            window_timer = perf_monitor.start_timer("ui", "main_window_creation")
            main_window = create_main_window()
            perf_monitor.stop_timer(window_timer)
            
            # Configure window
            main_window.resize(WINDOW_CONFIG['width'], WINDOW_CONFIG['height'])
            main_window.setMinimumSize(
                QSize(WINDOW_CONFIG['min_width'], WINDOW_CONFIG['min_height'])
            )
            
            # Center window
            center_window(main_window)
            
            # Stop total initialization timer
            perf_monitor.stop_timer(startup_timer, "Application startup completed")
            
            # Log startup time
            init_time = time.time() - start_time
            logger.info(f"Application initialized in {init_time:.2f} seconds")
            perf_monitor.print_report()
            
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
        perf_monitor.stop_timer(startup_timer, f"Error during startup: {str(e)}")
        
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