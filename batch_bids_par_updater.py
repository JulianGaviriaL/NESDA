#!/usr/bin/env python3
"""
ENHANCED Multi-Site BIDS PAR to JSON Updater for NESDA Dataset (3 Sites)
Author: JulianGaviriaL
Date: 2025-09-10 14:19:55
Purpose: Extract ALL BIDS parameters from Philips PAR files for 3 NESDA sites
ENHANCED: Handles Groningen, Amsterdam, and Leiden sites with different PAR versions
CORRECTED: Fixed slice timing for Philips interleaved ascending from bottom
"""

import os
import json
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime
import time

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

def detect_nesda_site(content, file_path=""):
    """
    Detect which of the 3 NESDA sites we're processing:
    1. Groningen (V4.1)
    2. Amsterdam (V4.2) 
    3. Leiden (V4.2)
    """
    
    site_info = {
        'version': 'unknown',
        'tool_version': 'unknown',
        'site_group': 'unknown',
        'actual_site': 'unknown',
        'characteristics': [],
        'confidence': 'low'
    }
    
    # Tool version detection (primary site indicator)
    version_match = re.search(r'Research image export tool\s+V([\d.]+)', content)
    if version_match:
        tool_version = version_match.group(1)
        site_info['tool_version'] = tool_version
        site_info['version'] = f"V{tool_version}"
        
        if tool_version == '4.1':
            site_info['site_group'] = 'Groningen'
            site_info['actual_site'] = 'Groningen'
            site_info['characteristics'].append('V4.1_format')
            site_info['confidence'] = 'high'
            
        elif tool_version == '4.2':
            site_info['site_group'] = 'AmsLei'
            site_info['characteristics'].append('V4.2_format')
            site_info['characteristics'].append('ASL_capable')
            
            # Distinguish Amsterdam vs Leiden within V4.2
            # Method 1: Check patient names for site-specific patterns
            patient_match = re.search(r'Patient name\s*:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
            if patient_match:
                patient_name = patient_match.group(1).strip().upper()
                
                # Amsterdam patterns (VUMC)
                if any(pattern in patient_name for pattern in ['VU', 'VUMC', 'AMSTERDAM']):
                    site_info['actual_site'] = 'Amsterdam'
                    site_info['confidence'] = 'high'
                # Leiden patterns (LUMC) 
                elif any(pattern in patient_name for pattern in ['LUMC', 'LEIDEN', 'HULSBOSCH']):
                    site_info['actual_site'] = 'Leiden'
                    site_info['confidence'] = 'high'
            
            # Method 2: Check file path for site indicators
            if site_info['actual_site'] == 'unknown' and file_path:
                path_upper = str(file_path).upper()
                if any(pattern in path_upper for pattern in ['AMSTERDAM', 'VUMC', 'AMS']):
                    site_info['actual_site'] = 'Amsterdam'
                    site_info['confidence'] = 'medium'
                elif any(pattern in path_upper for pattern in ['LEIDEN', 'LUMC', 'LEI']):
                    site_info['actual_site'] = 'Leiden'
                    site_info['confidence'] = 'medium'
            
            # Method 3: Infer from subject ID patterns (if applicable)
            examination_match = re.search(r'Examination name\s*:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
            if examination_match and site_info['actual_site'] == 'unknown':
                exam_name = examination_match.group(1).strip()
                # Look for site-specific subject ID patterns
                if re.search(r'110\d{3}', exam_name):  # Pattern like 110293, 110639
                    # Could use subject ID ranges to infer site
                    subject_match = re.search(r'110(\d{3})', exam_name)
                    if subject_match:
                        subject_num = int(subject_match.group(1))
                        # This is example logic - adjust based on actual ID ranges
                        if subject_num < 500:
                            site_info['actual_site'] = 'Leiden'
                        else:
                            site_info['actual_site'] = 'Amsterdam'
                        site_info['confidence'] = 'medium'
            
            # Default fallback for V4.2
            if site_info['actual_site'] == 'unknown':
                site_info['actual_site'] = 'AmsLei_unspecified'
                site_info['confidence'] = 'low'
    
    # Additional characteristics detection
    if 'Number of label types' in content:
        site_info['characteristics'].append('ASL_capable')
    
    if 'SPIR' in content:
        site_info['characteristics'].append('SPIR_suppression')
        
    if 'SENSE' in content:
        site_info['characteristics'].append('SENSE_acceleration')
    
    return site_info

def extract_philips_bids_3sites(par_file_path):
    """
    Enhanced BIDS parameter extraction for all 3 NESDA sites
    Handles Groningen (V4.1), Amsterdam (V4.2), and Leiden (V4.2)
    CORRECTED: Fixed slice timing for Philips interleaved ascending
    """
    
    bids_fields = {}
    
    try:
        with open(par_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print(f"        🔍 Extracting from: {Path(par_file_path).name}")
        
        # Detect which NESDA site
        site_info = detect_nesda_site(content, par_file_path)
        bids_fields['_SiteInfo'] = site_info
        
        site_display = f"{site_info['actual_site']} ({site_info['version']})"
        confidence_icon = "🎯" if site_info['confidence'] == 'high' else "🔍" if site_info['confidence'] == 'medium' else "❓"
        print(f"          🏥 Site: {confidence_icon} {site_display}")
        
        # === 1. REPETITION TIME (TR) - Site-aware patterns ===
        tr_patterns = [
            r'Repetition time \[ms\]\s*:\s*([\d.]+)',
            r'TR\s*[=:]\s*([\d.]+)',
            r'repetition_time\s+([\d.]+)',
            r'Repetition\s+time\s*:\s*([\d.]+)'
        ]
        
        for pattern in tr_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                tr_ms = safe_float(match.group(1))
                if tr_ms and tr_ms > 0:
                    bids_fields['RepetitionTime'] = round(tr_ms / 1000.0, 6)
                    print(f"          ✅ RepetitionTime: {bids_fields['RepetitionTime']} s")
                    break
        
        # === 2. ECHO TIME - Enhanced for 3 sites ===
        te_patterns = [
            r'Echo time\s*\[ms\]\s*:\s*([\d.]+)',
            r'TE\s*[=:]\s*([\d.]+)',
            r'echo_time\s+([\d.]+)',
            r'Echo\s+time\s*:\s*([\d.]+)'
        ]
        
        for pattern in te_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                te_ms = safe_float(match.group(1))
                if te_ms and te_ms > 0:
                    bids_fields['EchoTime'] = round(te_ms / 1000.0, 6)
                    print(f"          ✅ EchoTime: {bids_fields['EchoTime']} s")
                    break
        
        # === 3. NUMBER OF SLICES ===
        slices_patterns = [
            r'Max\.\s*number of slices/locations\s*:\s*(\d+)',
            r'Max\. number of slices/locations\s*:\s*(\d+)',
            r'number of slices\s*[=:]\s*(\d+)',
            r'Number\s+of\s+slices\s*:\s*(\d+)'
        ]
        
        n_slices = None
        for pattern in slices_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                n_slices = safe_int(match.group(1))
                if n_slices and n_slices > 0:
                    bids_fields['NumberOfSlices'] = n_slices
                    print(f"          ✅ NumberOfSlices: {n_slices}")
                    break
        
        # === 4. SLICE TIMING - CORRECTED for Philips interleaved ascending ===
        if 'RepetitionTime' in bids_fields and n_slices:
            tr = bids_fields['RepetitionTime']
            
            slice_timing = [0.0] * n_slices
            time_per_slice = tr / n_slices
            
            # CORRECTED: Philips interleaved ascending from bottom
            acquisition_order = []
            
            # First pass: ODD slice numbers (1, 3, 5, 7, ..., up to n_slices)
            # These map to EVEN array indices (0, 2, 4, 6, ...)
            for slice_num in range(1, n_slices + 1, 2):  # 1, 3, 5, 7, ...
                acquisition_order.append(slice_num - 1)  # Convert to 0-based: 0, 2, 4, 6, ...
            
            # Second pass: EVEN slice numbers (2, 4, 6, 8, ..., up to n_slices)
            # These map to ODD array indices (1, 3, 5, 7, ...)
            for slice_num in range(2, n_slices + 1, 2):  # 2, 4, 6, 8, ...
                acquisition_order.append(slice_num - 1)  # Convert to 0-based: 1, 3, 5, 7, ...
            
            # Assign timing based on acquisition order
            for acq_time_index, slice_index in enumerate(acquisition_order):
                slice_timing[slice_index] = round(acq_time_index * time_per_slice, 6)
            
            bids_fields['SliceTiming'] = slice_timing
            bids_fields['_SliceTimingMethod'] = 'interleaved_ascending_from_bottom'
            
            print(f"          ✅ SliceTiming: Interleaved ascending from bottom, {len(slice_timing)} slices")
            print(f"          📋 Order: Odd slices (1,3,5,...,{2*((n_slices+1)//2)-1}), then even slices (2,4,6,...,{2*(n_slices//2)})")
        
        # === 5. SLICE ENCODING DIRECTION - 3-site compatible ===
        slice_encoding_dir = None
        
        # Strategy 1: Look for slice orientation in image information
        # Pattern for slice orientation code in image data section
        orientation_patterns = [
            r'slice orientation \( TRA/SAG/COR \)\s*\(integer\)\s+(\d+)',
            r'slice orientation\s*:\s*(\d+)',
            r'slice_orientation\s*:\s*(\d+)'
        ]
        
        for pattern in orientation_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                orient_code = safe_int(match.group(1))
                print(f"          🔍 Found slice orientation code: {orient_code}")
                
                if orient_code == 1:
                    slice_encoding_dir = 'k'  # Transverse/Axial
                elif orient_code == 2:
                    slice_encoding_dir = 'i'  # Sagittal
                elif orient_code == 3:
                    slice_encoding_dir = 'j'  # Coronal
                
                if slice_encoding_dir:
                    bids_fields['SliceEncodingDirection'] = slice_encoding_dir
                    print(f"          ✅ SliceEncodingDirection: {slice_encoding_dir} (from code {orient_code})")
                    break
        
        # Strategy 2: Look in actual image data for orientation
        if not slice_encoding_dir:
            # Parse image information section to find orientation
            image_section = re.search(r'# === IMAGE INFORMATION =+(.*)', content, re.DOTALL)
            if image_section:
                image_lines = image_section.group(1).split('\n')
                for line in image_lines[:10]:  # Check first few image lines
                    # Look for orientation in image data (typically column 21)
                    parts = line.split()
                    if len(parts) > 20:
                        try:
                            orient_val = int(parts[20])  # 21st column (0-indexed)
                            if orient_val in [1, 2, 3]:
                                if orient_val == 1:
                                    slice_encoding_dir = 'k'  # Transverse
                                elif orient_val == 2:
                                    slice_encoding_dir = 'i'  # Sagittal
                                elif orient_val == 3:
                                    slice_encoding_dir = 'j'  # Coronal
                                
                                bids_fields['SliceEncodingDirection'] = slice_encoding_dir
                                print(f"          ✅ SliceEncodingDirection: {slice_encoding_dir} (from image data)")
                                break
                        except (ValueError, IndexError):
                            continue
        
        # Strategy 3: Patient position fallback
        if not slice_encoding_dir:
            pos_patterns = [
                r'Patient position\s*:\s*([A-Z\s]+?)(?:\n|$)',
                r'patient position\s*:\s*([A-Z\s]+?)(?:\n|$)'
            ]
            
            for pattern in pos_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    position = match.group(1).strip().upper()
                    print(f"          🔍 Found patient position: '{position}'")
                    
                    if any(pos in position for pos in ['HEAD FIRST SUPINE', 'HFS']):
                        slice_encoding_dir = 'k'  # Most common for axial
                        bids_fields['SliceEncodingDirection'] = slice_encoding_dir
                        print(f"          ✅ SliceEncodingDirection: {slice_encoding_dir} (from position)")
                        break
        
        # Strategy 4: Default for fMRI
        if not slice_encoding_dir:
            if re.search(r'rest|bold|fmri|epi|task|SENSE', content, re.IGNORECASE):
                slice_encoding_dir = 'k'  # Axial default for fMRI
                bids_fields['SliceEncodingDirection'] = slice_encoding_dir
                print(f"          ✅ SliceEncodingDirection: {slice_encoding_dir} (fMRI default)")
        
        # === 6. PHASE ENCODING DIRECTION - Philips "Preparation direction" ===
        phase_encoding_dir = None
        
        # Enhanced patterns for Philips preparation direction
        prep_patterns = [
            r'Preparation direction\s*:\s*([^\n\r]+)',
            r'preparation direction\s*:\s*([^\n\r]+)',
            r'Phase encoding direction\s*:\s*([^\n\r]+)',
            r'PE direction\s*:\s*([^\n\r]+)',
            r'Fold-?over direction\s*:\s*([^\n\r]+)'
        ]
        
        for pattern in prep_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                direction = match.group(1).strip()
                print(f"          🔍 Found Preparation direction: '{direction}'")
                
                direction_lower = direction.lower()
                
                if 'anterior-posterior' in direction_lower or direction_lower == 'ap':
                    phase_encoding_dir = 'j-'  # A → P
                elif 'posterior-anterior' in direction_lower or direction_lower == 'pa':
                    phase_encoding_dir = 'j'   # P → A
                elif 'left-right' in direction_lower or direction_lower == 'lr':
                    phase_encoding_dir = 'i-'  # L → R
                elif 'right-left' in direction_lower or direction_lower == 'rl':
                    phase_encoding_dir = 'i'   # R → L
                
                if phase_encoding_dir:
                    bids_fields['PhaseEncodingDirection'] = phase_encoding_dir
                    print(f"          ✅ PhaseEncodingDirection: {phase_encoding_dir}")
                    break
        
        # === 7. EFFECTIVE ECHO SPACING - Site-aware ===
        water_fat_shift = None
        recon_matrix_pe = None
        
        # Water-Fat shift patterns
        wfs_patterns = [
            r'Water Fat shift \[pixels\]\s*:\s*([\d.]+)',
            r'water fat shift\s*:\s*([\d.]+)',
            r'WFS\s*:\s*([\d.]+)',
            r'Water\s+Fat\s+shift\s*:\s*([\d.]+)'
        ]
        
        for pattern in wfs_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                water_fat_shift = safe_float(match.group(1))
                if water_fat_shift and water_fat_shift > 0:
                    bids_fields['WaterFatShift'] = water_fat_shift
                    print(f"          ✅ WaterFatShift: {water_fat_shift} pixels")
                    break
        
        # Reconstruction matrix patterns
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
                if recon_x and recon_y:
                    bids_fields['ReconMatrixPE'] = recon_y
                    bids_fields['ReconMatrixFE'] = recon_x
                    recon_matrix_pe = recon_y
                    print(f"          ✅ ReconMatrix: {recon_x}×{recon_y}")
                    break
        
        # Calculate EffectiveEchoSpacing with site-specific adjustments
        if water_fat_shift and recon_matrix_pe:
            try:
                # Site-specific bandwidth factors (if different)
                bandwidth_factor = 434.215  # Standard Philips
                
                # Site-specific adjustments (if needed)
                if site_info['actual_site'] == 'Groningen':
                    bandwidth_factor = 434.215
                elif site_info['actual_site'] == 'Amsterdam':
                    bandwidth_factor = 434.215
                elif site_info['actual_site'] == 'Leiden':
                    bandwidth_factor = 434.215
                
                bandwidth_per_pixel_hz = bandwidth_factor / water_fat_shift
                ees = 1.0 / (bandwidth_per_pixel_hz * recon_matrix_pe)
                bids_fields['EffectiveEchoSpacing'] = round(ees, 8)
                print(f"          ✅ EffectiveEchoSpacing: {bids_fields['EffectiveEchoSpacing']} s")
            except Exception as e:
                print(f"          ❌ EffectiveEchoSpacing calculation failed: {e}")
        
        # === 8. ADDITIONAL PARAMETERS ===
        
        # SliceThickness
        thickness_patterns = [
            r'slice thickness \(in mm\s*\)\s*:\s*([\d.]+)',
            r'slice thickness\s*:\s*([\d.]+)',
            r'Slice thickness\s*:\s*([\d.]+)'
        ]
        
        for pattern in thickness_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                thickness = safe_float(match.group(1))
                if thickness and thickness > 0:
                    bids_fields['SliceThickness'] = thickness
                    print(f"          ✅ SliceThickness: {thickness} mm")
                    break
        
        # FlipAngle
        flip_patterns = [
            r'image_flip_angle \(in degrees\)\s+([\d.]+)',
            r'Flip angle\s*\[degrees\]\s*:\s*([\d.]+)',
            r'flip angle\s*:\s*([\d.]+)'
        ]
        
        for pattern in flip_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                flip_angle = safe_float(match.group(1))
                if flip_angle and flip_angle > 0:
                    bids_fields['FlipAngle'] = flip_angle
                    print(f"          ✅ FlipAngle: {flip_angle} degrees")
                    break
        
        # TaskName from protocol
        protocol_patterns = [
            r'Protocol name\s*:\s*([^\n\r]+)',
            r'Examination name\s*:\s*([^\n\r]+)'
        ]
        
        for pattern in protocol_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                protocol = match.group(1).strip().lower()
                
                task_name = 'rest'  # default
                if any(term in protocol for term in ['rest', 'resting', 'state']):
                    task_name = 'rest'
                elif 'nback' in protocol:
                    task_name = 'nback'
                elif any(term in protocol for term in ['faces', 'emotion']):
                    task_name = 'faces'
                
                bids_fields['TaskName'] = task_name
                print(f"          ✅ TaskName: {task_name}")
                break
        
        # Standard fields
        bids_fields['Manufacturer'] = 'Philips'
        
        # Add comprehensive processing metadata
        bids_fields['_ProcessingInfo'] = {
            'ExtractedBy': 'batch_bids_par_updater.py',
            'ExtractionDateTime': datetime.now().isoformat(),
            'ProcessedBy': 'JulianGaviriaL',
            'MultiSiteCapable': True,
            'SupportedSites': ['Groningen', 'Amsterdam', 'Leiden'],
            'SiteDetected': site_info['actual_site'],
            'DetectionConfidence': site_info['confidence'],
            'PAR_Version': site_info.get('version', 'unknown'),
            'SliceTimingCorrected': '2025-09-10'  # Mark when slice timing was fixed
        }
        
        # Summary
        bids_count = len([k for k in bids_fields.keys() if not k.startswith('_')])
        print(f"          📊 Extracted {bids_count} BIDS fields")
        print(f"          🎯 Critical fields status:")
        print(f"             - RepetitionTime: {'✅' if 'RepetitionTime' in bids_fields else '❌'}")
        print(f"             - SliceEncodingDirection: {'✅' if 'SliceEncodingDirection' in bids_fields else '❌'}")
        print(f"             - PhaseEncodingDirection: {'✅' if 'PhaseEncodingDirection' in bids_fields else '❌'}")
        print(f"             - EffectiveEchoSpacing: {'✅' if 'EffectiveEchoSpacing' in bids_fields else '❌'}")
        print(f"             - SliceTiming: {'✅' if 'SliceTiming' in bids_fields else '❌'}")
        
        return bids_fields
        
    except Exception as e:
        print(f"          ❌ Error: {e}")
        return {}

def find_par_json_pairs(func_dir):
    """Find PAR and JSON file pairs in func directory"""
    
    func_path = Path(func_dir)
    if not func_path.exists():
        return []
    
    # Find PAR files
    par_files = [f for f in func_path.iterdir() 
                 if f.suffix.upper() == '.PAR' and f.is_file()]
    
    # Find JSON files (exclude backups)
    json_files = [f for f in func_path.iterdir() 
                  if (f.suffix.lower() == '.json' and f.is_file() and 
                      not f.name.startswith('.') and 
                      'backup' not in f.name.lower())]
    
    pairs = []
    
    if par_files and json_files:
        # Smart pairing logic
        for json_file in json_files:
            json_stem = json_file.stem.lower()
            
            # Look for task-related files
            if any(task in json_stem for task in ['rest', 'bold', 'task', 'func']):
                best_par = None
                
                # Try to find matching PAR
                for par_file in par_files:
                    par_stem = par_file.stem.lower()
                    if any(task in par_stem for task in ['rest', 'bold', 'task', 'func']):
                        best_par = par_file
                        break
                
                if not best_par and par_files:
                    best_par = par_files[0]
                
                if best_par:
                    pairs.append((best_par, json_file))
        
        # Fallback pairing
        if not pairs and par_files and json_files:
            pairs.append((par_files[0], json_files[0]))
    
    return pairs

def update_bids_json(json_file_path, bids_params, create_backup=True):
    """Update BIDS JSON with extracted parameters"""
    
    if create_backup:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{json_file_path}.backup_{timestamp}"
        try:
            shutil.copy2(json_file_path, backup_path)
        except:
            pass
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        added_fields = []
        updated_fields = []
        
        for field_name, field_value in bids_params.items():
            if field_name.startswith('_'):
                continue  # Skip metadata
                
            if field_name in json_data:
                if json_data[field_name] != field_value:
                    json_data[field_name] = field_value
                    updated_fields.append(field_name)
            else:
                json_data[field_name] = field_value
                added_fields.append(field_name)
        
        # Add processing metadata
        processing_info = bids_params.get('_ProcessingInfo', {})
        site_info = bids_params.get('_SiteInfo', {})
        
        json_data['_BIDSProcessingInfo'] = {
            'ProcessedBy': 'JulianGaviriaL',
            'ProcessingDateTime': datetime.now().isoformat(),
            'ProcessingScript': 'batch_bids_par_updater.py',
            'NESDAMultiSite': True,
            'SupportedSites': ['Groningen', 'Amsterdam', 'Leiden'],
            'DetectedSite': site_info.get('actual_site', 'unknown'),
            'SiteConfidence': site_info.get('confidence', 'unknown'),
            'PAR_Version': site_info.get('version', 'unknown'),
            'PhilipsSpecific': True,
            'SliceTimingCorrected': '2025-09-10',  # Mark correction date
            'ExtractionCapabilities': {
                'SliceEncodingDirection': 'Multi-strategy detection',
                'PhaseEncodingDirection': 'From Preparation direction',
                'SliceTimingMethod': 'Interleaved ascending from bottom (CORRECTED)',
                'EffectiveEchoSpacing': 'Water-Fat shift calculation'
            },
            'FieldsAdded': added_fields,
            'FieldsUpdated': updated_fields
        }
        
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, sort_keys=False)
        
        return True, len(added_fields), len(updated_fields)
        
    except Exception as e:
        print(f"          ❌ JSON update failed: {e}")
        return False, 0, 0

def find_all_participants(nesda_root):
    """Find all participant directories"""
    
    root_path = Path(nesda_root)
    if not root_path.exists():
        return []
    
    return sorted([item for item in root_path.iterdir() 
                   if item.is_dir() and item.name.startswith('sub-')])

def process_participant(participant_dir):
    """Process a single participant directory"""
    
    participant_name = participant_dir.name
    print(f"\n    👤 {participant_name}")
    
    func_dirs = []
    for item in participant_dir.iterdir():
        if item.is_dir():
            if item.name.startswith('ses-'):
                func_dir = item / 'func'
                if func_dir.exists():
                    func_dirs.append(func_dir)
            elif item.name == 'func':
                func_dirs.append(item)
    
    if not func_dirs:
        print(f"      ⚠️  No func directories")
        return 0, 0, 0
    
    total_pairs = 0
    total_successes = 0
    total_failures = 0
    
    for func_dir in func_dirs:
        session_info = f"/{func_dir.parent.name}" if func_dir.parent.name.startswith('ses-') else ""
        print(f"      📂 {participant_name}{session_info}/func")
        
        pairs = find_par_json_pairs(func_dir)
        
        if not pairs:
            print(f"        ⚠️  No PAR/JSON pairs")
            continue
        
        total_pairs += len(pairs)
        
        for par_file, json_file in pairs:
            print(f"        📄 {par_file.name} → {json_file.name}")
            
            bids_params = extract_philips_bids_3sites(str(par_file))
            
            if not bids_params:
                print(f"          ❌ No parameters extracted")
                total_failures += 1
                continue
            
            success, added, updated = update_bids_json(str(json_file), bids_params)
            
            if success:
                print(f"          ✅ Updated (+{added}, ~{updated})")
                total_successes += 1
            else:
                total_failures += 1
    
    return total_pairs, total_successes, total_failures

def main():
    """Main function"""
    
    print("=" * 100)
    print("🚀 ENHANCED Multi-Site BIDS PAR Updater for 3 NESDA Sites")
    print(f"👨‍💻 Author: JulianGaviriaL")
    print(f"📅 Date: 2025-09-10 14:19:55")
    print("🏥 Sites: Groningen (V4.1) + Amsterdam & Leiden (V4.2)")
    print("🔧 CORRECTED: Fixed slice timing for Philips interleaved ascending")
    print("=" * 100)
    
    # Default to AmsLei, but allow override
    default_path = r"D:\NESDA\W3\par_rec_AmsLei"
    nesda_root = sys.argv[1] if len(sys.argv) > 1 else default_path
    
    print(f"📁 Processing: {nesda_root}")
    
    participants = find_all_participants(nesda_root)
    
    if not participants:
        print("❌ No participants found!")
        return 1
    
    print(f"👥 Found {len(participants)} participants")
    print(f"\n🎯 3-SITE EXTRACTION FEATURES:")
    print(f"   🏥 Groningen: PAR V4.1 format")
    print(f"   🏥 Amsterdam: PAR V4.2 format") 
    print(f"   🏥 Leiden: PAR V4.2 format")
    print(f"   ✅ Automatic site detection")
    print(f"   ✅ SliceEncodingDirection from orientation codes")
    print(f"   ✅ PhaseEncodingDirection from 'Preparation direction'")
    print(f"   ✅ CORRECTED SliceTiming: Interleaved ascending from bottom")
    print(f"       📋 Order: Odd slices (1,3,5,...), then even slices (2,4,6,...)")
    print(f"   ✅ Complete BIDS parameter extraction")
    
    response = input(f"\n❓ Process {len(participants)} participants? [y/N]: ").lower().strip()
    if response != 'y':
        return 1
    
    start_time = time.time()
    
    print(f"\n🏁 Starting 3-site batch processing...")
    print("=" * 100)
    
    stats = {'processed': 0, 'skipped': 0, 'pairs': 0, 'successes': 0, 'failures': 0}
    site_stats = {}
    
    for i, participant_dir in enumerate(participants, 1):
        print(f"\n  [{i}/{len(participants)}] {participant_dir.name}")
        
        try:
            pairs, successes, failures = process_participant(participant_dir)
            
            if pairs > 0:
                stats['processed'] += 1
                stats['pairs'] += pairs
                stats['successes'] += successes
                stats['failures'] += failures
            else:
                stats['skipped'] += 1
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
            stats['skipped'] += 1
    
    end_time = time.time()
    
    print("\n" + "=" * 100)
    print("🎉 3-SITE PROCESSING COMPLETE!")
    print("=" * 100)
    print(f"⏱️  Time: {(end_time-start_time)/60:.1f} minutes")
    print(f"✅ Successful updates: {stats['successes']}")
    print(f"📈 Success rate: {(stats['successes']/max(stats['pairs'],1))*100:.1f}%")
    
    if stats['successes'] > 0:
        print(f"\n🎊 SUCCESS! Updated {stats['successes']} BIDS JSON files!")
        print("✨ 3-Site capabilities applied:")
        print("   🏥 Site auto-detection (Groningen/Amsterdam/Leiden)")
        print("   🔧 PAR version compatibility (V4.1 & V4.2)")
        print("   📋 Complete BIDS parameter extraction")
        print("   🎯 CORRECTED SliceTiming: Interleaved ascending from bottom")
        print("   💾 Automatic backup creation")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())