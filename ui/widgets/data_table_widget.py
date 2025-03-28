"""
Data Table Widget for DSSAT Viewer
Provides tabular view of DSSAT output data
"""
import os
import sys
import logging
from typing import  Any
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QHeaderView,
    QPushButton, QHBoxLayout, QFileDialog, QGroupBox, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, QAbstractTableModel, pyqtSlot


# Add project root to path
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_dir)

# Configure logging
logger = logging.getLogger(__name__)

class PandasTableModel(QAbstractTableModel):
    """Table model for pandas DataFrame to display in QTableView"""
    
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data.index)

    def columnCount(self, parent=None):
        return len(self._data.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            # Format based on data type
            if pd.isna(value):
                return "NA"
            elif isinstance(value, (float, np.float64)):
                return f"{value:.4f}"
            elif isinstance(value, (int, np.int64)):
                return str(value)
            else:
                return str(value)
                
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            else:
                return str(self._data.index[section])
        return None
    
    def sort(self, column, order):
        """Sort table by given column number"""
        self.layoutAboutToBeChanged.emit()
        col_name = self._data.columns[column]
        self._data = self._data.sort_values(
            col_name, 
            ascending=(order == Qt.SortOrder.AscendingOrder)
        )
        self.layoutChanged.emit()


class DataTableWidget(QWidget):
    """
    Widget for displaying tabular data from DSSAT outputs
    
    Features include:
    - Display data in a sortable, filterable table
    - Export data to CSV/Excel
    - Filter by treatment, variable, etc.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        # Store data
        self._data = None
        self._filtered_data = None
    
    def setup_ui(self):
        """Setup the UI components"""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Export button
        self.export_button = QPushButton("Export Data")
        self.export_button.setToolTip("Export table to CSV/Excel")
        controls_layout.addWidget(self.export_button)
        
        # Filter controls
        filter_group = QGroupBox("Filter")
        filter_layout = QHBoxLayout()
        filter_group.setLayout(filter_layout)
        
        self.filter_column = QComboBox()
        filter_layout.addWidget(QLabel("Column:"))
        filter_layout.addWidget(self.filter_column)
        
        self.filter_value = QComboBox()
        self.filter_value.setEditable(True)
        filter_layout.addWidget(QLabel("Value:"))
        filter_layout.addWidget(self.filter_value)
        
        self.apply_filter_button = QPushButton("Apply")
        filter_layout.addWidget(self.apply_filter_button)
        
        self.clear_filter_button = QPushButton("Clear")
        filter_layout.addWidget(self.clear_filter_button)
        
        controls_layout.addWidget(filter_group)
        
        # Add controls to main layout
        layout.addLayout(controls_layout)
        
        # Table view
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setVisible(True)
        layout.addWidget(self.table_view)
        
        # Connect signals
        self.export_button.clicked.connect(self.export_data)
        self.apply_filter_button.clicked.connect(self.apply_filter)
        self.clear_filter_button.clicked.connect(self.clear_filter)
        self.filter_column.currentIndexChanged.connect(self.update_filter_values)
    
    def set_data(self, data: pd.DataFrame):
        """
        Set the data to display in the table
        
        Args:
            data: DataFrame containing DSSAT output data
        """
        if data is None or data.empty:
            self.clear()
            return
            
        self._data = data.copy()
        self._filtered_data = self._data.copy()
        
        # Update model
        model = PandasTableModel(self._filtered_data)
        self.table_view.setModel(model)
        
        # Auto-resize columns to content
        self.table_view.resizeColumnsToContents()
        
        # Update filter controls
        self.update_filter_columns()
    
    def clear(self):
        """Clear the table"""
        self._data = None
        self._filtered_data = None
        self.table_view.setModel(None)
        self.filter_column.clear()
        self.filter_value.clear()
    
    def update_filter_columns(self):
        """Update the filter column dropdown with available columns"""
        if self._data is None:
            return
            
        self.filter_column.clear()
        
        # Add columns to filter dropdown
        for col in self._data.columns:
            self.filter_column.addItem(str(col))
    
    def update_filter_values(self):
        """Update filter values based on selected column"""
        if self._data is None:
            return
            
        self.filter_value.clear()
        
        column = self.filter_column.currentText()
        if column and column in self._data.columns:
            # Get unique values for the column
            unique_values = self._data[column].dropna().unique()
            
            # Add values to filter dropdown
            for value in sorted(unique_values):
                self.filter_value.addItem(str(value))
    
    def apply_filter(self):
        """Apply filter to the data"""
        if self._data is None:
            return
            
        column = self.filter_column.currentText()
        filter_text = self.filter_value.currentText()
        
        if column and filter_text and column in self._data.columns:
            try:
                # Check if column is numeric
                if pd.api.types.is_numeric_dtype(self._data[column]):
                    try:
                        # Try to convert filter value to numeric
                        filter_value = float(filter_text)
                        self._filtered_data = self._data[self._data[column] == filter_value]
                    except ValueError:
                        # If conversion fails, do string match
                        self._filtered_data = self._data[self._data[column].astype(str).str.contains(filter_text)]
                else:
                    # String match for non-numeric columns
                    self._filtered_data = self._data[self._data[column].astype(str).str.contains(filter_text)]
                
                # Update model
                model = PandasTableModel(self._filtered_data)
                self.table_view.setModel(model)
                self.table_view.resizeColumnsToContents()
                
            except Exception as e:
                logger.error(f"Error applying filter: {e}")
    
    def clear_filter(self):
        """Clear filter and show all data"""
        if self._data is None:
            return
            
        self._filtered_data = self._data.copy()
        
        # Update model
        model = PandasTableModel(self._filtered_data)
        self.table_view.setModel(model)
        self.table_view.resizeColumnsToContents()
    
    def export_data(self):
        """Export data to CSV or Excel"""
        if self._filtered_data is None or self._filtered_data.empty:
            return
            
        # Ask for file name and type
        file_path, filter_type = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                self._filtered_data.to_csv(file_path, index=False)
            elif file_path.endswith('.xlsx'):
                self._filtered_data.to_excel(file_path, index=False)
            else:
                # Add extension based on filter
                if 'CSV' in filter_type:
                    file_path += '.csv'
                    self._filtered_data.to_csv(file_path, index=False)
                else:
                    file_path += '.xlsx'
                    self._filtered_data.to_excel(file_path, index=False)
                    
        except Exception as e:
            logger.error(f"Error exporting data: {e}")