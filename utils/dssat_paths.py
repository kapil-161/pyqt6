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
    """Find DSSATPRO.V48 file location, including subdirectory Tools\GBuild"""
    try:
        # First check environment variable
        dssat_env = os.getenv('DSSAT48')
        if dssat_env:
            env_path = os.path.join(dssat_env, 'DSSATPRO.V48')
            if os.path.exists(env_path):
                return env_path

        possible_drives = ['C:', 'D:', 'E:']
        possible_paths = [f'DSSAT{i:02d}' for i in range(48, 49)]  # Focus on DSSAT48
        
        search_paths = []
        for drive in possible_drives:
            # Program Files paths
            if drive == 'C:':
                search_paths.extend([
                    os.path.join('C:\\Program Files', path) for path in possible_paths
                ])
                search_paths.extend([
                    os.path.join('C:\\Program Files (x86)', path) for path in possible_paths
                ])
            
            # Root directory paths
            search_paths.extend([
                os.path.join(f"{drive}\\", path) for path in possible_paths
            ])
            
            # Tools\GBuild paths
            search_paths.extend([
                os.path.join(f"{drive}\\", path, 'Tools', 'GBuild') for path in possible_paths
            ])

        # Search all paths for DSSATPRO.V48
        for base_path in search_paths:
            file_path = os.path.join(base_path, 'DSSATPRO.V48')
            if os.path.exists(file_path):
                logger.info(f"Found DSSATPRO.V48 at: {file_path}")
                return file_path

        raise FileNotFoundError("Could not find DSSATPRO.V48 file. Please ensure DSSAT is installed correctly.")
    
    except Exception as e:
        logger.error(f"Error finding DSSATPRO.V48: {str(e)}")
        raise

def verify_dssat_installation(base_path: str) -> bool:
    """Verify that all required DSSAT files exist"""
    required_files = ['DSSATPRO.V48', 'DETAIL.CDE', 'DSCSM048.EXE']
    return all(os.path.exists(os.path.join(base_path, file)) for file in required_files)

def get_dssat_base() -> str:
    """Get DSSAT base directory from DSSATPRO.V48"""
    try:
        v48_path = find_dssatpro_file()
        
        with open(v48_path, 'r') as file:
            for line in file:
                if line.strip().startswith('DDB'):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        dssat_path = (parts[1] + parts[2]).replace(' ', '')
                        dssat_path = dssat_path.replace('\\', '/')
                        
                        # Verify installation
                        if verify_dssat_installation(dssat_path):
                            return dssat_path
                        else:
                            logger.warning(f"Found DSSAT path but missing required files: {dssat_path}")
                            
        raise ValueError("Valid DSSAT installation not found")
        
    except Exception as e:
        logger.error(f"Error getting DSSAT base directory: {str(e)}")
        raise

def get_crop_details() -> List[dict]:
    """Get crop codes, names, and directories from DETAIL.CDE and DSSATPRO.V48."""
    try:
        from config import DSSAT_BASE
        
        detail_cde_path = os.path.join(DSSAT_BASE, 'DETAIL.CDE')
        dssatpro_path = os.path.join(DSSAT_BASE, 'DSSATPRO.V48')
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
        
        # Step 2: Get directories from DSSATPRO.V48
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
                        
                        # Update matching crop directory
                        for crop in crop_details:
                            if crop['code'] == code:
                                crop['directory'] = directory
                                logger.info(f"Found directory for {crop['name']}: {directory}")
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
