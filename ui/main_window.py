import os
import pandas as pd
import sys
import logging
import time
from typing import List, Dict, Optional, Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QLabel, QComboBox, QPushButton, QGroupBox,
    QMessageBox,  QListWidget, QCheckBox,
     QApplication, 
    QListWidgetItem, QProgressBar, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer,  pyqtSignal, pyqtSlot



project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_dir)

import config
from utils.dssat_paths import get_crop_details, prepare_folders
from data.dssat_io import (
    prepare_experiment, prepare_treatment, prepare_out_files, 
    read_file, read_observed_data, read_evaluate_file,
    create_batch_file, run_treatment
)
from data.data_processing import (
    get_evaluate_variable_pairs, get_all_evaluate_variables
)
from ui.widgets.plot_widget import PlotWidget
from ui.widgets.status_widget import StatusWidget
from ui.widgets.data_table_widget import DataTableWidget
from ui.widgets.scatter_plot_widget import ScatterPlotWidget
from ui.widgets.metrics_table_widget import MetricsDialog, MetricsTableWidget

class MainWindow(QMainWindow):
    execution_completed = pyqtSignal(bool, str)
    data_loaded = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.execution_status = {"completed": False}
        self.selected_treatments = []
        self.selected_experiment = None
        self.selected_folder = None
        self.current_data = None
        self.time_series_metrics = []
        self.scatter_metrics = []
        self.current_metrics = []
        self._tab_content_loaded = {}
        self._data_needs_refresh = False
        self.setWindowTitle("DSSAT Viewer")
        self.setMinimumSize(1200, 800)

        # Make window resizable
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.status_widget = StatusWidget()
        self.statusBar().addPermanentWidget(self.status_widget, 1)
        self.setup_ui()
        
        # Allow child widgets to expand with the window
        self.central_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Ensure content_area can expand
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.setup_loading_indicator()
        self.connect_signals()
        self.initialize_data()
        self.update_ui_state()
        self.monkey_patch_plot_widgets()
        
    def monkey_patch_plot_widgets(self):
        if not hasattr(self.time_series_plot, 'begin_update'):
            def begin_update(self):
                if hasattr(self, 'plot_view'):
                    self.plot_view.setUpdatesEnabled(False)
            self.time_series_plot.begin_update = begin_update.__get__(self.time_series_plot)
        
        if not hasattr(self.time_series_plot, 'end_update'):
            def end_update(self):
                if hasattr(self, 'plot_view'):
                    self.plot_view.setUpdatesEnabled(True)
                    self.plot_view.updateGeometry()
            self.time_series_plot.end_update = end_update.__get__(self.time_series_plot)
        
        if not hasattr(self.scatter_plot, 'begin_update'):
            def begin_update(self):
                pass
            self.scatter_plot.begin_update = begin_update.__get__(self.scatter_plot)
        
        if not hasattr(self.scatter_plot, 'end_update'):
            def end_update(self):
                pass
            self.scatter_plot.end_update = end_update.__get__(self.scatter_plot)
    
    def setup_ui(self):
        # Set application-wide style with lighter colors
        self.setStyleSheet("""
            * { color: #000000; }  /* Make all text black */
            
            QMainWindow, QWidget {
                background-color: #F0F5F9;  /* Light blue-gray background */
            }
            QTabWidget::pane {
                border: 1px solid #E4E8ED;
                background-color: #F0F5F9;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background-color: #E4E8ED;
                border: 1px solid #C9D6DF;
                padding: 6px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #F0F5F9;
                border-bottom-color: white;
            }
            QComboBox, QListWidget {
                background-color: #F0F5F9;
                border: 1px solid #C9D6DF;
                border-radius: 3px;
                padding: 2px;
                selection-background-color: #A8D8F0;
            }
            QGroupBox {
                background-color: #F0F5F9;
                border: 1px solid #C9D6DF;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #F0F5F9;
            }
            QTableView {
                background-color: #F0F5F9;
                alternate-background-color: #F9FBFC;
                border: 1px solid #C9D6DF;
            }
            QScrollArea {
                background-color: transparent;
            }
            QPushButton {
                background-color: #52A7E0;  /* Sky blue */
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3D8BC7;
            }
            QPushButton:disabled {
                background-color: #C9D6DF;
            }
        """)
        
        # Rest of your code remains unchanged...
        
        self.central_widget = QWidget()
        self.central_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCentralWidget(self.central_widget)
        
        main_layout = QHBoxLayout()
        self.central_widget.setLayout(main_layout)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        sidebar_container = QWidget()
        sidebar_container_layout = QVBoxLayout()
        sidebar_container_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_container.setLayout(sidebar_container_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sidebar_container_layout.addWidget(scroll_area)
        
        self.sidebar = QWidget()
        sidebar_layout = QVBoxLayout()
        self.sidebar.setLayout(sidebar_layout)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        scroll_area.setWidget(self.sidebar)
        
        sidebar_container.setMinimumWidth(220)
        sidebar_container.setMaximumWidth(320)
        
        self.splitter.addWidget(sidebar_container)
        self.splitter.setSizes([270, 930])
        self.splitter.setHandleWidth(5)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #cccccc; }")
        
        self.setup_folder_selection(sidebar_layout)
        self.setup_experiment_selection(sidebar_layout)
        self.setup_treatment_selection(sidebar_layout)
        self.setup_run_controls(sidebar_layout)
        self.setup_visualization_controls(sidebar_layout)
        self.setup_metrics_button(sidebar_layout)
        sidebar_layout.addStretch(1)
        
        self.content_area = QTabWidget()
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.content_area.setDocumentMode(True)
        self.splitter.addWidget(self.content_area)
        
        # Set the stretch factors for the splitter
        self.splitter.setStretchFactor(0, 1)  # Sidebar
        self.splitter.setStretchFactor(1, 3)  # Content area
        
        self.time_series_tab = QWidget()
        time_series_layout = QVBoxLayout()
        self.time_series_tab.setLayout(time_series_layout)
        self.time_series_plot = PlotWidget()
        time_series_layout.addWidget(self.time_series_plot)
        
        self.scatter_tab = QWidget()
        scatter_layout = QVBoxLayout()
        self.scatter_tab.setLayout(scatter_layout)
        self.scatter_plot = ScatterPlotWidget()
        scatter_layout.addWidget(self.scatter_plot)
        
        self.data_tab = QWidget()
        data_layout = QVBoxLayout()
        self.data_tab.setLayout(data_layout)
        self.data_table = DataTableWidget()
        data_layout.addWidget(self.data_table)
        
        self.content_area.addTab(self.time_series_tab, "Time Series")
        self.content_area.addTab(self.scatter_tab, "Scatter Plot")
        self.content_area.addTab(self.data_tab, "Data View")
        self.content_area.currentChanged.connect(self.on_tab_changed)
    
    def setup_loading_indicator(self):
        self.loading_indicator = QWidget(self)
        layout = QVBoxLayout()
        self.loading_indicator.setLayout(layout)
        self.loading_progress = QProgressBar()
        self.loading_progress.setRange(0, 0)
        layout.addWidget(self.loading_progress)
        self.loading_label = QLabel("Loading tab content...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_label)
        self.loading_indicator.setStyleSheet("""
            background-color: rgba(255, 255, 255, 220);
            border: 1px solid #ccc;
            border-radius: 10px;
        """)
        self.loading_indicator.setFixedSize(200, 100)
        self.loading_indicator.hide()
        self.tab_switch_timer = QTimer()
        self.tab_switch_timer.setSingleShot(True)
        self.tab_switch_timer.timeout.connect(self._deferred_tab_load)
        self._current_tab_index = 0
        self._pending_tab_load = False
        
    def show_loading_indicator(self, visible=True):
        if visible:
            rect = self.content_area.currentWidget().geometry()
            self.loading_indicator.move(
                rect.x() + (rect.width() - self.loading_indicator.width()) // 2,
                rect.y() + (rect.height() - self.loading_indicator.height()) // 2
            )
            self.loading_indicator.raise_()
            self.loading_indicator.show()
            QApplication.processEvents()
        else:
            self.loading_indicator.hide()
    
    def setup_folder_selection(self, layout):
        group = QGroupBox("Select Crop")
        group_layout = QVBoxLayout()
        group.setLayout(group_layout)
        self.folder_selector = QComboBox()
        self.folder_selector.setToolTip("Select crop folder")
        group_layout.addWidget(self.folder_selector)
        layout.addWidget(group)
    
    def setup_experiment_selection(self, layout):
        group = QGroupBox("Select Experiment")
        group_layout = QVBoxLayout()
        group.setLayout(group_layout)
        self.experiment_selector = QComboBox()
        self.experiment_selector.setToolTip("Select experiment file")
        group_layout.addWidget(self.experiment_selector)
        layout.addWidget(group)
    
    def setup_treatment_selection(self, layout):
        group = QGroupBox("Select Treatments")
        group_layout = QVBoxLayout()
        group.setLayout(group_layout)
        self.treatment_list = QListWidget()
        self.treatment_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.treatment_list.setToolTip("Select one or more treatments")
        self.treatment_list.setMinimumHeight(70)
        self.treatment_list.setMaximumHeight(90)
        group_layout.addWidget(self.treatment_list)
        layout.addWidget(group)
    
    def setup_run_controls(self, layout):
        self.run_button = QPushButton("Run Treatment")
        self.run_button.setToolTip("Run selected treatment")
        self.run_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        layout.addWidget(self.run_button)
    
    def setup_visualization_controls(self, layout):
        file_group = QGroupBox("Output Files")
        file_layout = QVBoxLayout()
        file_group.setLayout(file_layout)
        self.out_file_selector = QListWidget()
        self.out_file_selector.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.out_file_selector.setMinimumHeight(60)
        self.out_file_selector.setMaximumHeight(80)
        file_layout.addWidget(self.out_file_selector)
        layout.addWidget(file_group)
        self.time_series_group = QGroupBox("Time Series Variables")
        ts_layout = QVBoxLayout()
        self.time_series_group.setLayout(ts_layout)
        ts_layout.addWidget(QLabel("X Variable"))
        self.x_var_selector = QComboBox()
        ts_layout.addWidget(self.x_var_selector)
        ts_layout.addWidget(QLabel("Y Variables"))
        self.y_var_selector = QListWidget()
        self.y_var_selector.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.y_var_selector.setMinimumHeight(120)
        ts_layout.addWidget(self.y_var_selector)
        layout.addWidget(self.time_series_group)
        self.scatter_group = QGroupBox("Scatter Plot Variables")
        scatter_layout = QVBoxLayout()
        self.scatter_group.setLayout(scatter_layout)
        self.sim_vs_meas_radio = QCheckBox("Simulated vs Measured (Auto)")
        self.sim_vs_meas_radio.setChecked(True)
        scatter_layout.addWidget(self.sim_vs_meas_radio)
        self.custom_xy_radio = QCheckBox("Custom X-Y Variables")
        scatter_layout.addWidget(self.custom_xy_radio)
        scatter_layout.addWidget(QLabel("Variables to Compare"))
        self.scatter_var_selector = QListWidget()
        self.scatter_var_selector.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.scatter_var_selector.setMinimumHeight(120)
        scatter_layout.addWidget(self.scatter_var_selector)
        scatter_layout.addWidget(QLabel("X Variable"))
        self.scatter_x_var_selector = QComboBox()
        scatter_layout.addWidget(self.scatter_x_var_selector)
        scatter_layout.addWidget(QLabel("Y Variables"))
        self.scatter_y_var_selector = QListWidget()
        self.scatter_y_var_selector.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.scatter_y_var_selector.setMinimumHeight(120)
        scatter_layout.addWidget(self.scatter_y_var_selector)
        layout.addWidget(self.scatter_group)
        self.refresh_button = QPushButton("Refresh Plot")
        self.refresh_button.setToolTip("Refresh the current plot")
        self.refresh_button.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px; }"
            "QPushButton:hover { background-color: #0b7dda; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        layout.addWidget(self.refresh_button)
        self.scatter_group.setVisible(False)
        self.file_group = file_group
    
    def setup_metrics_button(self, layout):
        self.metrics_button = QPushButton("Show Metrics")
        self.metrics_button.setToolTip("Show performance metrics")
        self.metrics_button.setStyleSheet(
            "QPushButton { background-color: #03A9F4; color: white; font-weight: bold; padding: 8px; }"
            "QPushButton:hover { background-color: #0288D1; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        layout.addWidget(self.metrics_button)
        
    def connect_signals(self):
        self.folder_selector.currentIndexChanged.connect(self.on_folder_changed)
        self.experiment_selector.currentIndexChanged.connect(self.on_experiment_changed)
        self.treatment_list.itemSelectionChanged.connect(self.on_treatment_selection_changed)
        self.run_button.clicked.connect(self.on_run_button_clicked)
        self.out_file_selector.itemSelectionChanged.connect(self.on_out_file_selection_changed)
        self.x_var_selector.currentIndexChanged.connect(self.on_variable_selection_changed)
        self.y_var_selector.itemSelectionChanged.connect(self.on_variable_selection_changed)
        self.sim_vs_meas_radio.toggled.connect(self.on_scatter_mode_changed)
        self.custom_xy_radio.toggled.connect(self.on_scatter_mode_changed)
        self.scatter_var_selector.itemSelectionChanged.connect(self.on_scatter_var_selection_changed)
        self.scatter_x_var_selector.currentIndexChanged.connect(self.on_scatter_var_selection_changed)
        self.scatter_y_var_selector.itemSelectionChanged.connect(self.on_scatter_var_selection_changed)
        self.refresh_button.clicked.connect(self.on_refresh_clicked)
        self.connect_metrics_signals()
        self.execution_completed.connect(self.on_execution_completed)
        self.data_loaded.connect(self.on_data_loaded)
    
    def connect_metrics_signals(self):
        self.metrics_button.clicked.connect(self.show_metrics_dialog)
        self.time_series_plot.metrics_calculated.connect(self.update_timeseries_metrics)
        self.scatter_plot.metrics_calculated.connect(self.update_scatter_metrics)
        self.content_area.currentChanged.connect(self.update_current_metrics)
        
    def initialize_data(self):
        self.load_folders()
    
    def update_ui_state(self):
        has_folder = self.selected_folder is not None
        has_experiment = self.selected_experiment is not None
        has_treatments = len(self.selected_treatments) > 0
        execution_complete = self.execution_status.get("completed", False)
        self.run_button.setEnabled(has_folder and has_experiment and has_treatments)
        self.time_series_group.setEnabled(execution_complete)
        self.scatter_group.setEnabled(execution_complete)
        self.refresh_button.setEnabled(execution_complete)
        current_tab = self.content_area.currentIndex()
        self.time_series_group.setVisible(current_tab == 0)
        self.scatter_group.setVisible(current_tab == 1)
        sim_vs_meas_selected = self.sim_vs_meas_radio.isChecked()
        custom_xy_selected = self.custom_xy_radio.isChecked()
        self.scatter_var_selector.setVisible(sim_vs_meas_selected)
        self.scatter_x_var_selector.setVisible(custom_xy_selected)
        self.scatter_y_var_selector.setVisible(custom_xy_selected)
        self.metrics_button.setEnabled(bool(self.current_metrics) and execution_complete)
    
    def load_folders(self):
        try:
            folders = prepare_folders()
            self.folder_selector.clear()
            for folder in folders:
                self.folder_selector.addItem(folder)
            if folders:
                self.folder_selector.setCurrentIndex(0)
        except Exception as e:
            logging.error(f"Error loading folders: {e}")
            self.show_error("Error loading crop folders", str(e))
    
    def load_experiments(self):
        try:
            if not self.selected_folder:
                return
            experiments = prepare_experiment(self.selected_folder)
            self.experiment_selector.clear()
            for exp_name, filename in experiments:
                self.experiment_selector.addItem(exp_name, userData=filename)
            if experiments:
                self.experiment_selector.setCurrentIndex(0)
        except Exception as e:
            logging.error(f"Error loading experiments: {e}")
            self.show_error("Error loading experiments", str(e))
    
    def load_treatments(self):
        try:
            if not self.selected_folder or not self.selected_experiment:
                return
            treatments = prepare_treatment(self.selected_folder, self.selected_experiment)
            self.treatment_list.clear()
            self.treatment_names = {}
            if treatments is not None and not treatments.empty:
                for _, row in treatments.iterrows():
                    self.treatment_names[row.TR] = row.TNAME
                    item = QListWidgetItem(f"{row.TR} - {row.TNAME}")
                    item.setData(Qt.ItemDataRole.UserRole, row.TR)
                    self.treatment_list.addItem(item)
                for i in range(self.treatment_list.count()):
                    self.treatment_list.item(i).setSelected(True)
        except Exception as e:
            logging.error(f"Error loading treatments: {e}")
            self.show_error("Error loading treatments", str(e))
        
    def load_output_files(self):
        try:
            if not self.selected_folder:
                return
            out_files = prepare_out_files(self.selected_folder)
            self.out_file_selector.clear()
            for file in out_files:
                self.out_file_selector.addItem(file)
            if "PlantGro.OUT" in out_files:
                for i in range(self.out_file_selector.count()):
                    if self.out_file_selector.item(i).text() == "PlantGro.OUT":
                        self.out_file_selector.item(i).setSelected(True)
            elif out_files:
                self.out_file_selector.item(0).setSelected(True)
        except Exception as e:
            logging.error(f"Error loading output files: {e}")
            self.show_error("Error loading output files", str(e))
    
    def load_variables(self):
        try:
            selected_files = [item.text() for item in 
                            self.out_file_selector.selectedItems()]
            
            if not self.selected_folder or not selected_files:
                return
            crop_details = get_crop_details()
            crop_info = next(
                (crop for crop in crop_details 
                if crop['name'].upper() == self.selected_folder.upper()),
                None
            )
            if not crop_info:
                return
            all_columns = set()
            for out_file in selected_files:
                file_path = os.path.join(crop_info['directory'], out_file)
                data = read_file(file_path)
                if data is not None and not data.empty:
                    all_columns.update(
                        col for col in data.columns 
                        if col not in ["TRT", "FILEX"]
                    )
            from data.data_processing import get_variable_info
            self.x_var_selector.clear()
            for col in sorted(all_columns):
                var_label, _ = get_variable_info(col)
                display_text = f"{var_label} ({col})" if var_label else col
                self.x_var_selector.addItem(display_text, userData=col)
            if "DATE" in all_columns:
                for i in range(self.x_var_selector.count()):
                    if self.x_var_selector.itemData(i) == "DATE":
                        self.x_var_selector.setCurrentIndex(i)
                        break
            self.y_var_selector.clear()
            for col in sorted(all_columns):
                var_label, _ = get_variable_info(col)
                display_text = f"{var_label} ({col})" if var_label else col
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, col)
                self.y_var_selector.addItem(item)
            if "CWAD" in all_columns:
                for i in range(self.y_var_selector.count()):
                    if self.y_var_selector.item(i).data(Qt.ItemDataRole.UserRole) == "CWAD":
                        self.y_var_selector.item(i).setSelected(True)
                        break
            elif all_columns:
                self.y_var_selector.item(0).setSelected(True)
        except Exception as e:
            logging.error(f"Error loading variables: {e}")
            self.show_error("Error loading variables", str(e))
            
    def load_scatter_variables(self):
        try:
            if not self.selected_folder:
                logging.warning("No folder selected for loading scatter variables")
                return
            logging.info(f"Loading scatter variables for folder: {self.selected_folder}")
            crop_details = get_crop_details()
            crop_info = next(
                (crop for crop in crop_details 
                if crop['name'].upper() == self.selected_folder.upper()),
                None
            )
            if not crop_info:
                logging.error(f"Could not find crop info for: {self.selected_folder}")
                self.populate_default_scatter_variables()
                return
            folder_path = crop_info['directory'].strip()
            evaluate_path = os.path.join(folder_path, "EVALUATE.OUT")
            logging.info(f"Looking for EVALUATE.OUT at: {evaluate_path}")
            if not os.path.exists(evaluate_path):
                logging.warning(f"EVALUATE.OUT not found at: {evaluate_path}")
                self.populate_default_scatter_variables()
                return
            evaluate_data = read_evaluate_file(self.selected_folder)
            if evaluate_data is None or evaluate_data.empty:
                logging.warning(f"No evaluate data available for folder: {self.selected_folder}")
                self.populate_default_scatter_variables()
                return
            logging.info(f"Successfully loaded evaluate data with {len(evaluate_data)} rows")
            var_pairs = get_evaluate_variable_pairs(evaluate_data)
            logging.info(f"Found {len(var_pairs)} variable pairs")
            self.scatter_var_selector.clear()
            for display_name, sim_var, meas_var in var_pairs:
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, (display_name, sim_var, meas_var))
                self.scatter_var_selector.addItem(item)
                logging.info(f"Added auto-pair: {display_name} ({sim_var} vs {meas_var})")
            if self.scatter_var_selector.count() > 0:
                self.scatter_var_selector.item(0).setSelected(True)
                logging.info(f"Selected default auto-pair: {self.scatter_var_selector.item(0).text()}")
            all_vars = get_all_evaluate_variables(evaluate_data)
            logging.info(f"Found {len(all_vars)} total variables")
            self.scatter_x_var_selector.clear()
            for display_name, var_name in all_vars:
                self.scatter_x_var_selector.addItem(display_name, userData=var_name)
            self.scatter_y_var_selector.clear()
            for display_name, var_name in all_vars:
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, var_name)
                self.scatter_y_var_selector.addItem(item)
            if self.scatter_y_var_selector.count() > 0:
                self.scatter_y_var_selector.item(0).setSelected(True)
        except Exception as e:
            logging.error(f"Error loading scatter variables: {e}", exc_info=True)
            self.populate_default_scatter_variables()

    def populate_default_scatter_variables(self):
        logging.warning("Populating default scatter variables")
        self.scatter_var_selector.clear()
        default_vars = ["LAI", "GSAT", "HWAH"]
        for var in default_vars:
            item = QListWidgetItem(var)
            item.setData(Qt.ItemDataRole.UserRole, (var, f"{var}S", f"{var}M"))
            self.scatter_var_selector.addItem(item)
        if self.scatter_var_selector.count() > 0:
            self.scatter_var_selector.item(0).setSelected(True)
        self.scatter_x_var_selector.clear()
        self.scatter_y_var_selector.clear()
        for var in default_vars:
            self.scatter_x_var_selector.addItem(var, userData=var)
            item = QListWidgetItem(var)
            item.setData(Qt.ItemDataRole.UserRole, var)
            self.scatter_y_var_selector.addItem(item)
        if self.scatter_y_var_selector.count() > 0:
            self.scatter_y_var_selector.item(0).setSelected(True)

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)
    
    def show_success(self, message):
        self.status_widget.show_success(message)
    
    def show_warning(self, message):
        self.status_widget.show_warning(message)
    
    def mark_data_needs_refresh(self):
        self._data_needs_refresh = True
        self._tab_content_loaded = {}
    
    @pyqtSlot()
    def on_folder_changed(self):
        self.selected_folder = self.folder_selector.currentText()
        self.load_experiments()
        self.execution_status = {"completed": False}
        self.show_warning("Please run treatment to update visualizations")
        self.mark_data_needs_refresh()
        self.update_ui_state()
    
    @pyqtSlot()
    def on_experiment_changed(self):
        index = self.experiment_selector.currentIndex()
        if index >= 0:
            self.selected_experiment = self.experiment_selector.itemData(index)
            if not self.selected_experiment:
                self.selected_experiment = self.experiment_selector.currentText()
            self.load_treatments()
            self.execution_status = {"completed": False}
            self.show_warning("Please run treatment to update visualizations")
            self.mark_data_needs_refresh()
            self.update_ui_state()
    
    @pyqtSlot()
    def on_treatment_selection_changed(self):
        self.selected_treatments = []
        for item in self.treatment_list.selectedItems():
            trt_str = item.text().split(' - ')[0]
            self.selected_treatments.append(trt_str)
        self.update_ui_state()
    
    @pyqtSlot()
    def on_run_button_clicked(self):
        if not all([self.selected_folder, self.selected_treatments, self.selected_experiment]):
            self.show_error("Missing selections", "Please select crop, experiment, and treatments")
            return
        try:
            self.status_widget.show_running("Running treatment...")
            self.run_button.setEnabled(False)
            from PyQt6.QtCore import QThread
            class WorkerThread(QThread):
                result_signal = pyqtSignal(bool, str)
                def __init__(self, parent, input_data, dssat_base):
                    super().__init__(parent)
                    self.input_data = input_data
                    self.dssat_base = dssat_base
                def run(self):
                    try:
                        batch_file_path = create_batch_file(self.input_data, self.dssat_base)
                        run_treatment(self.input_data, self.dssat_base)
                        treatment_str = (
                            ", ".join(str(t) for t in self.input_data["treatment"])
                            if isinstance(self.input_data["treatment"], list)
                            else str(self.input_data["treatment"])
                        )
                        success_msg = f"Treatment(s) {treatment_str} executed successfully!"
                        self.result_signal.emit(True, success_msg)
                    except Exception as e:
                        error_msg = f"Error executing treatment: {str(e)}"
                        self.result_signal.emit(False, error_msg)
            input_data = {
                "folders": self.selected_folder,
                "executables": config.DSSAT_EXE,
                "experiment": self.selected_experiment,
                "treatment": self.selected_treatments,
            }
            self.worker_thread = WorkerThread(self, input_data, config.DSSAT_BASE)
            self.worker_thread.result_signal.connect(self.handle_execution_completed)
            self.worker_thread.start()
        except Exception as e:
            self.run_button.setEnabled(True)
            self.status_widget.clear()
            self.show_error("Error executing treatment", str(e))
    
    @pyqtSlot(bool, str)
    def handle_execution_completed(self, success, message):
        self.execution_completed.emit(success, message)
    
    @pyqtSlot(bool, str)
    def on_execution_completed(self, success, message):
        self.run_button.setEnabled(True)
        self.status_widget.clear()
        if success:
            self.execution_status = {"completed": True}
            self.show_success(message)
            self.load_output_files()
            self.load_variables()
            self.load_scatter_variables()
            self.mark_data_needs_refresh()
            self.update_ui_state()
            self.on_refresh_clicked()
            self._tab_content_loaded[self.content_area.currentIndex()] = True
        else:
            self.show_error("Execution Error", message)
    
    @pyqtSlot()
    def on_out_file_selection_changed(self):
        self.load_variables()
        self.mark_data_needs_refresh()
    
    @pyqtSlot()
    def on_variable_selection_changed(self):
        if self.content_area.currentIndex() in self._tab_content_loaded:
            self._tab_content_loaded.pop(self.content_area.currentIndex())
    
    @pyqtSlot()
    def on_refresh_clicked(self):
        current_tab = self.content_area.currentIndex()
        self.show_loading_indicator(True)
        try:
            self.setUpdatesEnabled(False)
            if current_tab == 0:
                self.update_time_series_plot()
            elif current_tab == 1:
                self.update_scatter_plot()
            elif current_tab == 2:
                self.update_data_table()
            self._tab_content_loaded[current_tab] = True
        finally:
            self.setUpdatesEnabled(True)
            self.show_loading_indicator(False)
            self.repaint()
    
    @pyqtSlot(int)
    def on_tab_changed(self, index):
        self._current_tab_index = index
        old_tab = self.content_area.currentWidget()
        self.update_ui_state()
        if hasattr(self, 'file_group'):
            self.file_group.setVisible(index != 1)
        self.update_current_metrics(index)
        if self.execution_status.get("completed", False):
            if index not in self._tab_content_loaded or self._data_needs_refresh:
                self._pending_tab_load = True
                self.show_loading_indicator(True)
                self.tab_switch_timer.start(10)
            else:
                if index == 0:
                    self.time_series_plot.update()
                elif index == 1:
                    self.scatter_plot.update()
                elif index == 2:
                    self.data_table.update()
    
    def _deferred_tab_load(self):
        index = self._current_tab_index
        needs_loading = True
        try:
            start_time = time.time()
            self.setUpdatesEnabled(False)
            if index == 0:
                self.update_time_series_plot()
            elif index == 1:
                self.update_scatter_plot()
            elif index == 2:
                self.update_data_table()
            self._tab_content_loaded[index] = True
            if all(i in self._tab_content_loaded for i in range(self.content_area.count())):
                self._data_needs_refresh = False
            loading_time = time.time() - start_time
            logging.info(f"Tab {index} loaded in {loading_time:.3f} seconds")
        except Exception as e:
            logging.error(f"Error loading tab {index}: {e}", exc_info=True)
        finally:
            self.setUpdatesEnabled(True)
            self.show_loading_indicator(False)
            self.repaint()
            self._pending_tab_load = False
    
    @pyqtSlot(bool)
    def on_scatter_mode_changed(self, checked):
        if self.sender() == self.sim_vs_meas_radio and checked:
            self.custom_xy_radio.setChecked(False)
        elif self.sender() == self.custom_xy_radio and checked:
            self.sim_vs_meas_radio.setChecked(False)
        self.update_ui_state()
        if 1 in self._tab_content_loaded:
            self._tab_content_loaded.pop(1)
    
    @pyqtSlot()
    def on_scatter_var_selection_changed(self):
        if 1 in self._tab_content_loaded:
            self._tab_content_loaded.pop(1)
    
    @pyqtSlot(dict)
    def on_data_loaded(self, data):
        self.current_data = data
        self.update_ui_state()
    
    def update_timeseries_metrics(self, metrics_data):
        self.time_series_metrics = metrics_data
        if self.content_area.currentIndex() == 0:
            self.current_metrics = self.time_series_metrics
            self.metrics_button.setEnabled(bool(self.current_metrics))

    def update_scatter_metrics(self, metrics_data):
        self.scatter_metrics = metrics_data
        if self.content_area.currentIndex() == 1:
            self.current_metrics = self.scatter_metrics
            self.metrics_button.setEnabled(bool(self.current_metrics))

    def update_current_metrics(self, tab_index):
        if tab_index == 0:
            self.current_metrics = self.time_series_metrics
        elif tab_index == 1:
            self.current_metrics = self.scatter_metrics
        else:
            self.current_metrics = []
        self.metrics_button.setEnabled(bool(self.current_metrics) and self.execution_status.get("completed", False))

    def show_metrics_dialog(self):
        if not self.current_metrics:
            self.status_widget.show_warning("No metrics data available for current view")
            return
        dialog = MetricsDialog(self.current_metrics, self)
        dialog.exec()  # Note: In PyQt6, exec() doesn't have parentheses
    
    def update_time_series_plot(self):
        try:
            if not self.execution_status.get("completed", False):
                return
            selected_files = [item.text() for item in self.out_file_selector.selectedItems()]
            if not selected_files:
                return
            x_var = self.x_var_selector.currentData()
            if not x_var:
                x_var = self.x_var_selector.currentText()
            y_vars = []
            for item in self.y_var_selector.selectedItems():
                var_code = item.data(Qt.ItemDataRole.UserRole)
                if var_code:
                    y_vars.append(var_code)
                else:
                    y_vars.append(item.text())
            if not x_var or not y_vars:
                return
            self.time_series_plot.plot_time_series(
                self.selected_folder,
                selected_files,
                self.selected_experiment,
                self.selected_treatments,
                x_var,
                y_vars,
                self.treatment_names
            )
            self.update_data_table()
        except Exception as e:
            logging.error(f"Error updating time series plot: {e}")
            self.show_error("Error updating plot", str(e))
    
    def update_scatter_plot(self):
        try:
            if not self.execution_status.get("completed", False):
                return
            sim_vs_meas_mode = self.sim_vs_meas_radio.isChecked()
            if sim_vs_meas_mode:
                selected_items = self.scatter_var_selector.selectedItems()
                if not selected_items:
                    return
                selected_vars = []
                for item in selected_items:
                    var_info = item.data(Qt.ItemDataRole.UserRole)
                    if var_info:
                        selected_vars.append(var_info)
                    else:
                        selected_vars.append(item.text())
                if not selected_vars:
                    return
                logging.info(f"Plotting {len(selected_vars)} scatter variable pairs")
                self.scatter_plot.plot_sim_vs_meas(
                    self.selected_folder,
                    self.selected_treatments,
                    selected_vars,
                    self.treatment_names 
                )
            else:
                x_var = self.scatter_x_var_selector.currentData()
                if not x_var:
                    x_var = self.scatter_x_var_selector.currentText()
                selected_items = self.scatter_y_var_selector.selectedItems()
                if not selected_items:
                    return
                y_vars = []
                for item in selected_items:
                    var_name = item.data(Qt.ItemDataRole.UserRole)
                    if var_name:
                        y_vars.append(var_name)
                    else:
                        y_vars.append(item.text())
                if not x_var or not y_vars:
                    return
                logging.info(f"Plotting custom scatter: {x_var} vs {y_vars}")
                self.scatter_plot.plot_custom_scatter(
                    self.selected_folder,
                    self.selected_treatments,
                    x_var,
                    y_vars
                )
        except Exception as e:
            logging.error(f"Error updating scatter plot: {e}", exc_info=True)
            self.show_error("Error updating scatter plot", str(e))
    
    def update_data_table(self):
        try:
            if not self.execution_status.get("completed", False):
                return
            selected_files = [item.text() for item in self.out_file_selector.selectedItems()]
            if not selected_files:
                return
            all_data = []
            for out_file in selected_files:
                crop_details = get_crop_details()
                crop_info = next(
                    (crop for crop in crop_details 
                    if crop['name'].upper() == self.selected_folder.upper()),
                    None
                )
                if not crop_info:
                    continue
                file_path = os.path.join(crop_info['directory'], out_file)
                file_data = read_file(file_path)
                if file_data is not None and not file_data.empty:
                    file_data['FILE'] = out_file
                    all_data.append(file_data)
            if all_data:
                combined_data = pd.concat(all_data, ignore_index=True)
                filtered_data = combined_data[combined_data['TRT'].isin(self.selected_treatments)]
                self.data_table.set_data(filtered_data)
            else:
                self.data_table.clear()
        except Exception as e:
            logging.error(f"Error updating data table: {e}")
            self.show_error("Error updating data table", str(e))
            
    def closeEvent(self, event):
        event.accept()