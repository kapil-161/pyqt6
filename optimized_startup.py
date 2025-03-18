"""
Optimized startup settings for DSSAT Viewer
Includes performance optimizations for PyQt and PyQtGraph
"""
import os
import sys
import logging
from PyQt5.QtCore import Qt, QCoreApplication, QSettings
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QApplication

# Configure logging
logger = logging.getLogger(__name__)

def optimize_qt_settings():
    """Apply performance optimizations for PyQt"""
    # Disable high DPI scaling which can cause performance issues
    # This should be called before QApplication is initialized
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, False)
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
    
    # Disable desktop effects for performance
    QCoreApplication.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
    
    # Set application name and organization for settings
    QCoreApplication.setApplicationName("DSSAT Viewer")
    QCoreApplication.setOrganizationName("DSSAT")
    
    # Set environment variables for performance
    os.environ["QT_SCALE_FACTOR"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"
    
    # For OpenGL acceleration
    os.environ["QSG_RENDER_LOOP"] = "basic"  # Use basic render loop for better performance
    
    logger.info("Applied Qt performance optimizations")
    return True

def optimize_qtgraph_settings():
    """Apply performance optimizations for PyQtGraph"""
    try:
        import pyqtgraph as pg
        
        # Use OpenGL for hardware acceleration if available
        pg.setConfigOption('useOpenGL', True)
        
        # Disable antialiasing for faster rendering
        pg.setConfigOption('antialias', False)
        
        # Enable downsampling for large datasets
        pg.setConfigOption('downsample', True)
        
        # Set background to solid color (faster than transparent)
        pg.setConfigOption('background', 'w')  # White
        
        # Optimize other settings
        pg.setConfigOption('exitCleanup', False)  # Faster exit
        
        logger.info("Applied PyQtGraph performance optimizations")
        return True
    except ImportError:
        logger.warning("PyQtGraph not found, skipping optimizations")
        return False

def set_memory_optimizations():
    """Apply memory usage optimizations"""
    # Limit cache sizes
    import pandas as pd
    pd.options.mode.chained_assignment = None  # Disable chained assignment warning
    pd.options.display.max_columns = 50  # Limit display columns
    
    # Set numpy performance options
    try:
        import numpy as np
        np.seterr(all='ignore')  # Ignore numpy warnings for performance
    except ImportError:
        pass
    
    # Clean up memory
    import gc
    gc.enable()  # Ensure garbage collection is enabled
    
    logger.info("Applied memory optimizations")
    return True

def optimize_application(app):
    """Apply optimizations to a QApplication instance"""
    # Set style to Fusion which is generally more performant
    app.setStyle('Fusion')
    
    # Disable animated effects
    app.setEffectEnabled(Qt.UI_AnimateCombo, False)
    app.setEffectEnabled(Qt.UI_AnimateTooltip, False)
    app.setEffectEnabled(Qt.UI_FadeMenu, False)
    app.setEffectEnabled(Qt.UI_FadeTooltip, False)
    
    # Set desktop settings for performance
    settings = QSettings()
    settings.setValue("GUI/ComputeHighDPI", False)
    settings.setValue("GUI/ShowToolTips", False)
    settings.setValue("GUI/AnimateMenu", False)
    
    # Set palette for better performance (less translucency)
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, Qt.black)
    app.setPalette(palette)
    
    # Set a reasonable default font
    from PyQt5.QtGui import QFont
    app.setFont(QFont("Segoe UI", 9))
    
    # Set OpenGL settings if available
    try:
        from PyQt5.QtCore import QCoreApplication
        QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    except:
        pass
    
    logger.info("Optimized QApplication instance")
    return app