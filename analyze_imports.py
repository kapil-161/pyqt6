# -*- coding: utf-8 -*-
"""
Script to analyze Python source files in a project directory and list all used and unused imports.
This helps identify unnecessary dependencies to optimize PyInstaller builds.
"""

import os
import ast
import logging
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def collect_files(root_dir, exclude_dirs=('build', 'dist', 'hooks', '__pycache__')):
    """Collect all .py files in the project directory, excluding specified directories."""
    py_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                py_files.append(os.path.join(root, file))
    return py_files

def parse_file(file_path):
    """Parse a Python file and return its AST."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return ast.parse(f.read(), filename=file_path)
    except SyntaxError as e:
        logger.error(f"Syntax error in {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")
        return None

def collect_names(node):
    """Collect all names (variables, functions, classes) used in the AST node."""
    names = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            names.add(n.id)
    return names

def analyze_imports(file_path, tree):
    """Analyze imports in a file and determine which are used or unused."""
    if tree is None:
        return defaultdict(list), defaultdict(list)

    # Collect all imports
    imports = defaultdict(list)  # module -> [names]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.name].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                asname = alias.asname or alias.name
                imports[node.module].append(asname)

    # Collect all used names in the file
    used_names = collect_names(tree)

    # Determine used and unused imports
    used_imports = defaultdict(list)
    unused_imports = defaultdict(list)

    for module, names in imports.items():
        for name in names:
            if name in used_names:
                used_imports[module].append(name)
            else:
                unused_imports[module].append(name)

    return used_imports, unused_imports

def main():
    """Main function to analyze imports in the project directory."""
    project_dir = os.getcwd()  # Assumes script is run from project root
    logger.info(f"Analyzing Python files in {project_dir}")

    # Collect all .py files
    py_files = collect_files(project_dir)
    if not py_files:
        logger.warning("No Python files found in the project directory.")
        return

    logger.info(f"Found {len(py_files)} Python files to analyze.")

    # Analyze each file
    all_used_imports = defaultdict(set)
    all_unused_imports = defaultdict(set)

    for file_path in py_files:
        logger.info(f"Analyzing {file_path}")
        tree = parse_file(file_path)
        if tree:
            used_imports, unused_imports = analyze_imports(file_path, tree)

            # Aggregate used imports
            for module, names in used_imports.items():
                all_used_imports[module].update(names)

            # Aggregate unused imports
            for module, names in unused_imports.items():
                all_unused_imports[module].update(names)

    # Remove unused imports that are actually used (e.g., in other files)
    for module in list(all_unused_imports.keys()):
        if module in all_used_imports:
            all_unused_imports[module] = all_unused_imports[module] - all_used_imports[module]
            if not all_unused_imports[module]:
                del all_unused_imports[module]

    # Print results
    print("\n=== Used Imports ===")
    if all_used_imports:
        for module, names in sorted(all_used_imports.items()):
            print(f"{module}: {', '.join(sorted(names))}")
    else:
        print("No used imports found.")

    print("\n=== Unused Imports ===")
    if all_unused_imports:
        for module, names in sorted(all_unused_imports.items()):
            print(f"{module}: {', '.join(sorted(names))}")
    else:
        print("No unused imports found.")

    # Suggest optimizations for PyInstaller
    print("\n=== Optimization Suggestions for PyInstaller ===")
    if all_unused_imports:
        print("Consider adding these unused modules to the 'excludes' list in your PyInstaller spec file:")
        for module in sorted(all_unused_imports.keys()):
            print(f"  - {module}")
        print("This may reduce the executable size. Verify these modules are not indirectly required.")
    else:
        print("No unused imports to exclude. Check main.py for unnecessary top-level imports.")

if __name__ == "__main__":
    main()