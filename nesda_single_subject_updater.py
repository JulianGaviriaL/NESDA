#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NESDA Single Subject BIDS JSON Updater - sub-210456 Only
Author: JulianGaviriaL
Date: 2025-09-23 13:53:58
Purpose: Process only sub-210456/ses-lei02/func
"""

import os
import json
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime

def safe_float(value_str, default=None):
    """Safely convert string to float"""
    if not value_str or str(value_str).strip() in ['', '(float)', 'N/A', 'n/a', '?', 'null']:
        return default
    try:
        clean_val = str(value_str).strip().replace('(', '').replace(')', '')
        return float(clean_val)
    except (ValueError, TypeError):
        return default

def safe_int(value_str, default=None):
    """Safely convert string to int"""
    val = safe_float(value_str)
    return int(val) if val is not None else default

def safe_str(value_str, default=""):
    """Safely convert to string"""
    if not value_str:
        return default
    clean_val = str(value_str).strip()
    if clean_val in ['(string)', 'N/A', 'n/a', '?', 'null', '']:
        return default
    return clean_val

def extract_complete_philips_params(par_file_path):
    """Extract COMPLETE Philips parameters from PAR file"""
    
    bids_fields = {}
    
    try:
        with open(par_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print(f"🔍 Extracting from: {Path(par_file_path).name}")
        
        # Basic parameters
        bids_fields['Manufacturer'] = 'Philips'
        bids_fields['ImageComments'] = 'NESDA'
        bids_fields['UsePhilipsFloatNotDisplayScaling'] = True
        bids_fields['TaskName'] = 'rest'
        
        # Patient Position
        position_patterns = [r'Patient position\s*:\s*([^\n\r]+)']
        for pattern in position_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                position = safe_str(match.group(1).strip())
                if position:
                    bids_fields['PatientPosition'] = position
                    print(f"✅ PatientPosition: {position}")
                    break
        if 'PatientPosition' not in bids_fields:
            bids_fields['PatientPosition'] = 'HFS'
        
        # Series Description
        series_patterns = [r'Series Type\s*:\s*([^\n\r]+)']
        for pattern in series_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                series_desc = safe_str(match.group(1).strip())
                if series_desc:
                    bids_fields['SeriesDescription'] = series_desc
                    print(f"✅ SeriesDescription: {series_desc}")
                    break
        if 'SeriesDescription' not in bids_fields:
            bids_fields['SeriesDescription'] = 'fMRI_BOLD_REST'
        
        # Protocol Name
        protocol_patterns = [r'Protocol name\s*:\s*([^\n\r]+)']
        for pattern in protocol_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                protocol = safe_str(match.group(1).strip())
                if protocol:
                    bids_fields['ProtocolName'] = protocol
                    print(f"✅ ProtocolName: {protocol}")
                    break
        if 'ProtocolName' not in bids_fields:
            bids_fields['ProtocolName'] = 'NESDA_REST_fMRI'
        
        # Series Number
        series_num_patterns = [r'Series nr\s*:\s*(\d+)']
        for pattern in series_num_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                series_num = safe_int(match.group(1))
                if series_num:
                    bids_fields['SeriesNumber'] = series_num
                    print(f"✅ SeriesNumber: {series_num}")
                    break
        if 'SeriesNumber' not in bids_fields:
            bids_fields['SeriesNumber'] = 1
        
        # Acquisition Number
        acq_patterns = [r'Acquisition nr\s*:\s*(\d+)']
        for pattern in acq_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                acq_num = safe_int(match.group(1))
                if acq_num:
                    bids_fields['AcquisitionNumber'] = acq_num
                    print(f"✅ AcquisitionNumber: {acq_num}")
                    break
        if 'AcquisitionNumber' not in bids_fields:
            bids_fields['AcquisitionNumber'] = 1
        
        # Philips Rescale Parameters from image data
        image_section = re.search(r'# === IMAGE INFORMATION =+(.*?)(?=# ===|$)', content, re.DOTALL)
        if image_section:
            image_lines = image_section.group(1).split('\n')
            for line in image_lines:
                parts = line.strip().split()
                if len(parts) >= 12 and parts[0].isdigit():
                    try:
                        rescale_slope = safe_float(parts[10]) if len(parts) > 10 else 1.0
                        rescale_intercept = safe_float(parts[11]) if len(parts) > 11 else 0.0
                        scale_slope = safe_float(parts[12]) if len(parts) > 12 else 1.0
                        
                        if rescale_slope:
                            bids_fields['PhilipsRescaleSlope'] = rescale_slope
                        if rescale_intercept is not None:
                            bids_fields['PhilipsRescaleIntercept'] = rescale_intercept
                        if scale_slope:
                            bids_fields['PhilipsScaleSlope'] = scale_slope
                        break
                    except (ValueError, IndexError):
                        continue
        
        # Defaults if not found
        if 'PhilipsRescaleSlope' not in bids_fields:
            bids_fields['PhilipsRescaleSlope'] = 1.0
        if 'PhilipsRescaleIntercept' not in bids_fields:
            bids_fields['PhilipsRescaleIntercept'] = 0.0
        if 'PhilipsScaleSlope' not in bids_fields:
            bids_fields['PhilipsScaleSlope'] = 1.0
        
        # Echo Time
        te_patterns = [r'Echo time\s*\[ms\]\s*:\s*([\d.]+)']
        for pattern in te_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                te_ms = safe_float(match.group(1))
                if te_ms and te_ms > 0:
                    bids_fields['EchoTime'] = round(te_ms / 1000.0, 6)
                    print(f"✅ EchoTime: {bids_fields['EchoTime']} s")
                    break
        if 'EchoTime' not in bids_fields:
            bids_fields['EchoTime'] = 0.028
        
        # Image Orientation
        orientation_matrix = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]  # Default
        if image_section:
            image_lines = image_section.group(1).split('\n')
            for line in image_lines:
                parts = line.strip().split()
                if len(parts) >= 18 and parts[0].isdigit():
                    try:
                        orientation_values = [
                            safe_float(parts[13]), safe_float(parts[14]), safe_float(parts[15]),
                            safe_float(parts[16]), safe_float(parts[17]), safe_float(parts[18])
                        ]
                        if all(v is not None for v in orientation_values):
                            orientation_matrix = orientation_values
                            break
                    except (ValueError, IndexError):
                        continue
        bids_fields['ImageOrientationPatientDICOM'] = orientation_matrix
        
        # Repetition Time
        tr_patterns = [r'Repetition time \[ms\]\s*:\s*([\d.]+)']
        for pattern in tr_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                tr_ms = safe_float(match.group(1))
                if tr_ms and tr_ms > 0:
                    bids_fields['RepetitionTime'] = round(tr_ms / 1000.0, 6)
                    print(f"✅ RepetitionTime: {bids_fields['RepetitionTime']} s")
                    break
        
        # Number of slices for SliceTiming
        slices_patterns = [r'Max\.\s*number of slices/locations\s*:\s*(\d+)']
        n_slices = None
        for pattern in slices_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                n_slices = safe_int(match.group(1))
                if n_slices and n_slices > 0:
                    print(f"✅ NumberOfSlices: {n_slices}")
                    break
        
        # Slice Timing - Interleaved Ascending
        if 'RepetitionTime' in bids_fields and n_slices:
            tr = bids_fields['RepetitionTime']
            time_per_slice = tr / n_slices
            slice_timing = [0.0] * n_slices
            acquisition_order = []
            
            # Odd slices first (1,3,5...)
            for slice_num in range(1, n_slices + 1, 2):
                acquisition_order.append(slice_num - 1)
            
            # Even slices second (2,4,6...)
            for slice_num in range(2, n_slices + 1, 2):
                acquisition_order.append(slice_num - 1)
            
            # Assign timing
            for acq_time_index, slice_index in enumerate(acquisition_order):
                slice_timing[slice_index] = round(acq_time_index * time_per_slice, 6)
            
            bids_fields['SliceTiming'] = slice_timing
            print(f"✅ SliceTiming: Interleaved ascending, {len(slice_timing)} slices")
        
        # Slice Encoding Direction
        slice_encoding_dir = 'k'  # Default axial
        orientation_patterns = [r'slice orientation \( TRA/SAG/COR \)\s*\(integer\)\s+(\d+)']
        for pattern in orientation_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                orient_code = safe_int(match.group(1))
                if orient_code == 1:
                    slice_encoding_dir = 'k'  # Axial
                elif orient_code == 2:
                    slice_encoding_dir = 'i'  # Sagittal
                elif orient_code == 3:
                    slice_encoding_dir = 'j'  # Coronal
                break
        bids_fields['SliceEncodingDirection'] = slice_encoding_dir
        print(f"✅ SliceEncodingDirection: {slice_encoding_dir}")
        
        # Phase Encoding Direction
        phase_encoding_dir = 'j-'  # Default A-P
        prep_patterns = [r'Preparation direction\s*:\s*([^\n\r]+)']
        for pattern in prep_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                direction = match.group(1).strip().lower()
                if 'anterior-posterior' in direction or direction == 'ap':
                    phase_encoding_dir = 'j-'
                elif 'posterior-anterior' in direction or direction == 'pa':
                    phase_encoding_dir = 'j'
                elif 'left-right' in direction or direction == 'lr':
                    phase_encoding_dir = 'i-'
                elif 'right-left' in direction or direction == 'rl':
                    phase_encoding_dir = 'i'
                break
        bids_fields['PhaseEncodingDirection'] = phase_encoding_dir
        print(f"✅ PhaseEncodingDirection: {phase_encoding_dir}")
        
        # Effective Echo Spacing
        water_fat_shift = None
        recon_matrix_pe = None
        
        wfs_patterns = [r'Water Fat shift \[pixels\]\s*:\s*([\d.]+)']
        for pattern in wfs_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                water_fat_shift = safe_float(match.group(1))
                break
        
        recon_patterns = [r'recon resolution \(x,?\s*y\)\s*:\s*(\d+)\s+(\d+)']
        for pattern in recon_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                recon_y = safe_int(match.group(2))
                if recon_y:
                    recon_matrix_pe = recon_y
                break
        
        if water_fat_shift and recon_matrix_pe:
            try:
                bandwidth_factor = 434.215
                bandwidth_per_pixel_hz = bandwidth_factor / water_fat_shift
                ees = 1.0 / (bandwidth_per_pixel_hz * recon_matrix_pe)
                bids_fields['EffectiveEchoSpacing'] = round(ees, 8)
                print(f"✅ EffectiveEchoSpacing: {bids_fields['EffectiveEchoSpacing']} s")
            except Exception as e:
                bids_fields['EffectiveEchoSpacing'] = 0.0005
        else:
            bids_fields['EffectiveEchoSpacing'] = 0.0005
        
        param_count = len([k for k in bids_fields.keys() if not k.startswith('_')])
        print(f"📊 Extracted {param_count} BIDS parameters")
        
        return bids_fields
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}

def update_json_file(json_file_path, bids_params):
    """Update JSON with BIDS parameters"""
    
    # Create backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{json_file_path}.backup_{timestamp}"
    try:
        shutil.copy2(json_file_path, backup_path)
        print(f"💾 Backup created: {Path(backup_path).name}")
    except Exception as e:
        print(f"⚠️ Backup failed: {e}")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        added_fields = []
        updated_fields = []
        
        for field_name, field_value in bids_params.items():
            if field_name.startswith('_'):
                continue
                
            if field_name in json_data:
                if json_data[field_name] != field_value:
                    json_data[field_name] = field_value
                    updated_fields.append(field_name)
            else:
                json_data[field_name] = field_value
                added_fields.append(field_name)
        
        json_data['_ProcessingInfo'] = {
            'ProcessedBy': 'JulianGaviriaL',
            'ProcessingDateTime': datetime.now().isoformat(),
            'Subject': 'sub-210456',
            'Session': 'ses-lei02',
            'SingleSubjectRerun': True,
            'FieldsAdded': added_fields,
            'FieldsUpdated': updated_fields
        }
        
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, sort_keys=False)
        
        return True, len(added_fields), len(updated_fields)
        
    except Exception as e:
        print(f"❌ JSON update failed: {e}")
        return False, 0, 0

def main():
    """Process sub-210456 only"""
    
    print("=" * 80)
    print("🎯 NESDA Single Subject Rerun - sub-210456/ses-lei02/func")
    print(f"👨‍💻 Author: JulianGaviriaL")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Target paths
    bids_root = "D:\\NESDA\\BIDS"
    subject_path = Path(bids_root) / "sub-210456" / "ses-lei02" / "func"
    
    print(f"📁 Target: {subject_path}")
    
    if not subject_path.exists():
        print(f"❌ Directory not found: {subject_path}")
        return 1
    
    # Find PAR and JSON files
    par_files = [f for f in subject_path.iterdir() if f.suffix.upper() == '.PAR']
    json_files = [f for f in subject_path.iterdir() 
                  if f.suffix.lower() == '.json' and 'backup' not in f.name.lower()]
    
    print(f"📄 Found {len(par_files)} PAR files, {len(json_files)} JSON files")
    
    if not par_files or not json_files:
        print("❌ No PAR/JSON files found!")
        return 1
    
    # Process the files
    par_file = par_files[0]
    json_file = json_files[0]
    
    print(f"\n🔄 Processing: {par_file.name} → {json_file.name}")
    
    # Extract parameters
    bids_params = extract_complete_philips_params(str(par_file))
    
    if not bids_params:
        print("❌ Failed to extract parameters")
        return 1
    
    # Update JSON
    success, added, updated = update_json_file(str(json_file), bids_params)
    
    if success:
        print(f"\n✅ SUCCESS! Updated JSON file (+{added} new, ~{updated} updated)")
        print("🎉 sub-210456 processing complete!")
    else:
        print("\n❌ Failed to update JSON file")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())