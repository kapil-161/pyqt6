import os
import re
from pathlib import Path
import shutil

def backup_file(file_path):
    """Create a backup of the file before modifying it."""
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Backup created: {backup_path}")

def convert_imports(content):
    """Convert PyQt5 imports to PyQt6."""
    # Direct module imports
    content = re.sub(r'from PyQt5\.', r'from PyQt6.', content)
    content = re.sub(r'import PyQt6\.', r'import PyQt6.', content)
    content = re.sub(r'import PyQt6\b', r'import PyQt6', content)
    
    return content

def convert_qt_constants(content):
    """Convert Qt constants that have changed in PyQt6."""
    # Common Qt constant changes
    replacements = {
        'Qt.Orientation.Horizontal': 'Qt.Orientation.Horizontal',
        'Qt.Orientation.Vertical': 'Qt.Orientation.Vertical',
        'Qt.DockWidgetArea.LeftDockWidgetArea': 'Qt.DockWidgetArea.LeftDockWidgetArea',
        'Qt.DockWidgetArea.RightDockWidgetArea': 'Qt.DockWidgetArea.RightDockWidgetArea',
        'Qt.DockWidgetArea.TopDockWidgetArea': 'Qt.DockWidgetArea.TopDockWidgetArea',
        'Qt.DockWidgetArea.BottomDockWidgetArea': 'Qt.DockWidgetArea.BottomDockWidgetArea',
        'Qt.AlignmentFlag.AlignLeft': 'Qt.AlignmentFlag.AlignLeft',
        'Qt.AlignmentFlag.AlignRight': 'Qt.AlignmentFlag.AlignRight',
        'Qt.AlignmentFlag.AlignTop': 'Qt.AlignmentFlag.AlignTop',
        'Qt.AlignmentFlag.AlignBottom': 'Qt.AlignmentFlag.AlignBottom',
        'Qt.AlignmentFlag.AlignCenter': 'Qt.AlignmentFlag.AlignCenter',
        'Qt.AlignmentFlag.AlignVCenter': 'Qt.AlignmentFlag.AlignVCenter',
        'Qt.AlignmentFlag.AlignHCenter': 'Qt.AlignmentFlag.AlignHCenter',
        'Qt.PenStyle.SolidLine': 'Qt.PenStyle.SolidLine',
        'Qt.PenStyle.DashLine': 'Qt.PenStyle.DashLine',
        'Qt.PenStyle.DotLine': 'Qt.PenStyle.DotLine',
        'Qt.PenStyle.DashDotLine': 'Qt.PenStyle.DashDotLine',
        'Qt.PenStyle.DashDotDotLine': 'Qt.PenStyle.DashDotDotLine',
        'Qt.PenStyle.NoPen': 'Qt.PenStyle.NoPen',
        'Qt.ItemDataRole.UserRole': 'Qt.ItemDataRole.UserRole',
        'Qt.ItemDataRole.DisplayRole': 'Qt.ItemDataRole.DisplayRole',
        'Qt.ItemDataRole.EditRole': 'Qt.ItemDataRole.EditRole',
        'Qt.ItemDataRole.DecorationRole': 'Qt.ItemDataRole.DecorationRole',
        'Qt.ItemDataRole.TextAlignmentRole': 'Qt.ItemDataRole.TextAlignmentRole',
        'Qt.ItemDataRole.BackgroundRole': 'Qt.ItemDataRole.BackgroundRole',
        'Qt.ItemDataRole.ForegroundRole': 'Qt.ItemDataRole.ForegroundRole',
        'Qt.ItemDataRole.FontRole': 'Qt.ItemDataRole.FontRole',
        'Qt.SortOrder.AscendingOrder': 'Qt.SortOrder.AscendingOrder',
        'Qt.SortOrder.DescendingOrder': 'Qt.SortOrder.DescendingOrder',
        'Qt.Key.': 'Qt.Key.',
        'Qt.WindowType.WindowCloseButtonHint': 'Qt.WindowType.WindowCloseButtonHint',
        'Qt.WindowType.WindowMinimizeButtonHint': 'Qt.WindowType.WindowMinimizeButtonHint',
        'Qt.WindowType.WindowMaximizeButtonHint': 'Qt.WindowType.WindowMaximizeButtonHint',
        'Qt.WindowType.WindowMinMaxButtonsHint': 'Qt.WindowType.WindowMinMaxButtonsHint',
        'Qt.WindowType.MSWindowsFixedSizeDialogHint': 'Qt.WindowType.MSWindowsFixedSizeDialogHint',
        'Qt.WindowType.CustomizeWindowHint': 'Qt.WindowType.CustomizeWindowHint',
        'Qt.WindowType.WindowTitleHint': 'Qt.WindowType.WindowTitleHint',
        'Qt.WindowType.Dialog': 'Qt.WindowType.Dialog',
        'Qt.WindowType.Window': 'Qt.WindowType.Window'
    }
    
    for old, new in replacements.items():
        # Be careful not to replace partial matches
        content = re.sub(r'\b' + re.escape(old) + r'\b', new, content)
    
    return content

def convert_signal_slot_syntax(content):
    """Update signal-slot connection syntax for PyQt6."""
    # PyQt6 keeps the same signal-slot connection syntax, but if there are deprecated methods,
    # they would be handled here
    return content

def convert_widget_api_changes(content):
    """Convert widget API changes between PyQt5 and PyQt6."""
    # Many QWidget methods have changed names or parameters
    replacements = {
        '.isChecked()': '.isChecked()',  # No change, just an example
        '.setEnabled(': '.setEnabled(',  # No change, just an example
        '.exec()': '.exec()',  # This one actually changed
        '.isActive()': '.isActive()',  # No change, just an example
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    return content

def convert_file(file_path):
    """Process a single Python file to convert PyQt5 to PyQt6."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Skip if file doesn't use PyQt5
        if 'PyQt5' not in content:
            print(f"Skipping {file_path} - no PyQt5 imports found")
            return False
        
        # Create backup before modifying
        backup_file(file_path)
        
        # Apply conversions
        new_content = convert_imports(content)
        new_content = convert_qt_constants(new_content)
        new_content = convert_signal_slot_syntax(new_content)
        new_content = convert_widget_api_changes(new_content)
        
        # Write changes back to file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(new_content)
        
        print(f"Converted: {file_path}")
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def process_directory(directory):
    """Process all Python files in the given directory recursively."""
    converted_files = 0
    skipped_files = 0
    
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.py'):
                file_path = os.path.join(root, filename)
                if convert_file(file_path):
                    converted_files += 1
                else:
                    skipped_files += 1
    
    return converted_files, skipped_files

def update_requirements(directory):
    """Update requirements or dependency files to use PyQt6 instead of PyQt5."""
    requirement_files = ['requirements.txt', 'setup.py', 'install_dependencies.py']
    
    for req_file in requirement_files:
        file_path = os.path.join(directory, req_file)
        if os.path.exists(file_path):
            backup_file(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Replace PyQt5 with PyQt6 in requirements
            if 'PyQt5' in content:
                content = re.sub(r'PyQt5==[\d\.]+', r'PyQt6==6.5.0', content)
                content = re.sub(r'PyQt5>=[\d\.]+', r'PyQt6>=6.5.0', content)
                content = re.sub(r'PyQt5~=[\d\.]+', r'PyQt6>=6.5.0', content)
                content = re.sub(r'"PyQt5"', r'"PyQt6"', content)
                content = re.sub(r"'PyQt5'", r"'PyQt6'", content)
                
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                print(f"Updated dependencies in {file_path}")

def check_pyqtgraph_compatibility(directory):
    """Check for pyqtgraph usage and warn about potential compatibility issues."""
    has_pyqtgraph = False
    
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.py'):
                file_path = os.path.join(root, filename)
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    if 'import pyqtgraph' in content or 'from pyqtgraph' in content:
                        has_pyqtgraph = True
                        print(f"PyQtGraph usage found in: {file_path}")
    
    if has_pyqtgraph:
        print("\nWARNING: PyQtGraph usage detected in the codebase.")
        print("Make sure you're using a version of PyQtGraph that's compatible with PyQt6.")
        print("You may need to update to pyqtgraph 0.12.0 or later.")
        print("Consider adding the following to your requirements: pyqtgraph>=0.12.4\n")

def main():
    # Directory to process
    directory = '.'  # Current directory, change if needed
    
    print(f"Starting PyQt5 to PyQt6 conversion in: {directory}")
    
    # Process all Python files
    converted, skipped = process_directory(directory)
    
    # Update requirements files
    update_requirements(directory)
    
    # Check pyqtgraph compatibility
    check_pyqtgraph_compatibility(directory)
    
    print("\nConversion complete!")
    print(f"Converted files: {converted}")
    print(f"Skipped files: {skipped}")
    print("\nPlease test your application thoroughly as manual adjustments may be needed.")
    print("Common issues to check for:")
    print("1. Qt namespace changes (Qt.Orientation, Qt.ItemDataRole, etc.)")
    print("2. Method name changes (.exec() → .exec())")
    print("3. Parameter type changes (QModelIndex changes)")
    print("4. Signal/slot connection issues")
    print("5. Layout and widget sizing behavior differences")

if __name__ == "__main__":
    main()