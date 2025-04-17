
# hook-pyqtgraph.py - Disable automatic collection and use manual imports instead

# Tell PyInstaller NOT to collect submodules automatically
def hook(hook_api):
    hook_api.add_option('pathex', 'pyqtgraph')
    
# These are the only modules we'll use - everything else is excluded
hiddenimports = [
    'pyqtgraph.functions',
    'pyqtgraph.Point',
    'pyqtgraph.Qt',
    'pyqtgraph.ptime',
    'pyqtgraph.graphicsItems.PlotItem',
    'pyqtgraph.graphicsItems.ViewBox',
    'pyqtgraph.graphicsItems.PlotDataItem',
    'pyqtgraph.graphicsItems.AxisItem',
    'pyqtgraph.graphicsItems.GridItem',
    'pyqtgraph.graphicsItems.ScatterPlotItem',
    'pyqtgraph.graphicsItems.TextItem',
    'pyqtgraph.graphicsItems.InfiniteLine',
    'pyqtgraph.graphicsItems.LabelItem',
    'pyqtgraph.widgets.PlotWidget'
]

# Explicitly EXCLUDE all problematic modules
excludedimports = [
    'pyqtgraph.canvas',
    'pyqtgraph.opengl',
    'pyqtgraph.examples',
    'pyqtgraph.jupyter',
    'pyqtgraph.console',
    'jupyter_rfb',
    'ipykernel',
    'ipython',
    'jupyter_client',
    'nbformat',
    'notebook'
]

# Don't collect pyqtgraph data files automatically
datas = []
