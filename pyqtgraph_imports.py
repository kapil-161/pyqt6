
# pyqtgraph_imports.py - Manual imports for PyQtGraph to avoid crash during analysis
# This allows PyInstaller to capture imports without running problematic code

# Explicitly import PyQt6 first to ensure it's used instead of PyQt5
import PyQt6
import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets

# Core PyQtGraph imports
import pyqtgraph

# Only import the specific submodules we need for our application
from pyqtgraph import functions
from pyqtgraph import Point
from pyqtgraph import Qt
from pyqtgraph import ptime

# Import specific graphic items
from pyqtgraph.graphicsItems import PlotItem
from pyqtgraph.graphicsItems import ViewBox
from pyqtgraph.graphicsItems import PlotDataItem
from pyqtgraph.graphicsItems import AxisItem
from pyqtgraph.graphicsItems import GridItem 
from pyqtgraph.graphicsItems import ScatterPlotItem
from pyqtgraph.graphicsItems import TextItem
from pyqtgraph.graphicsItems import InfiniteLine
from pyqtgraph.graphicsItems import LabelItem

# Import widgets (need to be explicit to avoid loading console/canvas)
from pyqtgraph.widgets import PlotWidget

# Explicitly avoid problematic modules
# DO NOT IMPORT: pyqtgraph.canvas, pyqtgraph.opengl, pyqtgraph.console, pyqtgraph.jupyter

# Tell PyInstaller this is a dependency
__all__ = ['pyqtgraph', 'PyQt6']
