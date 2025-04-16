"""
Time Series Plot Widget for DSSAT Viewer
Replaces Dash/Plotly with PyQtGraph for time series plotting
"""
import os
import sys
import logging
from typing import List, Dict,  Any

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,  QHBoxLayout, 
     QFrame, QSizePolicy,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QRectF
from PyQt6.QtGui import QBrush, QPen, QColor

# Add project root to path
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_dir)

import config
from utils.dssat_paths import get_crop_details
from data.dssat_io import read_file, read_observed_data
from data.data_processing import (
    handle_missing_xvar, get_variable_info, improved_smart_scale,
    standardize_dtypes, unified_date_convert
)
from models.metrics import MetricsCalculator
from utils.performance_monitor import PerformanceMonitor, function_timer

# Configure logging
logger = logging.getLogger(__name__)

class PlotWidget(QWidget):
    """
    Custom widget for time series visualization using PyQtGraph
    
    Replaces Dash/Plotly graphs with PyQtGraph for better integration
    and performance in a desktop application.
    """
    
    # Signal for metrics calculation
    metrics_calculated = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.perf_monitor = PerformanceMonitor()
        
        # Initialize colors and symbols from config
        self.colors = config.PLOT_COLORS
        self.marker_symbols = config.MARKER_SYMBOLS
        
        # Improved performance configurations
        self.batch_size = 5000  # Increased from 2000
        self.enable_antialiasing = False
        self.downsampling_enabled = True
        self.max_points_before_downsampling = 500  # Reduced threshold for earlier downsampling
        
        # Advanced caching with size limits
        self.variable_info_cache = {}
        self.date_cache = {}
        self.treatment_display_cache = {}
        self.data_cache = {}
        self.plot_item_cache = {}
        self.last_plot_config = None
        self.cache_size_limit = 1000  # Limit cache entries
        
        # Initialize data attributes
        self.sim_data = None
        self.obs_data = None
        
        # Set size policy for proper resizing
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Initialize UI with performance monitoring
        setup_timer = self.perf_monitor.start_timer("ui", "plot_widget_setup")
        self.setup_ui()
        
        # Configure plot defaults for maximum performance
        pg.setConfigOptions(
            antialias=False,
            useOpenGL=True,
            enableExperimental=True,
            foreground='k',
            background='w'
        )
        
        # Configure plot view for better performance
        self.plot_view.setDownsampling(mode='peak', auto=True)
        self.plot_view.setClipToView(True)
        self.plot_view.setAntialiasing(False)
        self.plot_view.setBackground('w')
        self.plot_view.setMouseEnabled(x=True, y=True)
        self.plot_view.enableAutoRange(False)
        self.plot_view.setMenuEnabled(False)
        self.plot_view.setLogMode(False, False)  # Disable log mode by default
        
        self.perf_monitor.stop_timer(setup_timer)
        
    def setup_ui(self):
        """Setup the UI components"""
        # Main layout - horizontal layout with plot and legend
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # Add some padding
        self.setLayout(main_layout)
        
        # Left side - plot and scaling container
        left_container = QWidget()
        left_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout()
        left_container.setLayout(left_layout)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Plot widget
        self.plot_view = pg.PlotWidget()
        self.plot_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.plot_view.setBackground('w')  # White background
        self.plot_view.showGrid(x=True, y=True, alpha=0.3)
        
        # Add extra bottom margin to the plot for x-axis labels and scaling text
        self.plot_view.getPlotItem().getAxis('bottom').setHeight(40)
        
        # Add plot to layout
        left_layout.addWidget(self.plot_view, 1)  # 1 = stretch factor
        
        # Create separated scaling panel at the bottom with clear visual distinction
        scaling_frame = QFrame()
        scaling_frame.setFrameShape(QFrame.Shape.StyledPanel)
        scaling_frame.setFrameShadow(QFrame.Shadow.Raised)
        scaling_frame.setStyleSheet("background-color: #f8f8f8; border: 1px solid #ddd;")
        
        scaling_layout = QVBoxLayout()
        scaling_layout.setContentsMargins(5, 3, 5, 3)  # Small margins
        scaling_frame.setLayout(scaling_layout)
        
        # Scaling panel heading
        scaling_header = QLabel("Scaling Factors:")
        scaling_header.setStyleSheet("font-weight: bold;")
        scaling_layout.addWidget(scaling_header)
        
        # Actual scaling factors text
        self.scaling_label = QLabel()
        self.scaling_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.scaling_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        scaling_layout.addWidget(self.scaling_label)
        
        # Set a fixed height for the scaling panel
        scaling_frame.setMinimumHeight(60)
        # Let it grow with content but don't let it get too large
        scaling_frame.setMaximumHeight(200)
        scaling_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Add scaling panel to left layout
        left_layout.addWidget(scaling_frame)
        
        # Add left container to main layout (80% of space)
        main_layout.addWidget(left_container, 80)
        
        # Right side - legend container with FIXED position at top
        legend_scroll_area = QScrollArea()
        legend_scroll_area.setWidgetResizable(True)
        legend_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        legend_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        legend_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        legend_scroll_area.setFixedWidth(200)  # Fixed width
        
        # Create a container widget for the legend with fixed alignment
        self.legend_container = QWidget()
        self.legend_layout = QVBoxLayout()
        self.legend_layout.setSpacing(2)  # Reduced spacing between items
        self.legend_layout.setContentsMargins(5, 0, 5, 0)  # Minimal margins
        self.legend_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Always align to top
        
        # Set a strict alignment policy
        self.legend_container.setLayout(self.legend_layout)
        
        # Create a container to hold the legend container
        legend_outer_widget = QWidget()
        legend_outer_layout = QVBoxLayout()
        legend_outer_layout.setContentsMargins(0, 0, 0, 0)
        legend_outer_layout.addWidget(self.legend_container, 0, Qt.AlignmentFlag.AlignTop)  # Force top alignment
        legend_outer_layout.addStretch(1)  # Add stretch at the bottom to push content to the top
        legend_outer_widget.setLayout(legend_outer_layout)
        
        # Set the legend container as the widget for the scroll area
        legend_scroll_area.setWidget(legend_outer_widget)
        
        # Add the scroll area to the main layout
        main_layout.addWidget(legend_scroll_area, 20)  # 20% of space
        
        # Enable auto-range on resize
        self.plot_view.enableAutoRange()
        
        # Connect resize event
        self.resizeEvent = self.on_resize
        
    def on_resize(self, event):
        """Handle resize events"""
        try:
            if hasattr(self, 'sim_data') and self.sim_data is not None:
                # ...existing resize handling code...
                pass
        except Exception as e:
            logger.warning(f"Error during plot resize: {str(e)}")
    


    @function_timer("visualization")
    def plot_time_series(self, selected_folder, selected_out_files, selected_experiment, 
                        selected_treatments, x_var, y_vars, treatment_names=None):
        timer_id = self.perf_monitor.start_timer("ui", "plot_rendering")
        
        try:
            # Check cache first
            plot_config = (selected_folder, tuple(selected_out_files), selected_experiment,
                        tuple(selected_treatments), x_var, tuple(y_vars))
            
            if plot_config == self.last_plot_config and self.data_cache:
                sim_data = self.data_cache.get('sim_data')
                obs_data = self.data_cache.get('obs_data')
                if sim_data is not None:
                    # Reuse cached data
                    self.plot_cached_data(sim_data, obs_data, x_var, y_vars, selected_treatments, treatment_names)
                    duration = self.perf_monitor.stop_timer(timer_id, "Used cached data")
                    return duration

            # Clear the plot view efficiently
            self.plot_view.clear()

            # Process simulation data in batches
            sim_data_list = []
            for file_path in selected_out_files:
                df = read_file(file_path)
                if df is not None and not df.empty:
                    df.columns = df.columns.str.strip().str.upper()
                    
                    # Skip conversion for non-numeric columns like 'CR'
                    numeric_columns = df.columns[~df.columns.isin(['CR', 'CROP'])]
                    for col in numeric_columns:
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                        except Exception as e:
                            logger.warning(f"Could not convert column {col} to numeric: {e}")
                    
                    df = batch_date_convert(df)
                    df['source'] = 'sim'
                    df['FILE'] = os.path.basename(file_path)
                    sim_data_list.append(df)
            
            sim_data = pd.concat(sim_data_list, ignore_index=True) if sim_data_list else None

            # Clear the legend container
            for i in reversed(range(self.legend_layout.count())):
                item = self.legend_layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()
            
            # Collect data from all files
            all_data = []
            for selected_out_file in selected_out_files:
                # Get crop directory
                crop_details = get_crop_details()
                crop_info = next(
                    (crop for crop in crop_details 
                    if crop['name'].upper() == selected_folder.upper()),
                    None
                )
                
                if not crop_info:
                    logger.error(f"Could not find crop info for: {selected_folder}")
                    return

                file_path = os.path.join(crop_info['directory'], selected_out_file)
                sim_data = read_file(file_path)
                
                if sim_data is None or sim_data.empty:
                    continue
                    
                sim_data.columns = sim_data.columns.str.strip().str.upper()
                
                if "TRNO" in sim_data.columns and "TRT" not in sim_data.columns:
                    sim_data["TRT"] = sim_data["TRNO"]
                elif "TRT" not in sim_data.columns:
                    sim_data["TRT"] = "1"
                    
                sim_data["TRT"] = sim_data["TRT"].astype(str)
                
                for col in ["YEAR", "DOY"]:
                    if col in sim_data.columns:
                        sim_data[col] = (
                            pd.to_numeric(sim_data[col], errors="coerce")
                            .fillna(0)
                            .replace([np.inf, -np.inf], 0)
                        )
                    else:
                        sim_data[col] = 0
                        
                sim_data["DATE"] = sim_data.apply(
                    lambda row: unified_date_convert(row["YEAR"], row["DOY"]),
                    axis=1,
                )
                
                # Convert to string for compatibility
                sim_data["DATE"] = sim_data["DATE"].dt.strftime("%Y-%m-%d")
                sim_data["source"] = "sim"
                sim_data["FILE"] = selected_out_file
                all_data.append(sim_data)
                
            if not all_data:
                logger.warning("No simulation data available")
                return
                
            # Combine all simulation data
            sim_data = pd.concat(all_data, ignore_index=True)
            missing_values = {-99, -99.0, -99.9, -99.99}
            
            # Read observed data
            obs_data = None
            if selected_experiment:
                obs_data = read_observed_data(
                    selected_folder, selected_experiment, x_var, y_vars
                )
                if obs_data is not None and not obs_data.empty:
                    logger.info(f"Loaded observed data with shape: {obs_data.shape}")
                    obs_data["source"] = "obs"
                    obs_data = handle_missing_xvar(obs_data, x_var, sim_data)
                    
                    if obs_data is not None:
                        if "TRNO" in obs_data.columns:
                            obs_data["TRNO"] = obs_data["TRNO"].astype(str)
                            obs_data = obs_data.rename(columns={"TRNO": "TRT"})
                            
                        for var in y_vars:
                            if var in obs_data.columns:
                                obs_data[var] = pd.to_numeric(
                                    obs_data[var], errors="coerce"
                                )
                                obs_data.loc[
                                    obs_data[var].isin(missing_values), var
                                ] = np.nan
                        
                        # Store the original data before scaling
                        self.obs_data = obs_data.copy()
            
            # Scale data for visualization
            sim_scaling_factors = {}
            if len(y_vars) > 1:
                # First pass: determine magnitude range
                magnitudes = {}
                for var in y_vars:
                    if var in sim_data.columns:
                        sim_values = (
                            pd.to_numeric(sim_data[var], errors="coerce")
                            .dropna()
                            .values
                        )
                        if len(sim_values) > 0 and not np.isclose(np.min(sim_values), np.max(sim_values)):
                            avg_value = np.mean(np.abs(sim_values))
                            if avg_value > 0:
                                magnitudes[var] = np.floor(np.log10(avg_value))
                
                # Skip if less than 2 valid variables
                if len(magnitudes) >= 2:
                    # Find reference magnitude (highest one)
                    reference_magnitude = max(magnitudes.values())
                    
                    # Calculate scaling factors based on powers of 10
                    for var, magnitude in magnitudes.items():
                        power_diff = reference_magnitude - magnitude
                        scale_factor = 10 ** power_diff
                        offset = 0
                        sim_scaling_factors[var] = (scale_factor, offset)
            
            # Store scaling factors
            self.scaling_factors = sim_scaling_factors
            
            # Apply scaling
            sim_scaled = improved_smart_scale(
                sim_data, y_vars, scaling_factors=sim_scaling_factors
            )
            
            for var in sim_scaled:
                sim_data[f"{var}_original"] = sim_data[var]
                sim_data[var] = sim_scaled[var]
                
            if obs_data is not None and not obs_data.empty:
                obs_scaled = improved_smart_scale(
                    obs_data, y_vars, scaling_factors=sim_scaling_factors
                )
                for var in obs_scaled:
                    obs_data[f"{var}_original"] = obs_data[var]
                    obs_data[var] = obs_scaled[var]
            
            # Store data for future use
            self.sim_data = sim_data
            self.obs_data = obs_data
            
            # Create scaling text with plain text formatting
            scaling_parts = []
            for var, (scale_factor, offset) in sim_scaling_factors.items():
                var_label, _ = get_variable_info(var)
                display_name = var_label or var
                scaling_parts.append(f"{display_name} = {scale_factor:.2f} * {display_name}")
            scaling_text = "\n".join(scaling_parts)
            self.scaling_label.setText(scaling_text)
            self.scaling_label.setWordWrap(True)
            
            # Set plot title and labels
            self.plot_view.setTitle("")
            x_label, _ = get_variable_info(x_var)
            x_display = x_label or x_var
            self.plot_view.setLabel('bottom', text=x_display, **{
                'color': '#000000',
                'font-weight': 'bold',
                'font-size': '12pt'
            })
            
            # Set y-axis label
            y_axis_label = ", ".join(
                get_variable_info(var)[0] or var
                for var in y_vars
                if var in sim_data.columns
            )
            self.plot_view.setLabel('left', text=y_axis_label, **{
                'color': '#0066CC',
                'font-weight': 'bold',
            })
            
            # Create custom Qt legend
            legend_label = QLabel("<b>Legend</b>")
            legend_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.legend_layout.addWidget(legend_label)
            
            # Storage for legend entries
            legend_entries = {
                "Simulated": {},
                "Observed": {}
            }
            
            # Plot the data
            line_styles = [Qt.PenStyle.SolidLine, Qt.PenStyle.DashLine, Qt.PenStyle.DotLine, Qt.PenStyle.DashDotLine]
            pen_width = 2
            
            for dataset in [sim_data, obs_data]:
                if dataset is not None and not dataset.empty:
                    source_type = dataset["source"].iloc[0]
                    category = "Simulated" if source_type == "sim" else "Observed"
                    
                    if source_type == "obs":
                        print("Observed data being plotted:", dataset)
                        
                    for var_idx, var in enumerate(y_vars):
                        var_label, _ = get_variable_info(var)
                        display_name = var_label or var
                        
                        if display_name not in legend_entries[category]:
                            legend_entries[category][display_name] = []
                        
                        for trt_idx, (trt_value, group) in enumerate(dataset.groupby("TRT")):
                            if (
                                trt_value in selected_treatments
                                and var in group.columns
                                and group[var].notna().any()
                            ):
                                if treatment_names and trt_value in treatment_names:
                                    trt_display = treatment_names[trt_value]
                                else:
                                    trt_display = f"Treatment {trt_value}"
                                color_idx = trt_idx % len(self.colors)
                                style_idx = var_idx % len(line_styles)
                                color = self.colors[color_idx]
                                qt_color = pg.mkColor(color)
                                
                                if source_type == "sim":
                                    pen = pg.mkPen(
                                        color=qt_color, 
                                        width=pen_width, 
                                        style=line_styles[style_idx]
                                    )
                                    
                                    valid_mask = group[var].notna()
                                    x_values = group[valid_mask][x_var].values
                                    y_values = group[valid_mask][var].values
                                    
                                    if x_var == "DATE":
                                        try:
                                            x_dates = pd.to_datetime(x_values)
                                            x_values = [d.timestamp() for d in x_dates]
                                        except Exception as e:
                                            logger.warning(f"Error converting dates: {e}")
                                        
                                    y_values = np.array(y_values, dtype=np.float64)
                                    
                                    curve = self.plot_view.plot(
                                        x_values, y_values, 
                                        pen=pen,
                                        name=None
                                    )
                                    
                                    legend_entries[category][display_name].append({
                                        "item": curve,
                                        "name": trt_display,
                                        "trt": trt_value,
                                        "pen": pen,
                                        "symbol": None
                                    })
                                    
                                else:
                                    symbol_idx = (trt_idx + var_idx * len(selected_treatments)) % len(self.marker_symbols)
                                    symbol = self.marker_symbols[symbol_idx]
                                    
                                    valid_mask = group[var].notna()
                                    x_values = group[valid_mask][x_var].values
                                    y_values = group[valid_mask][var].values
                                    
                                    if x_var == "DATE":
                                        try:
                                            x_dates = pd.to_datetime(x_values)
                                            x_values = [d.timestamp() for d in x_dates]
                                        except Exception as e:
                                            logger.warning(f"Error converting dates: {e}")
                                    
                                    symbol_pen = None
                                    if (var_idx + trt_idx) % 2 == 0:
                                        symbol_pen = pg.mkPen(qt_color, width=1)
                                    
                                    scatter = pg.ScatterPlotItem(
                                        x=x_values, y=y_values,
                                        symbol=symbol,
                                        size=8,
                                        pen=symbol_pen, brush=qt_color,
                                        name=None
                                    )
                                    self.plot_view.addItem(scatter)
                                    
                                    legend_entries[category][display_name].append({
                                        "item": scatter,
                                        "name": trt_display,
                                        "trt": trt_value,
                                        "brush": qt_color,
                                        "pen": symbol_pen,
                                        "symbol": symbol
                                    })
            
            # Build the custom legend in batch
            legend_items = []
            for category in ["Simulated", "Observed"]:
                if legend_entries[category]:
                    category_label = QLabel(f"<b>{category}</b>")
                    category_label.setStyleSheet("padding: 2px;")
                    legend_items.append(category_label)
                    
                    for var_name, treatments in sorted(legend_entries[category].items()):
                        var_label = QLabel(f"{var_name}")
                        var_label.setStyleSheet("padding-left: 5px;")
                        legend_items.append(var_label)
                        
                        for treatment in sorted(treatments, key=lambda x: x["trt"]):
                            trt_name = treatment["name"]
                            entry_widget = QWidget()
                            entry_layout = QHBoxLayout()
                            entry_layout.setSpacing(2)
                            entry_layout.setContentsMargins(10, 0, 0, 0)
                            entry_widget.setLayout(entry_layout)
                            
                            sample_widget = pg.PlotWidget(background=None)
                            sample_widget.setFixedSize(30, 15)
                            sample_widget.hideAxis('left')
                            sample_widget.hideAxis('bottom')
                            sample_widget.setMouseEnabled(False, False)
                            
                            if "symbol" in treatment and treatment["symbol"] is not None:
                                sample = pg.ScatterPlotItem(
                                    x=[0.5], y=[0.5],
                                    symbol=treatment["symbol"],
                                    size=8,
                                    pen=treatment["pen"],
                                    brush=treatment["brush"]
                                )
                            else:
                                sample = pg.PlotDataItem(
                                    x=[0, 1], y=[0.5, 0.5],
                                    pen=treatment["pen"]
                                )
                            sample_widget.addItem(sample)
                            
                            entry_layout.addWidget(sample_widget)
                            label = QLabel(trt_name)
                            label.setStyleSheet("padding: 0px;")
                            entry_layout.addWidget(label)
                            entry_layout.addStretch(1)
                            
                            legend_items.append(entry_widget)
            
            # Add all legend items at once
            for item in legend_items:
                self.legend_layout.addWidget(item)
            
            # Set nice axis formatting for dates
            if x_var == "DATE":
                date_axis = pg.DateAxisItem(orientation='bottom')
                date_axis.setLabel(text="Date", **{'color': '#000000', 'font-weight': 'bold'})
                self.plot_view.setAxisItems({'bottom': date_axis})
                
            # Enable auto-ranging and show grids
            self.plot_view.enableAutoRange()
            self.plot_view.showGrid(x=True, y=True)
            
            # Update the view
            self.plot_view.updateGeometry()
            
            # Cache the data for future use
            self.data_cache = {
                'sim_data': sim_data,
                'obs_data': obs_data
            }
            self.last_plot_config = plot_config

            # Calculate and emit metrics if we have observed data
            if obs_data is not None and not obs_data.empty:
                self.calculate_metrics(sim_data, obs_data, y_vars, selected_treatments, treatment_names)
                
            duration = self.perf_monitor.stop_timer(timer_id, f"Plotted {len(sim_data)} points")
            return duration
            
        except Exception as e:
            self.perf_monitor.stop_timer(timer_id, f"Error: {str(e)}")
            raise

    @function_timer("visualization")
    def plot_cached_data(self, sim_data, obs_data, x_var, y_vars, selected_treatments, treatment_names):
        """Plot using cached data for better performance"""
        timer_id = self.perf_monitor.start_timer("plotting", "cached_data")
        try:
            # Clear previous plot efficiently
            self.plot_view.clear()
            self.plot_view.enableAutoRange(False)
            
            # Reuse existing scaling factors
            if self.scaling_factors:
                scaling_timer = self.perf_monitor.start_timer("data_processing", "apply_scaling")
                sim_scaled = improved_smart_scale(sim_data, y_vars, scaling_factors=self.scaling_factors)
                for var in sim_scaled:
                    sim_data[var] = sim_scaled[var]
                
                if obs_data is not None and not obs_data.empty:
                    obs_scaled = improved_smart_scale(obs_data, y_vars, scaling_factors=self.scaling_factors)
                    for var in obs_scaled:
                        obs_data[var] = obs_scaled[var]
                self.perf_monitor.stop_timer(scaling_timer)
            
            # Plot data with performance monitoring
            line_styles = [Qt.PenStyle.SolidLine, Qt.PenStyle.DashLine, Qt.PenStyle.DotLine, Qt.PenStyle.DashDotLine]
            pen_width = 2
            
            for dataset in [{'data': sim_data, 'source': 'sim'}, {'data': obs_data, 'source': 'obs'}]:
                if dataset['data'] is not None and not dataset['data'].empty:
                    plot_timer = self.perf_monitor.start_timer("plotting", f"plot_{dataset['source']}_data")
                    self.plot_dataset(
                        dataset['data'], dataset['source'], x_var, y_vars,
                        selected_treatments, treatment_names, line_styles, pen_width
                    )
                    self.perf_monitor.stop_timer(plot_timer)
            
            self.plot_view.enableAutoRange(True)
            self.plot_view.updateGeometry()
            
            self.perf_monitor.stop_timer(timer_id)
        except Exception as e:
            self.perf_monitor.stop_timer(timer_id, f"Error: {str(e)}")
            raise

    @function_timer("visualization")
    def update_plot_for_resize(self):
        """Update plot when window is resized"""
        if hasattr(self, 'plot_view'):
            timer_id = self.perf_monitor.start_timer("ui", "plot_resize")
            self.plot_view.updateGeometry()
            if self.sim_data is not None:
                self.plot_view.autoRange()
            self.perf_monitor.stop_timer(timer_id)

    @function_timer("data_processing")  
    def calculate_metrics(self, sim_data, obs_data, y_vars, selected_treatments, treatment_names=None):
        """
        Calculate performance metrics and emit signal
        
        Args:
            sim_data: Simulation data DataFrame
            obs_data: Observed data DataFrame
            y_vars: List of Y variables
            selected_treatments: List of selected treatments
            treatment_names: Optional dictionary mapping treatment numbers to names
        """
        logger.info(f"Starting metrics calculation for {len(y_vars)} variables and {len(selected_treatments)} treatments")
        
        if obs_data is None or obs_data.empty:
            logger.warning("No observed data available for metrics calculation")
            return
            
        metrics_data = []
        
        # For each treatment and variable, calculate metrics
        for var in y_vars:
            if var not in sim_data.columns or var not in obs_data.columns:
                logger.warning(f"Variable {var} not found in both simulated and observed data")
                continue
                
            for trt in selected_treatments:
                try:
                    # Get data for this treatment
                    sim_trt_data = sim_data[sim_data['TRT'] == trt]
                    obs_trt_data = obs_data[obs_data['TRT'] == trt]
                    
                    if sim_trt_data.empty or obs_trt_data.empty:
                        logger.info(f"No data for treatment {trt}, variable {var} in either sim or obs data")
                        continue
                        
                    # Find common dates
                    common_dates = set(sim_trt_data['DATE']) & set(obs_trt_data['DATE'])
                    logger.info(f"Found {len(common_dates)} common dates for treatment {trt}, variable {var}")
                    
                    if not common_dates:
                        logger.warning(f"No common dates found for treatment {trt}, variable {var}")
                        continue
                        
                    # Filter to common dates
                    sim_values = []
                    obs_values = []
                    
                    for date in common_dates:
                        try:
                            # Try original columns first, fall back to regular columns
                            if f"{var}_original" in sim_trt_data.columns:
                                sim_val = sim_trt_data[sim_trt_data['DATE'] == date][f"{var}_original"].values
                            else:
                                sim_val = sim_trt_data[sim_trt_data['DATE'] == date][var].values
                                
                            if f"{var}_original" in obs_trt_data.columns:
                                obs_val = obs_trt_data[obs_trt_data['DATE'] == date][f"{var}_original"].values
                            else:
                                obs_val = obs_trt_data[obs_trt_data['DATE'] == date][var].values
                            
                            if len(sim_val) > 0 and len(obs_val) > 0:
                                # Skip NA/NaN values
                                if pd.isna(sim_val[0]) or pd.isna(obs_val[0]):
                                    continue
                                    
                                sim_values.append(float(sim_val[0]))
                                obs_values.append(float(obs_val[0]))
                        except Exception as e:
                            logger.warning(f"Error processing date {date}: {e}")
                            continue
                    
                    logger.info(f"Collected {len(sim_values)} valid data points for treatment {trt}, variable {var}")
                    
                    # Get treatment name if available
                    trt_name = trt
                    if treatment_names and trt in treatment_names:
                        trt_name = treatment_names[trt]
                    
                    if len(sim_values) < 2 or len(obs_values) < 2:
                        # Skip metric calculation if not enough valid data points
                        logger.warning(f"Insufficient data points for treatment {trt}, variable {var}")
                        
                        # Get variable display name
                        var_label, _ = get_variable_info(var)
                        display_name = var_label or var
                        
                        metrics_data.append({
                            "Variable": f"{display_name} - {trt_name}",
                            "n": len(sim_values),
                            #"R²": 0.0,  # Not applicable for insufficient points
                            "RMSE": 0.0,
                            "d-stat": 0.0,
                        })
                        continue
                    
                    # Calculate metrics
                    var_label, _ = get_variable_info(var)
                    display_name = var_label or var
                    
                    try:
                        # Use MetricsCalculator for consistency
                        sim_vals = np.array(sim_values, dtype=float)
                        obs_vals = np.array(obs_values, dtype=float)
                        
                        # Calculate R-squared
                        r2 = MetricsCalculator.r_squared(sim_vals, obs_vals)
                        
                        # Calculate RMSE
                        rmse = MetricsCalculator.rmse(obs_vals, sim_vals)
                        
                        # Calculate d-stat
                        d_stat_val = MetricsCalculator.d_stat(obs_vals, sim_vals)
                        
                        # Add to metrics data
                        metrics_data.append({
                            "Variable": f"{display_name} - {trt_name}",
                            "n": len(sim_values),
                            #"R²": round(r2, 3),
                            "RMSE": round(rmse, 3),
                            "d-stat": round(d_stat_val, 3),
                        })
                        
                        logger.info(f"Calculated metrics for {display_name} - {trt_name}: R²={r2:.3f}, RMSE={rmse:.3f}, d-stat={d_stat_val:.3f}")
                        
                    except Exception as e:
                        logger.error(f"Error calculating metrics: {e}", exc_info=True)
                        
                        metrics_data.append({
                            "Variable": f"{display_name} - {trt_name}",
                            "n": len(sim_values),
                            #"R²": 0.0,
                            "RMSE": 0.0,
                            "d-stat": 0.0,
                        })
                except Exception as e:
                    logger.error(f"Error processing treatment {trt} for variable {var}: {e}", exc_info=True)
                    continue
        
        # Emit signal if we have metrics
        if metrics_data:
            logger.info(f"Emitting metrics_calculated signal with {len(metrics_data)} entries")
            self.metrics_calculated.emit(metrics_data)
        else:
            logger.warning("No metrics were calculated, not emitting signal")

    @function_timer("visualization")
    def batch_render_dataset(self, data, var, x_var, color, style, symbol=None):
        """Render a dataset in batches for better performance"""
        timer_id = self.perf_monitor.start_timer("rendering", f"batch_render_{var}")
        try:
            if len(data) <= self.batch_size:
                plot_item = self._render_single_batch(data, var, x_var, color, style, symbol)
                self.perf_monitor.stop_timer(timer_id)
                return plot_item

            batches = []
            for i in range(0, len(data), self.batch_size):
                batch_timer = self.perf_monitor.start_timer("rendering", f"batch_{i//self.batch_size}")
                batch = data.iloc[i:i + self.batch_size]
                plot_item = self._render_single_batch(batch, var, x_var, color, style, symbol)
                if plot_item is not None:
                    batches.append(plot_item)
                self.perf_monitor.stop_timer(batch_timer)
            
            self.perf_monitor.stop_timer(timer_id)
            return batches
        except Exception as e:
            self.perf_monitor.stop_timer(timer_id, f"Error: {str(e)}")
            raise

    def calculate_d_stat(self, measured, simulated):
        """Calculate Willmott's index of agreement (d-stat) with proper error handling."""
        try:
            # Convert inputs to numpy arrays and ensure they are 1D
            M = np.array(measured, dtype=float)
            S = np.array(simulated, dtype=float)
            
            # Skip calculation if arrays have different lengths
            if len(M) != len(S) or len(M) == 0:
                return 0.0
                
            M_mean = np.mean(M)
            
            numerator = np.sum((M - S) ** 2)
            denominator = np.sum((np.abs(M - M_mean) + np.abs(S - M_mean)) ** 2)
            
            return 1 - (numerator / denominator) if denominator != 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error in d_stat calculation: {e}", exc_info=True)
            return 0.0

    def plot_dataset(self, data, source_type, x_var, y_vars, selected_treatments, treatment_names, line_styles, pen_width):
        """Helper method to plot a dataset efficiently"""
        # Debug info
        print(f"=== PLOT_DATASET CALLED ===")
        print(f"Source type: {source_type}")
        print(f"Data shape: {data.shape}")
        print(f"X variable: {x_var}")
        print(f"Y variables: {y_vars}")
        print(f"Selected treatments: {selected_treatments}")
        print(f"Treatments in data: {data['TRT'].unique().tolist()}")
        
        # Check for variable existence
        for var in y_vars:
            print(f"Variable {var} exists in data: {var in data.columns}")
        
        # Add the remaining method implementation...
        # Pre-filter and prepare data
        data = data[data['TRT'].isin(selected_treatments)].copy()
        
        # Pre-compute date conversion if needed
        if x_var == "DATE":
            try:
                data['_x_values'] = pd.to_datetime(data[x_var]).map(lambda x: x.timestamp())
            except Exception as e:
                logger.warning(f"Error converting dates: {e}")
                return {}
        else:
            data['_x_values'] = data[x_var]

        # Initialize legend entries
        legend_entries = {}
        
        # Pre-compute color indices
        color_idx_base = len(self.colors)
        style_idx_base = len(line_styles)
        
        # Process variables in vectorized operations
        for var_idx, var in enumerate(y_vars):
            if var not in data.columns:
                continue

            # Get variable display name once
            var_label, _ = get_variable_info(var)
            display_name = var_label or var
            if display_name not in legend_entries:
                legend_entries[display_name] = []

            # Group and plot by treatment
            groups = data.groupby('TRT')
            for trt_idx, (trt_value, group) in enumerate(groups):
                # Skip empty groups
                valid_mask = group[var].notna()
                if not valid_mask.any():
                    continue

                # Get display info
                trt_display = treatment_names.get(trt_value, f"Treatment {trt_value}") if treatment_names else f"Treatment {trt_value}"
                color_idx = trt_idx % color_idx_base
                style_idx = var_idx % style_idx_base
                color = self.colors[color_idx]
                qt_color = pg.mkColor(color)

                # Get data points efficiently
                x_values = group.loc[valid_mask, '_x_values'].values
                y_values = group.loc[valid_mask, var].values

                # Plot in batches for better performance
                if source_type == "sim":
                    pen = pg.mkPen(color=qt_color, width=pen_width, style=line_styles[style_idx])
                    plot_items = self.batch_render_dataset(x_values, y_values, pen=pen)
                    for item in plot_items:
                        self.plot_view.addItem(item)
                    legend_entries[display_name].append({
                        "items": plot_items,
                        "name": trt_display,
                        "trt": trt_value,
                        "pen": pen,
                        "symbol": None
                    })
                else:
                    symbol_idx = (trt_idx + var_idx * len(selected_treatments)) % len(self.marker_symbols)
                    symbol = self.marker_symbols[symbol_idx]
                    symbol_pen = pg.mkPen(qt_color, width=1) if (var_idx + trt_idx) % 2 == 0 else None
                    
                    plot_items = self.batch_render_points(x_values, y_values, qt_color, symbol, symbol_pen)
                    for item in plot_items:
                        self.plot_view.addItem(item)
                    legend_entries[display_name].append({
                        "items": plot_items,
                        "name": trt_display,
                        "trt": trt_value,
                        "brush": qt_color,
                        "pen": symbol_pen,
                        "symbol": symbol
                    })

        return legend_entries

    def set_render_quality(self, quality='auto'):
        """Set the rendering quality level
        
        Args:
            quality (str): One of 'low', 'high', or 'auto'
        """
        self.render_quality = quality
        
        if quality == 'low':
            self.enable_antialiasing = False
            self.downsampling_enabled = True
            self.batch_size = 500
        elif quality == 'high':
            self.enable_antialiasing = True
            self.downsampling_enabled = False
            self.batch_size = 2000
        else:  # auto
            # Automatically determine settings based on data size
            total_points = 0
            if hasattr(self, 'sim_data') and self.sim_data is not None:
                total_points += len(self.sim_data)
            if hasattr(self, 'obs_data') and self.obs_data is not None:
                total_points += len(self.obs_data)
                
            if total_points > 10000:
                self.enable_antialiasing = False
                self.downsampling_enabled = True
                self.batch_size = 500
            else:
                self.enable_antialiasing = True
                self.downsampling_enabled = False
                self.batch_size = 2000
                
        # Apply settings
        self.plot_view.setAntialiasing(self.enable_antialiasing)
        self.plot_view.setDownsampling(auto=self.downsampling_enabled)
        
        # Trigger replot if we have data
        if hasattr(self, 'sim_data') and self.sim_data is not None:
            self.replot_current_data()

    def batch_render_dataset(self, data, var, x_var, color, style, symbol=None):
        """Render a dataset in batches for better performance
        
        Args:
            data: DataFrame containing the data
            var: Variable to plot
            x_var: X-axis variable
            color: Color to use
            style: Line style (for sim data)
            symbol: Symbol to use (for obs data)
        """
        if len(data) <= self.batch_size:
            return self._render_single_batch(data, var, x_var, color, style, symbol)
            
        batches = []
        for i in range(0, len(data), self.batch_size):
            batch = data.iloc[i:i + self.batch_size]
            plot_item = self._render_single_batch(batch, var, x_var, color, style, symbol)
            if plot_item is not None:
                batches.append(plot_item)
        
        return batches

    def _render_single_batch(self, data, var, x_var, color, style, symbol):
        """Helper method to render a single batch of data"""
        valid_mask = data[var].notna()
        x_values = data.loc[valid_mask, x_var].values
        y_values = data.loc[valid_mask, var].values
        
        if len(x_values) == 0:
            return None
            
        if x_var == "DATE":
            try:
                x_values = pd.to_datetime(x_values).map(lambda x: x.timestamp())
            except Exception as e:
                logger.warning(f"Error converting dates: {e}")
                return None
                
        qt_color = pg.mkColor(color)
        
        if symbol is None:  # Simulation data
            pen = pg.mkPen(color=qt_color, width=2, style=style)
            return self.plot_view.plot(x_values, y_values, pen=pen, name=None)
        else:  # Observed data
            symbol_pen = pg.mkPen(qt_color, width=1)
            scatter = pg.ScatterPlotItem(
                x=x_values, y=y_values,
                symbol=symbol,
                size=8,
                pen=symbol_pen,
                brush=qt_color,
                name=None
            )
            self.plot_view.addItem(scatter)
            return scatter

    def replot_current_data(self):
        """Replot the current data with current settings"""
        if not hasattr(self, 'sim_data') or self.sim_data is None:
            return
            
        self.plot_view.clear()
        self.plot_cached_data(
            self.sim_data,
            self.obs_data,
            self._current_x_var,
            self._current_y_vars,
            self._current_treatments,
            self._current_treatment_names
        )

    def batch_render_points(self, x_values, y_values, color, symbol, symbol_pen=None):
        """Render scatter points in optimized batches"""
        if len(x_values) <= self.batch_size:
            scatter = pg.ScatterPlotItem(
                x=x_values, y=y_values,
                symbol=symbol,
                size=8,
                pen=symbol_pen,
                brush=color,
                name=None,
                antialias=False
            )
            return [scatter]
            
        batches = []
        for i in range(0, len(x_values), self.batch_size):
            batch_x = x_values[i:i + self.batch_size]
            batch_y = y_values[i:i + self.batch_size]
            
            scatter = pg.ScatterPlotItem(
                x=batch_x, y=y_values,
                symbol=symbol,
                size=8,
                pen=symbol_pen,
                brush=color,
                name=None,
                antialias=False
            )
            batches.append(scatter)
            
        return batches

    def batch_render_lines(self, x_values, y_values, pen):
        """Render line segments in optimized batches"""
        if len(x_values) <= self.batch_size:
            return [self.plot_view.plot(x_values, y_values, pen=pen, name=None)]
            
        batches = []
        for i in range(0, len(x_values), self.batch_size):
            batch_x = x_values[i:i + self.batch_size]
            batch_y = y_values[i:i + self.batch_size]
            
            # Add overlap point for smooth transitions between batches
            if i > 0:
                batch_x = np.insert(batch_x, 0, x_values[i-1])
                batch_y = np.insert(batch_y, 0, y_values[i-1])
                
            curve = self.plot_view.plot(batch_x, batch_y, pen=pen, name=None)
            batches.append(curve)
            
        return batches

    def preprocess_data(self, data, x_var, y_vars):
        """Preprocess data efficiently using vectorized operations"""
        # Generate cache key
        cache_key = f"{hash(str(data.index.values))}-{x_var}-{'-'.join(y_vars)}"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]

        # Vectorized operations
        processed = data.copy()
        
        # Convert dates once for all data
        if x_var == "DATE":
            try:
                processed['_x_values'] = pd.to_datetime(processed[x_var]).map(lambda x: x.timestamp())
            except Exception as e:
                logger.warning(f"Error converting dates: {e}")
                processed['_x_values'] = processed[x_var]
        else:
            processed['_x_values'] = processed[x_var]

        # Vectorized numeric conversion for y variables
        for var in y_vars:
            if var in processed.columns:
                processed[var] = pd.to_numeric(processed[var], errors='coerce')

        # Cache result with size management
        if len(self.data_cache) > self.cache_size_limit:
            # Remove oldest entries
            oldest_keys = sorted(self.data_cache.keys())[:-self.cache_size_limit//2]
            for key in oldest_keys:
                del self.data_cache[key]
                
        self.data_cache[cache_key] = processed
        return processed
    