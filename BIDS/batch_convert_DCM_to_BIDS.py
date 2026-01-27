#!/usr/bin/env python3
"""
This script converts DICOM medical imaging files to BIDS (Brain Imaging Data Structure) format using dcm2niix. It:

-Runs dcm2niix on DICOM files
-Organizes output into BIDS directory structure (anat/func/dwi/fmap folders)
-Automatically determines scan types from metadata
-Handles Windows encoding issues
-Creates BIDS-compliant JSON metadata files

"""

import os
import json
import subprocess
import shutil
import logging
import tempfile
from pathlib import Path
from datetime import datetime
import sys

# Fix encoding issues on Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# Configure logging with proper encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('nesda_conversion.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# System paths
DCM2NIIX_PATH = r"D:\software\dcm2niix\dcm2niix.exe"
INPUT_DIR = r"D:\NESDA\W6\BIDS_W3_v2\sub-500150\ses03-Leiden"
OUTPUT_DIR = r"D:\NESDA\W6\BIDS_converted"

def convert_dicom_to_bids():
    """Convert DICOM files using dcm2niix with proper error handling"""
    logger.info("Starting DICOM to BIDS conversion...")
    
    dicom_folder = Path(INPUT_DIR) / "DICOMS_500150" / "DICOM"
    
    if not dicom_folder.exists():
        logger.error(f"DICOM folder not found: {dicom_folder}")
        return False
    
    # Create a persistent temp directory to debug
    temp_dir = Path(OUTPUT_DIR) / "temp_dcm2niix"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Run dcm2niix
        cmd = [
            DCM2NIIX_PATH,
            '-b', 'y',  # BIDS sidecar
            '-z', 'y',  # Compress
            '-o', str(temp_dir),  # Output to temp
            '-f', 'sub-500150_ses-03Leiden_%p_%t_%s',  # BIDS naming
            str(dicom_folder)
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        # Run with proper encoding handling
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=600,
            encoding='utf-8',
            errors='replace'  # Replace problematic characters
        )
        
        if result.returncode == 0:
            logger.info("dcm2niix conversion successful")
            
            # List what dcm2niix created
            temp_files = list(temp_dir.glob("*"))
            logger.info(f"dcm2niix created {len(temp_files)} files")
            for f in temp_files:
                logger.info(f"   - {f.name}")
            
            # Organize output into BIDS structure
            success = organize_bids_output_safe(temp_dir)
            
            # Clean up temp directory only if successful
            if success:
                shutil.rmtree(temp_dir)
            else:
                logger.warning(f"Keeping temp files for debugging: {temp_dir}")
            
            return success
        else:
            logger.error(f"dcm2niix failed with return code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("dcm2niix conversion timed out")
        return False
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return False

def organize_bids_output_safe(temp_dir):
    """Safely organize dcm2niix output with encoding error handling"""
    temp_path = Path(temp_dir)
    nii_files = list(temp_path.glob("*.nii.gz"))
    
    logger.info(f"Organizing {len(nii_files)} NIfTI files...")
    
    if not nii_files:
        logger.error("No NIfTI files found in dcm2niix output")
        return False
    
    success_count = 0
    
    for nii_file in nii_files:
        json_file = nii_file.with_suffix('.json')
        
        if not json_file.exists():
            logger.warning(f"No JSON for {nii_file.name}")
            continue
        
        try:
            # Read metadata with encoding handling
            with open(json_file, 'r', encoding='utf-8', errors='replace') as f:
                metadata = json.load(f)
            
            # Determine modality and BIDS name
            modality, bids_name = determine_bids_info_safe(nii_file.stem, metadata)
            
            # Create BIDS directories
            bids_dir = Path(OUTPUT_DIR) / "sub-500150" / "ses-03Leiden" / modality
            bids_dir.mkdir(parents=True, exist_ok=True)
            
            # Define destination paths
            dest_nii = bids_dir / f"{bids_name}.nii.gz"
            dest_json = bids_dir / f"{bids_name}.json"
            
            # Add task info for functional scans
            if modality == 'func' and 'TaskName' not in metadata:
                if 'rest' in bids_name.lower():
                    metadata['TaskName'] = 'rest'
                elif 'ert' in bids_name.lower():
                    metadata['TaskName'] = 'ert'
            
            # Copy NIfTI file
            shutil.copy2(nii_file, dest_nii)
            
            # Save JSON with encoding handling
            with open(dest_json, 'w', encoding='utf-8', errors='replace') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Converted: {dest_nii.relative_to(OUTPUT_DIR)}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"Error organizing {nii_file.name}: {e}")
            continue
    
    logger.info(f"Successfully organized {success_count}/{len(nii_files)} files")
    return success_count > 0

def determine_bids_info_safe(filename, metadata):
    """Safely determine BIDS modality and filename"""
    try:
        series_desc = str(metadata.get('SeriesDescription', '')).lower()
        protocol_name = str(metadata.get('ProtocolName', '')).lower()
        filename_lower = filename.lower()
        
        logger.debug(f"Analyzing: {filename}")
        logger.debug(f"   Series: {series_desc}")
        logger.debug(f"   Protocol: {protocol_name}")
        
        # Functional
        if any(term in series_desc + protocol_name + filename_lower 
               for term in ['rest', 'resting', 'bold']):
            return 'func', 'sub-500150_ses-03Leiden_task-rest_bold'
        
        elif any(term in series_desc + protocol_name + filename_lower 
                 for term in ['ert', 'emotion']):
            return 'func', 'sub-500150_ses-03Leiden_task-ert_bold'
        
        # Anatomical
        elif any(term in series_desc + protocol_name + filename_lower 
                 for term in ['t1', 'mprage']):
            return 'anat', 'sub-500150_ses-03Leiden_T1w'
        
        elif any(term in series_desc + protocol_name + filename_lower 
                 for term in ['t2']):
            return 'anat', 'sub-500150_ses-03Leiden_T2w'
        
        # DWI
        elif any(term in series_desc + protocol_name + filename_lower 
                 for term in ['dti', 'dwi', 'diffusion']):
            return 'dwi', 'sub-500150_ses-03Leiden_dwi'
        
        # Fieldmap
        elif any(term in series_desc + protocol_name + filename_lower 
                 for term in ['fieldmap', 'b0']):
            if 'magnitude' in series_desc + filename_lower:
                return 'fmap', 'sub-500150_ses-03Leiden_magnitude'
            elif 'phase' in series_desc + filename_lower:
                return 'fmap', 'sub-500150_ses-03Leiden_phasediff'
            else:
                return 'fmap', 'sub-500150_ses-03Leiden_fieldmap'
        
        # Default
        else:
            logger.warning(f"Unknown scan type for {filename}, using anatomical")
            return 'anat', 'sub-500150_ses-03Leiden_unknown'
            
    except Exception as e:
        logger.error(f"Error determining BIDS info for {filename}: {e}")
        return 'anat', 'sub-500150_ses-03Leiden_unknown'

def create_dataset_description():
    """Create BIDS dataset description"""
    dataset_description = {
        "Name": "NESDA Neuroimaging Dataset",
        "BIDSVersion": "1.8.0",
        "DatasetType": "raw",
        "Authors": ["Julian Gaviria", "NESDA Consortium"],
        "GeneratedBy": [
            {
                "Name": "NESDA DICOM to BIDS Converter - Fixed",
                "Version": "1.1.0",
                "Author": "JulianGaviriaL"
            }
        ],
        "ConversionDate": datetime.now().isoformat()
    }
    
    desc_path = Path(OUTPUT_DIR) / "dataset_description.json"
    with open(desc_path, 'w', encoding='utf-8') as f:
        json.dump(dataset_description, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Created: {desc_path}")

def main():
    """Main conversion function"""
    logger.info("NESDA CONVERSION - FIXED VERSION")
    logger.info("=" * 60)
    logger.info(f"Input: {INPUT_DIR}")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info(f"dcm2niix: {DCM2NIIX_PATH}")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Convert DICOM files
    if convert_dicom_to_bids():
        create_dataset_description()
        logger.info("CONVERSION COMPLETED SUCCESSFULLY")
        logger.info(f"Check output: {OUTPUT_DIR}")
        
        # Verify results
        logger.info("\nVERIFICATION:")
        subj_dir = Path(OUTPUT_DIR) / "sub-500150" / "ses-03Leiden"
        if subj_dir.exists():
            for modality in ['anat', 'func', 'dwi', 'fmap']:
                mod_dir = subj_dir / modality
                if mod_dir.exists():
                    nii_count = len(list(mod_dir.glob("*.nii.gz")))
                    logger.info(f"   {modality}: {nii_count} files")
    else:
        logger.error("CONVERSION FAILED")

if __name__ == "__main__":
    main()
