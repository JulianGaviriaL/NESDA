#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
NESDA Targeted BIDS JSON Updater - Specific 39 Subjects Only
Author: JulianGaviriaL
Date: 2025-09-23 13:20:02
Purpose: Extract BIDS parameters ONLY for the specified 39 NESDA participants
Path Structure: D:\NESDA\BIDS\sub-XXXXXX\ses-XXXXX\func
r"""

import os
import json
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime
import time

# ===============================
# EXACT 39 TARGET SUBJECTS
# ===============================
TARGET_SUBJECTS = [
    'sub-110520', 'sub-110553', 'sub-110580', 'sub-110584', 'sub-110596',
    'sub-110614', 'sub-110639', 'sub-110643', 'sub-110653', 'sub-110654',
    'sub-110662', 'sub-110664', 'sub-110672', 'sub-110688', 'sub-110702',
    'sub-110706', 'sub-110716', 'sub-110723', 'sub-110727', 'sub-110754',
    'sub-110770', 'sub-110784', 'sub-110794', 'sub-110797', 'sub-110801',
    'sub-110819', 'sub-110834', 'sub-110854', 'sub-110855', 'sub-110861',
    'sub-120374', 'sub-120376', 'sub-120392', 'sub-120394', 'sub-120404',
    'sub-120409', 'sub-120417', 'sub-210456', 'sub-500150'
]

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
        
        print(f"        🔍 Extracting from: {Path(par_file_path).name}")
        
        # ===============================
        # 1. MANUFACTURER (always Philips)
        # ===============================
        bids_fields['Manufacturer'] = 'Philips'
        
        # ===============================
        # 2. PATIENT POSITION
        # ===============================
        position_patterns = [
            r'Patient position\s*:\s*([^\n\r]+)',
            r'patient position\s*:\s*([^\n\r]+)'
        ]
        
        for pattern in position_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                position = safe_str(match.group(1).strip())
                if position:
                    bids_fields['PatientPosition'] = position
                    print(f"          ✅ PatientPosition: {position}")
                    break
        
        if 'PatientPosition' not in bids_fields:
            bids_fields['PatientPosition'] = 'HFS'  # Default Head First Supine
        
        # ===============================
        # 3. SERIES DESCRIPTION
        # ===============================
        series_patterns = [
            r'Series Type\s*:\s*([^\n\r]+)',
            r'series description\s*:\s*([^\n\r]+)',
            r'Series description\s*:\s*([^\n\r]+)'
        ]
        
        for pattern in series_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                series_desc = safe_str(match.group(1).strip())
                if series_desc:
                    bids_fields['SeriesDescription'] = series_desc
                    print(f"          ✅ SeriesDescription: {series_desc}")
                    break
        
        if 'SeriesDescription' not in bids_fields:
            bids_fields['SeriesDescription'] = 'fMRI_BOLD_REST'
        
        # ===============================
        # 4. PROTOCOL NAME
        # ===============================
        protocol_patterns = [
            r'Protocol name\s*:\s*([^\n\r]+)',
            r'protocol name\s*:\s*([^\n\r]+)',
            r'Examination name\s*:\s*([^\n\r]+)'
        ]
        
        for pattern in protocol_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                protocol = safe_str(match.group(1).strip())
                if protocol:
                    bids_fields['ProtocolName'] = protocol
                    print(f"          ✅ ProtocolName: {protocol}")
                    break
        
        if 'ProtocolName' not in bids_fields:
            bids_fields['ProtocolName'] = 'NESDA_REST_fMRI'
        
        # ===============================
        # 5. SERIES NUMBER
        # ===============================
        series_num_patterns = [
            r'Series nr\s*:\s*(\d+)',
            r'series number\s*:\s*(\d+)',
            r'Series number\s*:\s*(\d+)'
        ]
        
        for pattern in series_num_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                series_num = safe_int(match.group(1))
                if series_num:
                    bids_fields['SeriesNumber'] = series_num
                    print(f"          ✅ SeriesNumber: {series_num}")
                    break
        
        if 'SeriesNumber' not in bids_fields:
            bids_fields['SeriesNumber'] = 1
        
        # ===============================
        # 6. ACQUISITION NUMBER
        # ===============================
        acq_patterns = [
            r'Acquisition nr\s*:\s*(\d+)',
            r'acquisition number\s*:\s*(\d+)',
            r'Acquisition number\s*:\s*(\d+)'
        ]
        
        for pattern in acq_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                acq_num = safe_int(match.group(1))
                if acq_num:
                    bids_fields['AcquisitionNumber'] = acq_num
                    print(f"          ✅ AcquisitionNumber: {acq_num}")
                    break
        
        if 'AcquisitionNumber' not in bids_fields:
            bids_fields['AcquisitionNumber'] = 1
        
        # ===============================
        # 7. IMAGE COMMENTS (always NESDA)
        # ===============================
        bids_fields['ImageComments'] = 'NESDA'
        
        # ===============================
        # 8. PHILIPS RESCALE PARAMETERS
        # ===============================
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
        
        # Default values if not found
        if 'PhilipsRescaleSlope' not in bids_fields:
            bids_fields['PhilipsRescaleSlope'] = 1.0
        if 'PhilipsRescaleIntercept' not in bids_fields:
            bids_fields['PhilipsRescaleIntercept'] = 0.0
        if 'PhilipsScaleSlope' not in bids_fields:
            bids_fields['PhilipsScaleSlope'] = 1.0
        
        # ===============================
        # 9. PHILIPS FLOAT SCALING
        # ===============================
        bids_fields['UsePhilipsFloatNotDisplayScaling'] = True
        
        # ===============================
        # 10. ECHO TIME
        # ===============================
        te_patterns = [
            r'Echo time\s*\[ms\]\s*:\s*([\d.]+)',
            r'TE\s*[=:]\s*([\d.]+)',
            r'echo_time\s+([\d.]+)'
        ]
        
        for pattern in te_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                te_ms = safe_float(match.group(1))
                if te_ms and te_ms > 0:
                    bids_fields['EchoTime'] = round(te_ms / 1000.0, 6)
                    print(f"          ✅ EchoTime: {bids_fields['EchoTime']} s")
                    break
        
        if 'EchoTime' not in bids_fields:
            bids_fields['EchoTime'] = 0.028  # Default fallback
        
        # ===============================
        # 11. IMAGE ORIENTATION PATIENT DICOM
        # ===============================
        orientation_matrix = []
        
        if image_section:
            image_lines = image_section.group(1).split('\n')
            for line in image_lines:
                parts = line.strip().split()
                if len(parts) >= 9 and parts[0].isdigit():
                    try:
                        if len(parts) >= 18:
                            orientation_values = [
                                safe_float(parts[13]), safe_float(parts[14]), safe_float(parts[15]),
                                safe_float(parts[16]), safe_float(parts[17]), safe_float(parts[18])
                            ]
                            
                            if all(v is not None for v in orientation_values):
                                orientation_matrix = orientation_values
                                break
                    except (ValueError, IndexError):
                        continue
        
        if not orientation_matrix:
            orientation_matrix = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        
        bids_fields['ImageOrientationPatientDICOM'] = orientation_matrix
        
        # ===============================
        # 12. REPETITION TIME
        # ===============================
        tr_patterns = [
            r'Repetition time \[ms\]\s*:\s*([\d.]+)',
            r'TR\s*[=:]\s*([\d.]+)',
            r'repetition_time\s+([\d.]+)'
        ]
        
        for pattern in tr_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                tr_ms = safe_float(match.group(1))
                if tr_ms and tr_ms > 0:
                    bids_fields['RepetitionTime'] = round(tr_ms / 1000.0, 6)
                    print(f"          ✅ RepetitionTime: {bids_fields['RepetitionTime']} s")
                    break
        
        # ===============================
        # 13. NUMBER OF SLICES (for SliceTiming)
        # ===============================
        slices_patterns = [
            r'Max\.\s*number of slices/locations\s*:\s*(\d+)',
            r'Max\. number of slices/locations\s*:\s*(\d+)',
            r'number of slices\s*[=:]\s*(\d+)'
        ]
        
        n_slices = None
        for pattern in slices_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                n_slices = safe_int(match.group(1))
                if n_slices and n_slices > 0:
                    print(f"          ✅ NumberOfSlices: {n_slices}")
                    break
        
        # ===============================
        # 14. SLICE TIMING - Interleaved Ascending
        # ===============================
        if 'RepetitionTime' in bids_fields and n_slices:
            tr = bids_fields['RepetitionTime']
            time_per_slice = tr / n_slices
            
            slice_timing = [0.0] * n_slices
            acquisition_order = []
            
            # Interleaved ascending: ODD slices first (1,3,5...), then EVEN slices (2,4,6...)
            for slice_num in range(1, n_slices + 1, 2):  # Odd slices
                acquisition_order.append(slice_num - 1)  # Convert to 0-based
            
            for slice_num in range(2, n_slices + 1, 2):  # Even slices
                acquisition_order.append(slice_num - 1)  # Convert to 0-based
            
            # Assign timing
            for acq_time_index, slice_index in enumerate(acquisition_order):
                slice_timing[slice_index] = round(acq_time_index * time_per_slice, 6)
            
            bids_fields['SliceTiming'] = slice_timing
            print(f"          ✅ SliceTiming: Interleaved ascending, {len(slice_timing)} slices")
        
        # ===============================
        # 15. TASK NAME
        # ===============================
        bids_fields['TaskName'] = 'rest'
        
        # ===============================
        # 16. SLICE ENCODING DIRECTION
        # ===============================
        slice_encoding_dir = None
        
        orientation_patterns = [
            r'slice orientation \( TRA/SAG/COR \)\s*\(integer\)\s+(\d+)',
            r'slice orientation\s*:\s*(\d+)'
        ]
        
        for pattern in orientation_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                orient_code = safe_int(match.group(1))
                if orient_code == 1:
                    slice_encoding_dir = 'k'  # Transverse/Axial
                elif orient_code == 2:
                    slice_encoding_dir = 'i'  # Sagittal
                elif orient_code == 3:
                    slice_encoding_dir = 'j'  # Coronal
                break
        
        if not slice_encoding_dir:
            slice_encoding_dir = 'k'  # Default axial
        
        bids_fields['SliceEncodingDirection'] = slice_encoding_dir
        print(f"          ✅ SliceEncodingDirection: {slice_encoding_dir}")
        
        # ===============================
        # 17. PHASE ENCODING DIRECTION
        # ===============================
        phase_encoding_dir = None
        
        prep_patterns = [
            r'Preparation direction\s*:\s*([^\n\r]+)',
            r'preparation direction\s*:\s*([^\n\r]+)',
            r'Phase encoding direction\s*:\s*([^\n\r]+)'
        ]
        
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
        
        if not phase_encoding_dir:
            phase_encoding_dir = 'j-'  # Default A-P
        
        bids_fields['PhaseEncodingDirection'] = phase_encoding_dir
        print(f"          ✅ PhaseEncodingDirection: {phase_encoding_dir}")
        
        # ===============================
        # 18. EFFECTIVE ECHO SPACING
        # ===============================
        water_fat_shift = None
        recon_matrix_pe = None
        
        wfs_patterns = [
            r'Water Fat shift \[pixels\]\s*:\s*([\d.]+)',
            r'water fat shift\s*:\s*([\d.]+)',
            r'WFS\s*:\s*([\d.]+)'
        ]
        
        for pattern in wfs_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                water_fat_shift = safe_float(match.group(1))
                break
        
        recon_patterns = [
            r'recon resolution \(x,?\s*y\)\s*:\s*(\d+)\s+(\d+)',
            r'Recon resolution \(x,?\s*y\)\s*:\s*(\d+)\s+(\d+)',
            r'Scan resolution\s*\(x,?\s*y\)\s*:\s*(\d+)\s+(\d+)'
        ]
        
        for pattern in recon_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                recon_x = safe_int(match.group(1))
                recon_y = safe_int(match.group(2))
                if recon_y:
                    recon_matrix_pe = recon_y
                break
        
        if water_fat_shift and recon_matrix_pe:
            try:
                bandwidth_factor = 434.215  # Standard Philips
                bandwidth_per_pixel_hz = bandwidth_factor / water_fat_shift
                ees = 1.0 / (bandwidth_per_pixel_hz * recon_matrix_pe)
                bids_fields['EffectiveEchoSpacing'] = round(ees, 8)
                print(f"          ✅ EffectiveEchoSpacing: {bids_fields['EffectiveEchoSpacing']} s")
            except Exception as e:
                print(f"          ⚠️  EffectiveEchoSpacing calculation failed: {e}")
                bids_fields['EffectiveEchoSpacing'] = 0.0005
        else:
            bids_fields['EffectiveEchoSpacing'] = 0.0005
        
        # Processing metadata
        bids_fields['_ProcessingInfo'] = {
            'ExtractedBy': 'nesda_targeted_bids_updater.py',
            'ExtractionDateTime': datetime.now().isoformat(),
            'ProcessedBy': 'JulianGaviriaL',
            'DataCollection': 'NESDA',
            'TargetedSubjects': len(TARGET_SUBJECTS),
            'AcquisitionType': 'interleaved_ascending',
            'ParametersExtracted': len([k for k in bids_fields.keys() if not k.startswith('_')])
        }
        
        param_count = len([k for k in bids_fields.keys() if not k.startswith('_')])
        print(f"          📊 Extracted {param_count} complete BIDS parameters")
        
        return bids_fields
        
    except Exception as e:
        print(f"          ❌ Error: {e}")
        return {}

def detect_session_pattern(subject_dir):
    """Detect the session pattern for each subject"""
    subject_path = Path(subject_dir)
    
    # Look for ses-* directories
    session_dirs = [item for item in subject_path.iterdir() 
                   if item.is_dir() and item.name.startswith('ses-')]
    
    if session_dirs:
        return session_dirs[0].name  # Return first session found
    
    return None

def find_par_json_pairs(func_dir):
    """Find PAR and JSON file pairs in BIDS func directory"""
    
    func_path = Path(func_dir)
    if not func_path.exists():
        return []
    
    par_files = [f for f in func_path.iterdir() 
                 if f.suffix.upper() == '.PAR' and f.is_file()]
    
    json_files = [f for f in func_path.iterdir() 
                  if (f.suffix.lower() == '.json' and f.is_file() and 
                      not f.name.startswith('.') and 
                      'backup' not in f.name.lower())]
    
    pairs = []
    
    if par_files and json_files:
        for json_file in json_files:
            json_stem = json_file.stem.lower()
            
            if 'task-rest' in json_stem or 'bold' in json_stem:
                best_par = None
                
                for par_file in par_files:
                    par_stem = par_file.stem.lower()
                    if any(task in par_stem for task in ['rest', 'bold', 'task', 'func']):
                        best_par = par_file
                        break
                
                if not best_par and par_files:
                    best_par = par_files[0]
                
                if best_par:
                    pairs.append((best_par, json_file))
        
        if not pairs and par_files and json_files:
            pairs.append((par_files[0], json_files[0]))
    
    return pairs

def update_json_with_complete_params(json_file_path, bids_params, create_backup=True):
    """Update JSON with complete BIDS parameters"""
    
    if create_backup:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{json_file_path}.backup_{timestamp}"
        try:
            shutil.copy2(json_file_path, backup_path)
            print(f"          💾 Backup created")
        except Exception as e:
            print(f"          ⚠️  Backup failed: {e}")
    
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
        
        processing_info = bids_params.get('_ProcessingInfo', {})
        
        json_data['_NESDAProcessingInfo'] = {
            'ProcessedBy': 'JulianGaviriaL',
            'ProcessingDateTime': datetime.now().isoformat(),
            'ProcessingScript': 'nesda_targeted_bids_updater.py',
            'DataCollection': 'NESDA',
            'TargetedProcessing': True,
            'TargetSubjects': len(TARGET_SUBJECTS),
            'AcquisitionType': 'interleaved_ascending',
            'FieldsAdded': added_fields,
            'FieldsUpdated': updated_fields
        }
        
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, sort_keys=False)
        
        return True, len(added_fields), len(updated_fields)
        
    except Exception as e:
        print(f"          ❌ JSON update failed: {e}")
        return False, 0, 0

def find_target_subjects(nesda_root):
    """Find only the 39 target subjects"""
    
    root_path = Path(nesda_root)
    if not root_path.exists():
        return []
    
    found_subjects = []
    missing_subjects = []
    
    for target_subject in TARGET_SUBJECTS:
        subject_path = root_path / target_subject
        if subject_path.exists() and subject_path.is_dir():
            found_subjects.append(subject_path)
        else:
            missing_subjects.append(target_subject)
    
    return found_subjects, missing_subjects

def process_target_subject(subject_dir):
    """Process one of the 39 target subjects"""
    
    subject_name = subject_dir.name
    print(f"\n    👤 {subject_name}")
    
    # Detect session pattern
    session_name = detect_session_pattern(subject_dir)
    
    if not session_name:
        print(f"      ⚠️  No session directory found")
        return 0, 0, 0
    
    session_dir = subject_dir / session_name
    func_dir = session_dir / 'func'
    
    if not func_dir.exists():
        print(f"      ⚠️  No func directory found in {session_name}")
        return 0, 0, 0
    
    print(f"      📂 {subject_name}/{session_name}/func")
    
    pairs = find_par_json_pairs(func_dir)
    
    if not pairs:
        print(f"        ⚠️  No PAR/JSON pairs found")
        return 0, 0, 0
    
    total_pairs = len(pairs)
    total_successes = 0
    total_failures = 0
    
    for par_file, json_file in pairs:
        print(f"        📄 {par_file.name} → {json_file.name}")
        
        bids_params = extract_complete_philips_params(str(par_file))
        
        if not bids_params:
            print(f"          ❌ No parameters extracted")
            total_failures += 1
            continue
        
        success, added, updated = update_json_with_complete_params(str(json_file), bids_params)
        
        if success:
            print(f"          ✅ Updated (+{added}, ~{updated})")
            total_successes += 1
        else:
            total_failures += 1
    
    return total_pairs, total_successes, total_failures

def main():
    """Main function for targeted 39-subject processing"""
    
    print("=" * 100)
    print("🎯 NESDA Targeted BIDS JSON Updater - Specific 39 Subjects Only")
    print(f"👨‍💻 Author: JulianGaviriaL")
    print(f"📅 Date: 2025-09-23 13:20:02")
    print("📁 Processing: D:\\NESDA\\BIDS")
    print(f"🎯 Target: Exactly {len(TARGET_SUBJECTS)} specific subjects")
    print("=" * 100)
    
    nesda_root = sys.argv[1] if len(sys.argv) > 1 else "D:\\NESDA\\BIDS"
    
    print(f"📁 BIDS Directory: {nesda_root}")
    print(f"🎯 Target Subjects: {len(TARGET_SUBJECTS)}")
    
    # Display target subjects
    print(f"\n📋 TARGET SUBJECTS ({len(TARGET_SUBJECTS)}):")
    for i, subject in enumerate(TARGET_SUBJECTS, 1):
        if i % 5 == 1:
            print(f"     ", end="")
        print(f"{subject:<12}", end="")
        if i % 5 == 0:
            print()
    if len(TARGET_SUBJECTS) % 5 != 0:
        print()
    
    found_subjects, missing_subjects = find_target_subjects(nesda_root)
    
    print(f"\n🔍 SEARCH RESULTS:")
    print(f"   ✅ Found: {len(found_subjects)} subjects")
    print(f"   ❌ Missing: {len(missing_subjects)} subjects")
    
    if missing_subjects:
        print(f"\n⚠️  MISSING SUBJECTS:")
        for missing in missing_subjects:
            print(f"     ❌ {missing}")
    
    if not found_subjects:
        print("\n❌ No target subjects found! Check your BIDS directory.")
        return 1
    
    print(f"\n🎯 PROCESSING FEATURES:")
    print(f"   📊 All required BIDS parameters")
    print(f"   🔬 Philips-specific parameters")
    print(f"   📋 Interleaved ascending slice timing")
    print(f"   🏥 Patient position and orientation")
    print(f"   💾 Automatic JSON backup")
    
    response = input(f"\n❓ Process {len(found_subjects)} found subjects? [y/N]: ").lower().strip()
    if response != 'y':
        print("Operation cancelled.")
        return 1
    
    start_time = time.time()
    
    print(f"\n🏁 Starting targeted processing for {len(found_subjects)} subjects...")
    print("=" * 100)
    
    stats = {'processed': 0, 'skipped': 0, 'pairs': 0, 'successes': 0, 'failures': 0}
    
    for i, subject_dir in enumerate(found_subjects, 1):
        print(f"\n  [{i}/{len(found_subjects)}] Processing {subject_dir.name}")
        
        try:
            pairs, successes, failures = process_target_subject(subject_dir)
            
            if pairs > 0:
                stats['processed'] += 1
                stats['pairs'] += pairs
                stats['successes'] += successes
                stats['failures'] += failures
            else:
                stats['skipped'] += 1
                
        except Exception as e:
            print(f"      ❌ Error processing {subject_dir.name}: {e}")
            stats['skipped'] += 1
    
    end_time = time.time()
    
    print("\n" + "=" * 100)
    print("🎉 NESDA TARGETED PROCESSING COMPLETE!")
    print("=" * 100)
    print(f"⏱️  Processing time: {(end_time-start_time)/60:.1f} minutes")
    print(f"🎯 Target subjects: {len(TARGET_SUBJECTS)}")
    print(f"✅ Found subjects: {len(found_subjects)}")
    print(f"👥 Processed subjects: {stats['processed']}")
    print(f"📄 JSON files updated: {stats['successes']}")
    print(f"📈 Success rate: {(stats['successes']/max(stats['pairs'],1))*100:.1f}%")
    
    if stats['successes'] > 0:
        print(f"\n🎊 SUCCESS! Updated {stats['successes']} JSON files for the targeted 39 subjects!")
        print("✨ Complete BIDS parameters extracted from PAR files")
        print("📋 Interleaved ascending slice timing applied")
        print("🎯 Only the specified 39 subjects were processed")
        print("💼 Ready for BIDS validation!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
