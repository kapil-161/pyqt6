import sys
import os
import logging
from typing import List, Optional, Tuple
from pathlib import Path

# Add project root to Python path
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_dir)

logger = logging.getLogger(__name__)

def find_dssatpro_file() -> str:
    """Find DSSATPRO.L48 file location for macOS"""
    try:
        # First check environment variable
        dssat_env = os.getenv('DSSAT48')
        if dssat_env:
            env_path = os.path.join(dssat_env, 'DSSATPRO.L48')
            if os.path.exists(env_path):
                return env_path

        # Check exact location shown in file info
        applications_path = '/Applications/DSSAT48/DSSATPRO.L48'
        if os.path.exists(applications_path):
            return applications_path

        # Fall back to other common macOS installation locations if needed
        possible_paths = [
            os.path.expanduser(f'~/DSSAT48'),
            os.path.expanduser(f'~/Applications/DSSAT48'),
            '/usr/local/DSSAT48',
        ]
        
        # Tools/GBuild paths
        tools_paths = [
            os.path.join(path, 'Tools', 'GBuild') for path in possible_paths
        ]
        
        # Combine all paths to search
        search_paths = possible_paths + tools_paths

        # Search all paths for DSSATPRO.L48
        for base_path in search_paths:
            file_path = os.path.join(base_path, 'DSSATPRO.L48')
            if os.path.exists(file_path):
                logger.info(f"Found DSSATPRO.L48 at: {file_path}")
                return file_path

        raise FileNotFoundError("Could not find DSSATPRO.L48 file. Please ensure DSSAT is installed correctly.")
    
    except Exception as e:
        logger.error(f"Error finding DSSATPRO.L48: {str(e)}")
        raise

def verify_dssat_installation(base_path: str) -> bool:
    """Verify that all required DSSAT files exist"""
    required_files = ['DSSATPRO.L48', 'DETAIL.CDE', 'DSCSM048.EXE']
    return all(os.path.exists(os.path.join(base_path, file)) for file in required_files)

def get_dssat_base() -> str:
    """Get DSSAT base directory from DSSATPRO.L48"""
    try:
        v48_path = find_dssatpro_file()
        
        # If we found the file directly in Applications, return the base path
        if v48_path == '/Applications/DSSAT48/DSSATPRO.L48':
            return '/Applications/DSSAT48'
        
        with open(v48_path, 'r') as file:
            for line in file:
                if line.strip().startswith('DDB'):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        dssat_path = (parts[1] + parts[2]).replace(' ', '')
                        # Convert Windows path separators to Unix
                        dssat_path = dssat_path.replace('\\', '/')
                        
                        # Handle potential Windows paths in the config file
                        if ':' in dssat_path:
                            # This is likely a Windows path (e.g., C:/DSSAT48)
                            # Use the known Mac path instead
                            dssat_path = '/Applications/DSSAT48'
                        
                        # Verify installation
                        if verify_dssat_installation(dssat_path):
                            return dssat_path
                        else:
                            logger.warning(f"Found DSSAT path but missing required files: {dssat_path}")
        
        # If we couldn't find it in the file, return the known path
        return '/Applications/DSSAT48'
        
    except Exception as e:
        logger.error(f"Error getting DSSAT base directory: {str(e)}")
        # Fallback to known location
        return '/Applications/DSSAT48'

def get_crop_details() -> List[dict]:
    """Get crop codes, names, and directories from DETAIL.CDE and DSSATPRO.L48."""
    try:
        from config import DSSAT_BASE
        
        detail_cde_path = os.path.join(DSSAT_BASE, 'DETAIL.CDE')
        dssatpro_path = os.path.join(DSSAT_BASE, 'DSSATPRO.L48')
        crop_details = []
        in_crop_section = False
        
        # Step 1: Get crop codes and names from DETAIL.CDE
        with open(detail_cde_path, 'r') as file:
            for line in file:
                if '*Crop and Weed Species' in line:
                    in_crop_section = True
                    continue
                    
                if '@CDE' in line:
                    continue
                    
                if line.startswith('*') and in_crop_section:
                    break
                    
                if in_crop_section and line.strip():
                    crop_code = line[:8].strip()
                    crop_name = line[8:72].strip()
                    if crop_code and crop_name:
                        crop_details.append({
                            'code': crop_code[:2],
                            'name': crop_name,
                            'directory': ''
                        })
        
        # Step 2: Get directories from DSSATPRO.L48
        with open(dssatpro_path, 'r') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split(None, 1)
                if len(parts) >= 2:
                    folder_code = parts[0]
                    if folder_code.endswith('D'):
                        code = folder_code[:-1]
                        directory = parts[1].replace(': ', ':')
                        # Convert Windows path separators if needed
                        directory = directory.replace('\\', '/')
                        
                        # Update matching crop directory
                        for crop in crop_details:
                            if crop['code'] == code:
                                crop['directory'] = directory
                                break
        
        return crop_details
        
    except Exception as e:
        logger.error(f"Error getting crop details: {str(e)}")
        return []
        
def prepare_folders() -> List[str]:
    """List available folders based on DETAIL.CDE crop codes and names."""
    try:
        from config import DSSAT_BASE
        
        detail_cde_path = os.path.join(DSSAT_BASE, 'DETAIL.CDE')
        valid_folders = []
        in_crop_section = False
        
        with open(detail_cde_path, 'r') as file:
            for line in file:
                if '*Crop and Weed Species' in line:
                    in_crop_section = True
                    continue
                
                if '@CDE' in line:
                    continue
                
                if line.startswith('*') and in_crop_section:
                    break
                
                if in_crop_section and line.strip():
                    crop_code = line[:8].strip()
                    crop_name = line[8:72].strip()
                    if crop_code and crop_name:
                        valid_folders.append(crop_name)
        
        return valid_folders
        
    except Exception as e:
        logger.error(f"Error preparing folders: {str(e)}")
        return []

def initialize_dssat_paths():
    """Initialize DSSAT paths and set global configuration variables."""
    try:
        import config
        
        # Hardcode the path for macOS to ensure it's correct
        dssat_base = '/Applications/DSSAT48'
        
        # Only try to get it dynamically if needed
        if not os.path.exists(dssat_base):
            dssat_base = get_dssat_base()
            
        print(f"DSSAT Base Directory: {dssat_base}")
        
        os.makedirs(dssat_base, exist_ok=True)
        dssat_exe = os.path.join(dssat_base, "DSCSM048.EXE")
        
        # Set global config variables
        config.DSSAT_BASE = dssat_base
        config.DSSAT_EXE = dssat_exe
        
        return dssat_base, dssat_exe
        
    except Exception as e:
        logger.error(f"Error initializing DSSAT paths: {str(e)}")
        raise