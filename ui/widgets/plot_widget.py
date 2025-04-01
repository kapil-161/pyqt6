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
        # Cache commonly used values
        self.variable_info_cache = {}
        self.date_cache = {}
        self.treatment_display_cache = {}
        
        # Set size policy for proper resizing
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Initialize
        self.setup_ui()
        
        # Store data
        self.sim_data = None
        self.obs_data = None
        self.scaling_factors = {}
        
        # Create color and line style cycles
        self.colors = config.PLOT_COLORS
        self.line_styles = config.LINE_STYLES
        self.marker_symbols = config.MARKER_SYMBOLS
        
    def setup_ui(self):
        """Setup the UI components"""
        # Main layout - horizontal layout with plot and legend
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)  # Add some padding
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
        
        # Right side - legend container
        # Create a scroll area
        legend_scroll_area = QScrollArea()
        legend_scroll_area.setWidgetResizable(True)
        legend_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        legend_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        legend_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Create the legend container as the content of the scroll area
        self.legend_container = QWidget()
        self.legend_layout = QVBoxLayout()
        self.legend_container.setLayout(self.legend_layout)
        
        # Set the legend container as the widget for the scroll area
        legend_scroll_area.setWidget(self.legend_container)
        
        # Add the scroll area to the main layout
        main_layout.addWidget(legend_scroll_area, 20)
        
        # Set initial size for legend scroll area
        legend_scroll_area.setMinimumWidth(180)
        legend_scroll_area.setMaximumWidth(220)
        
        # Enable auto-range on resize
        self.plot_view.enableAutoRange()
        
        # Connect resize event
        self.resizeEvent = self.on_resize
        
    def on_resize(self, event):
        # Update plots when resized
        if hasattr(self, 'plot_view'):
            self.plot_view.updateGeometry()
            # If you have data loaded, re-autoscale
            if self.sim_data is not None:
                self.plot_view.autoRange()
    
    def plot_time_series(self, selected_folder, selected_out_files, selected_experiment, 
                        selected_treatments, x_var, y_vars, treatment_names=None):
        """
        Create time series plot with simulation and observed data
        
        Args:
            selected_folder: Selected crop folder
            selected_out_files: Selected output files
            selected_experiment: Selected experiment
            selected_treatments: Selected treatments
            x_var: X-axis variable
            y_vars: Y-axis variables
            treatment_names: Dictionary mapping treatment numbers to names
        """
        # Vectorized date conversion
        def batch_date_convert(df):
            if 'YEAR' in df.columns and 'DOY' in df.columns:
                df['DATE'] = pd.to_datetime(
                    df['YEAR'].astype(str) + df['DOY'].astype(str).str.zfill(3), 
                    format='%Y%j'
                )
            return df

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

        # Clear previous plot
        self.plot_view.clear()
        
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
        
        # Scale data for visualization
        sim_scaling_factors = {}
        for var in y_vars:
            if var in sim_data.columns:
                sim_values = (
                    pd.to_numeric(sim_data[var], errors="coerce")
                    .dropna()
                    .values
                )
                if len(sim_values) > 0:
                    var_min, var_max = np.min(sim_values), np.max(sim_values)

                    if np.isclose(var_min, var_max):
                        midpoint = (10000 + 1000) / 2
                        sim_scaling_factors[var] = (1, midpoint)
                    else:
                        scale_factor = (10000 - 1000) / (var_max - var_min)
                        offset = 1000 - var_min * scale_factor
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
        
        # Create scaling text with improved formatting
        scaling_parts = []
        for var, (scale_factor, offset) in sim_scaling_factors.items():
            var_label, _ = get_variable_info(var)
            display_name = var_label or var
            scaling_parts.append(
                f"{display_name} = {round(scale_factor, 6):.6f} * {display_name} + {round(offset, 2):.2f}"
            )
        
        # Always use line breaks between variables
        scaling_html = "<br>".join(scaling_parts)
        self.scaling_label.setText(scaling_html)
        self.scaling_label.setWordWrap(True)  # Enable word wrapping
        
        # Set plot title and labels
        self.plot_view.setTitle("")
        x_label, _ = get_variable_info(x_var)
        x_display = x_label or x_var
        self.plot_view.setLabel('bottom', text=x_display, **{
            'color': '#000000',  # Black color
            'font-weight': 'bold',
            'font-size': '12pt'
        })
        
        # Set y-axis label (combined if multiple)
        y_axis_label = ", ".join(
            get_variable_info(var)[0] or var
            for var in y_vars
            if var in sim_data.columns
        )
        self.plot_view.setLabel('left', text=y_axis_label, **{
            'color': '#0066CC',  # Blue color
            'font-weight': 'bold',
        })
        
        # Create custom Qt legend in the legend container widget
        legend_label = QLabel("<b>Legend</b>")
        legend_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.legend_layout.addWidget(legend_label)
        
        # Storage for our legend entries
        legend_entries = {
            "Simulated": {},
            "Observed": {}
        }
        
        # Plot the data and collect items for legend
        line_styles = [Qt.PenStyle.SolidLine, Qt.PenStyle.DashLine, Qt.PenStyle.DotLine, Qt.PenStyle.DashDotLine]
        pen_width = 2
        
        # For each treatment and variable, add a line/points
        for dataset in [sim_data, obs_data]:
            if dataset is not None and not dataset.empty:
                # Determine if this is simulated or observed data
                source_type = dataset["source"].iloc[0]
                category = "Simulated" if source_type == "sim" else "Observed"
                
                # Process each variable
                for var_idx, var in enumerate(y_vars):
                    # Initialize storage for this variable if not already created
                    var_label, _ = get_variable_info(var)
                    display_name = var_label or var
                    
                    if display_name not in legend_entries[category]:
                        legend_entries[category][display_name] = []
                    
                    # Process each treatment
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
                            # Select color and style
                            color_idx = trt_idx % len(self.colors)
                            style_idx = var_idx % len(line_styles)
                            color = self.colors[color_idx]
                            qt_color = pg.mkColor(color)
                            
                            if source_type == "sim":
                                # Simulated data as line
                                pen = pg.mkPen(
                                    color=qt_color, 
                                    width=pen_width, 
                                    style=line_styles[style_idx]
                                )
                                
                                # Get valid x and y values
                                valid_mask = group[var].notna()
                                x_values = group[valid_mask][x_var].values
                                y_values = group[valid_mask][var].values
                                
                                # Try to convert to datetime for proper display
                                try:
                                    if x_var == "DATE":
                                        x_dates = pd.to_datetime(x_values)
                                        # Convert to numeric timestamp for plotting
                                        x_values = [d.timestamp() for d in x_dates]
                                except Exception as e:
                                    logger.warning(f"Error converting dates: {e}")
                                    
                                #x_values = np.array(x_values, dtype=np.float64)
                                y_values = np.array(y_values, dtype=np.float64)
                                
                                # Add line to plot
                                curve = self.plot_view.plot(
                                    x_values, y_values, 
                                    pen=pen,
                                    name=None  # No automatic legend
                                )
                                
                                # Save for legend
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
                                
                                # Get valid x and y values
                                valid_mask = group[var].notna()
                                x_values = group[valid_mask][x_var].values
                                y_values = group[valid_mask][var].values
                                
                                # Try to convert to datetime for proper display
                                try:
                                    if x_var == "DATE":
                                        x_dates = pd.to_datetime(x_values)
                                        # Convert to numeric timestamp for plotting
                                        x_values = [d.timestamp() for d in x_dates]
                                except Exception as e:
                                    logger.warning(f"Error converting dates: {e}")
                                
                                # Create symbol with or without border for more variations
                                symbol_pen = None
                                if (var_idx + trt_idx) % 2 == 0:  # Add borders for some combinations
                                    symbol_pen = pg.mkPen(qt_color, width=1)
                                
                                # Add scatter points to plot
                                scatter = pg.ScatterPlotItem(
                                    x=x_values, y=y_values,
                                    symbol=symbol,
                                    size=8,  # Fixed size
                                    pen=symbol_pen, brush=qt_color,
                                    name=None  # No automatic legend
                                )
                                self.plot_view.addItem(scatter)
                                
                                # Save for legend
                                legend_entries[category][display_name].append({
                                    "item": scatter,
                                    "name": trt_display,
                                    "trt": trt_value,
                                    "brush": qt_color,
                                    "pen": symbol_pen,
                                    "symbol": symbol
                                })
        
        # Build the custom legend in the sidebar widget
        for category in ["Simulated", "Observed"]:
            if legend_entries[category]:
                # Add category header
                category_label = QLabel(f"<b>--- {category} ---</b>")
                category_label.setStyleSheet("margin-top: 10px;")
                self.legend_layout.addWidget(category_label)
                
                # Add variables and treatments under each category
                for var_name, treatments in sorted(legend_entries[category].items()):
                    # Add variable name as subheader
                    var_label = QLabel(f"<b>{var_name}</b>")
                    var_label.setStyleSheet("margin-top: 5px; margin-left: 10px;")
                    self.legend_layout.addWidget(var_label)
                    
                    # Add treatments under this variable
                    for treatment in sorted(treatments, key=lambda x: x["trt"]):
                        trt_name = treatment["name"]
                        
                        # Create a custom legend entry using PyQtGraph's sample plotter
                        sample_widget = pg.PlotWidget(background=None)
                        sample_widget.setFixedHeight(20)
                        sample_widget.setFixedWidth(50)
                        sample_widget.hideAxis('left')
                        sample_widget.hideAxis('bottom')
                        sample_widget.setMouseEnabled(False, False)
                        
                        # Add the same kind of plot item
                        if "symbol" in treatment and treatment["symbol"] is not None:
                            # For scatter points
                            sample = pg.ScatterPlotItem(
                                x=[0.5], y=[0.5],
                                symbol=treatment["symbol"],
                                size=8,
                                pen=treatment["pen"],
                                brush=treatment["brush"]
                            )
                            sample_widget.addItem(sample)
                        else:
                            # For line plots
                            sample = pg.PlotDataItem(
                                x=[0, 1], y=[0.5, 0.5],
                                pen=treatment["pen"]
                            )
                            sample_widget.addItem(sample)
                        
                        # Entry layout with sample and label
                        entry_widget = QWidget()
                        entry_layout = QHBoxLayout()
                        entry_layout.setContentsMargins(15, 0, 0, 0)
                        entry_widget.setLayout(entry_layout)
                        
                        # Add sample and label to entry
                        entry_layout.addWidget(sample_widget)
                        entry_layout.addWidget(QLabel(trt_name))
                        entry_layout.addStretch(1)
                        
                        # Add entry to legend
                        self.legend_layout.addWidget(entry_widget)
        
        # Add stretch to push legend entries to the top
        self.legend_layout.addStretch(1)
        
        # Set nice axis formatting for dates
        if x_var == "DATE":
            date_axis = pg.DateAxisItem(orientation='bottom')
            date_axis.setLabel(text="Date", **{ 'color': '#000000', 'font-weight': 'bold'})
            self.plot_view.setAxisItems({'bottom': date_axis})
            
        # Enable auto-ranging and show grids
        self.plot_view.enableAutoRange()
        self.plot_view.showGrid(x=True, y=True)
        
        # Update the view
        self.plot_view.updateGeometry()
        
        # Calculate and emit metrics if we have observed data
        if obs_data is not None and not obs_data.empty:
            self.calculate_metrics(sim_data, obs_data, y_vars, selected_treatments, treatment_names)
            
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
        if obs_data is None or obs_data.empty:
            return
            
        metrics_data = []
        
        # For each treatment and variable, calculate metrics
        for var in y_vars:
            if var not in sim_data.columns or var not in obs_data.columns:
                continue
                
            for trt in selected_treatments:
                try:
                    # Get data for this treatment
                    sim_trt_data = sim_data[sim_data['TRT'] == trt]
                    obs_trt_data = obs_data[obs_data['TRT'] == trt]
                    
                    if sim_trt_data.empty or obs_trt_data.empty:
                        continue
                        
                    # Find common dates
                    common_dates = set(sim_trt_data['DATE']) & set(obs_trt_data['DATE'])
                    if not common_dates:
                        continue
                        
                    # Filter to common dates
                    sim_values = []
                    obs_values = []
                    
                    for date in common_dates:
                        try:
                            sim_val = sim_trt_data[sim_trt_data['DATE'] == date][f"{var}_original"].values
                            obs_val = obs_trt_data[obs_trt_data['DATE'] == date][f"{var}_original"].values
                            
                            if len(sim_val) > 0 and len(obs_val) > 0:
                                # Skip NA/NaN values
                                if pd.isna(sim_val[0]) or pd.isna(obs_val[0]):
                                    continue
                                    
                                sim_values.append(float(sim_val[0]))
                                obs_values.append(float(obs_val[0]))
                        except Exception as e:
                            logger.warning(f"Error processing date {date}: {e}")
                            continue
                    
                    if len(sim_values) < 2 or len(obs_values) < 2:
                        # Skip if not enough valid data points
                        metrics_data.append({
                            "Variable": f"{var} - Treatment {trt}",
                            "n": len(sim_values),
                            "R²": 0.0,  # Not applicable for insufficient points
                            "RMSE": 0.0,
                            "d-stat": 0.0,
                        })
                        continue
                    trt_name = trt
                    if treatment_names and trt in treatment_names:
                        trt_name = treatment_names[trt]   
                    # Calculate metrics
                    var_label, _ = get_variable_info(var)
                    display_name = var_label or var
                    
                    try:
                        # Calculate R-squared manually
                        sim_vals = np.array(sim_values, dtype=float)
                        obs_vals = np.array(obs_values, dtype=float)
                        
                        sim_mean = np.mean(sim_vals)
                        obs_mean = np.mean(obs_vals)
                        
                        numerator = np.sum((sim_vals - sim_mean) * (obs_vals - obs_mean))
                        denom1 = np.sum((sim_vals - sim_mean)**2)
                        denom2 = np.sum((obs_vals - obs_mean)**2)
                        
                        # Check for zero denominator explicitly
                        if denom1 > 0 and denom2 > 0:
                            denominator = np.sqrt(denom1 * denom2)
                            r = numerator / denominator
                            r2 = r**2
                        else:
                            r2 = 0.0
                        
                        # Calculate RMSE
                        rmse = np.sqrt(np.mean((obs_vals - sim_vals)**2))
                        
                        # Calculate d-stat
                        obs_mean = np.mean(obs_vals)
                        numerator_d = np.sum((obs_vals - sim_vals) ** 2)
                        denom_d = np.sum((np.abs(sim_vals - obs_mean) + np.abs(obs_vals - obs_mean)) ** 2)
                        
                        if denom_d > 0:
                            d_stat_val = 1 - (numerator_d / denom_d)
                        else:
                            d_stat_val = 0.0
                        
                        # Add to metrics data
                        metrics_data.append({
                            "Variable": f"{display_name} - {trt_name}",  # Use treatment name instead of "Treatment X"
                            "n": len(sim_values),
                            #"R²": round(r2, 3),
                            "RMSE": round(rmse, 3),
                            "d-stat": round(d_stat_val, 3),
                        })
                    except Exception as e:
                        # ... [error handling] ...
                        # Add placeholder metrics with treatment name
                        var_label, _ = get_variable_info(var)
                        display_name = var_label or var
                        
                        trt_name = trt
                        if treatment_names and trt in treatment_names:
                            trt_name = treatment_names[trt]
                            
                        metrics_data.append({
                            "Variable": f"{display_name} - {trt_name}",
                            "n": len(sim_values),
                            "R²": 0.0,
                            "RMSE": 0.0,
                            "d-stat": 0.0,
                        })
                except Exception as e:
                    logger.error(f"Error processing treatment {trt} for variable {var}: {e}", exc_info=True)
                    continue
        
        # Emit signal if we have metrics
        if metrics_data:
            self.metrics_calculated.emit(metrics_data)
            
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