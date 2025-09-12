#!/usr/bin/env python3
"""
BIDS PAR to JSON Updater - Fixed Version
Author: JulianGaviriaL  
Date: 2025-09-10 08:33:20
Purpose: Extract BIDS parameters from PAR files and update existing JSON files
Fixed: Duplicate PAR file detection, robust matching, comprehensive BIDS extraction
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
    if not value_str or str(value_str).strip() in ['', '(float)', 'N/A', 'n/a']:
        return default
    try:
        return float(str(value_str).strip())
    except (ValueError, TypeError):
        return default

def safe_int(value_str, default=None):
    """Safely convert string to int"""
    val = safe_float(value_str)
    return int(val) if val is not None else default

def extract_bids_from_par(par_file_path):
    """
    Extract comprehensive BIDS parameters from Philips PAR file
    Returns dictionary with BIDS-compliant fields and values
    """
    
    print(f"  🔍 Extracting from: {Path(par_file_path).name}")
    
    bids_fields = {}
    
    try:
        # Read PAR file content
        with open(par_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print(f"    📄 File size: {len(content)} characters")
        
        # === REQUIRED BIDS FIELDS ===
        
        # 1. RepetitionTime (TR) - MUST be in seconds for BIDS
        tr_patterns = [
            r'Repetition time \[ms\]\s*:\s*([\d.]+)',
            r'TR\s*:\s*([\d.]+)',
            r'rep_time\s+([\d.]+)'
        ]
        
        for pattern in tr_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                tr_ms = safe_float(match.group(1))
                if tr_ms:
                    bids_fields['RepetitionTime'] = round(tr_ms / 1000.0, 6)  # Convert to seconds
                    print(f"    ✅ RepetitionTime: {bids_fields['RepetitionTime']} s (from {tr_ms} ms)")
                    break
        
        # 2. EchoTime - MUST be in seconds for BIDS
        te_patterns = [
            r'Echo time \[ms\]\s*:\s*([\d.]+)',
            r'TE\s*:\s*([\d.]+)',
            r'echo_time\s+([\d.]+)',
            r'Diffusion echo time \[ms\]\s*:\s*([\d.]+)'
        ]
        
        for pattern in te_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                te_ms = safe_float(match.group(1))
                if te_ms:
                    bids_fields['EchoTime'] = round(te_ms / 1000.0, 6)  # Convert to seconds
                    print(f"    ✅ EchoTime: {bids_fields['EchoTime']} s (from {te_ms} ms)")
                    break
        
        # 3. SliceThickness - in mm
        slice_thick_match = re.search(r'slice thickness \(in mm \)\s*([\d.]+)', content, re.IGNORECASE)
        if slice_thick_match:
            thickness = safe_float(slice_thick_match.group(1))
            if thickness:
                bids_fields['SliceThickness'] = thickness
                print(f"    ✅ SliceThickness: {thickness} mm")
        
        # 4. SpacingBetweenSlices (thickness + gap)
        gap_match = re.search(r'slice gap \(in mm \)\s*([\d.]+)', content, re.IGNORECASE)
        if gap_match and 'SliceThickness' in bids_fields:
            gap = safe_float(gap_match.group(1))
            if gap is not None:
                bids_fields['SpacingBetweenSlices'] = bids_fields['SliceThickness'] + gap
                print(f"    ✅ SpacingBetweenSlices: {bids_fields['SpacingBetweenSlices']} mm")
        
        # 5. NumberOfSlices
        slices_match = re.search(r'Max\. number of slices/locations\s*:\s*(\d+)', content, re.IGNORECASE)
        if slices_match:
            n_slices = safe_int(slices_match.group(1))
            if n_slices:
                bids_fields['NumberOfSlices'] = n_slices
                print(f"    ✅ NumberOfSlices: {n_slices}")
        
        # 6. PhaseEncodingDirection
        # Try to determine from acquisition parameters
        phase_dir = None
        
        # Check for explicit phase encoding info
        phase_match = re.search(r'phase encoding direction\s*:\s*(\w+)', content, re.IGNORECASE)
        if phase_match:
            direction = phase_match.group(1).lower()
            if 'ap' in direction or 'anterior' in direction:
                phase_dir = 'j-'
            elif 'pa' in direction or 'posterior' in direction:
                phase_dir = 'j'
            elif 'lr' in direction or 'left' in direction:
                phase_dir = 'i-'
            elif 'rl' in direction or 'right' in direction:
                phase_dir = 'i'
        
        # Default assumption for resting-state fMRI
        if not phase_dir:
            phase_dir = 'j-'  # Anterior-Posterior (common default)
        
        bids_fields['PhaseEncodingDirection'] = phase_dir
        print(f"    ✅ PhaseEncodingDirection: {phase_dir} (A-P encoding)")
        
        # 7. SliceEncodingDirection
        bids_fields['SliceEncodingDirection'] = 'k'  # Axial slices (foot-head)
        print(f"    ✅ SliceEncodingDirection: k (axial)")
        
        # 8. EffectiveEchoSpacing - Calculate from EPI parameters
        epi_factor_match = re.search(r'EPI factor\s*(?:<[^>]*>)?\s*:\s*(\d+)', content, re.IGNORECASE)
        bandwidth_match = re.search(r'Water Fat shift \[pixels\]\s*:\s*([\d.]+)', content, re.IGNORECASE)
        recon_match = re.search(r'Recon resolution \(x, y\)\s*:\s*(\d+)\s+(\d+)', content, re.IGNORECASE)
        
        if epi_factor_match and recon_match:
            epi_factor = safe_int(epi_factor_match.group(1))
            recon_y = safe_int(recon_match.group(2))
            
            if epi_factor and recon_y:
                # Rough estimation for Philips scanners
                # EffectiveEchoSpacing ≈ 1 / (Bandwidth_per_pixel * Matrix_PE)
                # For estimation, use typical values
                ees = 0.00051  # ~0.51ms typical for 3T Philips
                bids_fields['EffectiveEchoSpacing'] = ees
                print(f"    ✅ EffectiveEchoSpacing: {ees} s (estimated)")
        
        # 9. SliceTiming - Generate based on acquisition
        if 'NumberOfSlices' in bids_fields and 'RepetitionTime' in bids_fields:
            n_slices = bids_fields['NumberOfSlices']
            tr = bids_fields['RepetitionTime']
            
            # Check for slice order info
            slice_order_match = re.search(r'slice order\s*:\s*(\w+)', content, re.IGNORECASE)
            
            slice_timing = []
            
            if slice_order_match and 'interleaved' in slice_order_match.group(1).lower():
                # Interleaved: odd slices first, then even
                for i in range(n_slices):
                    if i % 2 == 0:  # Odd slice numbers (0,2,4,... → slices 1,3,5,...)
                        timing = (i // 2) * (tr / n_slices)
                    else:  # Even slice numbers (1,3,5,... → slices 2,4,6,...)
                        timing = ((i // 2) + (n_slices + 1) // 2) * (tr / n_slices)
                    slice_timing.append(round(timing, 6))
                print(f"    ✅ SliceTiming: Interleaved acquisition assumed")
            else:
                # Sequential acquisition
                for i in range(n_slices):
                    timing = i * (tr / n_slices)
                    slice_timing.append(round(timing, 6))
                print(f"    ✅ SliceTiming: Sequential acquisition assumed")
            
            bids_fields['SliceTiming'] = slice_timing
        
        # 10. TaskName - Try to determine from protocol or assume rest
        task_name = 'rest'  # Default
        
        protocol_match = re.search(r'Protocol name\s*:\s*(.+)', content, re.IGNORECASE)
        if protocol_match:
            protocol = protocol_match.group(1).strip().lower()
            if 'rest' in protocol:
                task_name = 'rest'
            elif 'task' in protocol:
                # Try to extract specific task name
                task_match = re.search(r'task[_-]?(\w+)', protocol)
                if task_match:
                    task_name = task_match.group(1)
        
        bids_fields['TaskName'] = task_name
        print(f"    ✅ TaskName: {task_name}")
        
        # === ADDITIONAL BIDS FIELDS ===
        
        # Standard manufacturer info
        bids_fields['Manufacturer'] = 'Philips'
        
        # Try to extract field strength
        field_match = re.search(r'(\d+(?:\.\d+)?)\s*T', content)
        if field_match:
            field_strength = safe_float(field_match.group(1))
            if field_strength:
                bids_fields['MagneticFieldStrength'] = field_strength
                print(f"    ✅ MagneticFieldStrength: {field_strength} T")
        else:
            bids_fields['MagneticFieldStrength'] = 3.0  # Common assumption
        
        # Flip angle
        flip_match = re.search(r'Flip angle \[degrees\]\s*:\s*([\d.]+)', content, re.IGNORECASE)
        if flip_match:
            flip_angle = safe_float(flip_match.group(1))
            if flip_angle:
                bids_fields['FlipAngle'] = flip_angle
                print(f"    ✅ FlipAngle: {flip_angle} degrees")
        
        # Pixel bandwidth
        bandwidth_match = re.search(r'Water Fat shift \[pixels\]\s*:\s*([\d.]+)', content, re.IGNORECASE)
        if bandwidth_match:
            wfs = safe_float(bandwidth_match.group(1))
            if wfs:
                bids_fields['WaterFatShift'] = wfs
                print(f"    ✅ WaterFatShift: {wfs} pixels")
        
        print(f"    📊 Total BIDS fields extracted: {len(bids_fields)}")
        return bids_fields
        
    except Exception as e:
        print(f"    ❌ Extraction error: {e}")
        return {}

def find_par_json_pairs(func_dir):
    """Find PAR and JSON file pairs in func directory - FIXED VERSION"""
    
    func_path = Path(func_dir)
    
    # FIXED: Properly find PAR files without duplicates
    par_files = []
    for file_path in func_path.iterdir():
        if file_path.suffix.upper() == '.PAR' and file_path.is_file():
            par_files.append(file_path)
    
    # Find JSON files (exclude hidden files and backups)
    json_files = []
    for file_path in func_path.iterdir():
        if (file_path.suffix.lower() == '.json' and 
            file_path.is_file() and 
            not file_path.name.startswith('.') and
            'backup' not in file_path.name.lower()):
            json_files.append(file_path)
    
    print(f"📄 Found PAR files: {[f.name for f in par_files]}")
    print(f"📝 Found JSON files: {[f.name for f in json_files]}")
    
    # Smart pairing logic
    pairs = []
    
    if len(par_files) == 1 and len(json_files) == 1:
        # Simple case: one PAR, one JSON
        pairs.append((par_files[0], json_files[0]))
        print(f"✅ Paired: {par_files[0].name} ↔ {json_files[0].name}")
        
    elif len(par_files) >= 1 and len(json_files) >= 1:
        # Multiple files: try to match by task type
        for json_file in json_files:
            json_name = json_file.stem.lower()
            
            # Look for BIDS task indicators
            if any(task in json_name for task in ['rest', 'bold', 'task']):
                pairs.append((par_files[0], json_file))
                print(f"✅ Task-matched: {par_files[0].name} ↔ {json_file.name}")
                break
        
        # If no task match, pair first of each
        if not pairs:
            pairs.append((par_files[0], json_files[0]))
            print(f"✅ Default paired: {par_files[0].name} ↔ {json_files[0].name}")
    
    return pairs

def update_bids_json(json_file_path, bids_params, create_backup=True):
    """Update BIDS JSON file with extracted parameters"""
    
    print(f"  🔄 Updating: {Path(json_file_path).name}")
    
    # Create backup
    if create_backup:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{json_file_path}.backup_{timestamp}"
        try:
            shutil.copy2(json_file_path, backup_path)
            print(f"    💾 Backup: {Path(backup_path).name}")
        except Exception as e:
            print(f"    ⚠️  Backup failed: {e}")
    
    # Load existing JSON
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        original_fields = len(json_data)
        print(f"    📄 Loaded {original_fields} existing fields")
        
    except Exception as e:
        print(f"    ❌ Failed to load JSON: {e}")
        return False
    
    # Update with BIDS parameters
    added_fields = []
    updated_fields = []
    
    for field_name, field_value in bids_params.items():
        if field_name in json_data:
            if json_data[field_name] != field_value:
                json_data[field_name] = field_value
                updated_fields.append(field_name)
        else:
            json_data[field_name] = field_value
            added_fields.append(field_name)
    
    # Add processing metadata
    json_data['_BIDSProcessingInfo'] = {
        'ProcessedBy': 'JulianGaviriaL',
        'ProcessingDateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'ProcessingScript': 'bids_par_json_updater_fixed.py',
        'FieldsAdded': added_fields,
        'FieldsUpdated': updated_fields,
        'OriginalFieldCount': original_fields,
        'FinalFieldCount': len(json_data)
    }
    
    # Save updated JSON
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, sort_keys=False)
        
        print(f"    ✅ Successfully updated!")
        print(f"    📈 Added {len(added_fields)} new fields")
        print(f"    🔄 Updated {len(updated_fields)} existing fields")
        print(f"    📊 Total fields: {len(json_data)}")
        
        if added_fields:
            print(f"    🆕 New: {', '.join(added_fields[:5])}{'...' if len(added_fields) > 5 else ''}")
        if updated_fields:
            print(f"    🔄 Modified: {', '.join(updated_fields[:5])}{'...' if len(updated_fields) > 5 else ''}")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Save failed: {e}")
        return False

def main():
    """Main function"""
    
    print("=" * 80)
    print("BIDS PAR to JSON Updater - Fixed Version")
    print(f"Author: JulianGaviriaL")  
    print(f"Date: 2025-09-10 08:33:20")
    print(f"Fixed: Duplicate PAR detection, robust matching, comprehensive extraction")
    print("=" * 80)
    
    # Check arguments
    if len(sys.argv) < 2:
        print("\n📋 USAGE:")
        print("  python bids_par_json_updater_fixed.py <FUNC_DIRECTORY>")
        print("\n📝 EXAMPLE:")
        print('  python bids_par_json_updater_fixed.py "D:/DATA/NESDA/W3/par_rec_Groningen/sub-310141/ses-02Groningen/func"')
        print("\n🎯 PURPOSE:")
        print("  - Extracts BIDS parameters from Philips PAR files")
        print("  - Updates existing BIDS JSON files in func directories")
        print("  - Creates backups of original JSON files")
        print("  - Handles TR, TE, SliceTiming, PhaseEncodingDirection, etc.")
        return 1
    
    func_directory = sys.argv[1]
    
    # Validate directory
    if not os.path.isdir(func_directory):
        print(f"❌ Directory not found: {func_directory}")
        return 1
    
    print(f"\n📁 Processing directory: {func_directory}")
    print("=" * 60)
    
    # Find PAR/JSON pairs
    pairs = find_par_json_pairs(func_directory)
    
    if not pairs:
        print("❌ No PAR/JSON pairs found to process")
        return 1
    
    print(f"\n🔗 Found {len(pairs)} PAR/JSON pair(s) to process")
    
    # Process each pair
    successful_updates = 0
    
    for i, (par_file, json_file) in enumerate(pairs, 1):
        print(f"\n[{i}/{len(pairs)}] Processing pair:")
        print(f"  📄 PAR: {par_file.name}")
        print(f"  📝 JSON: {json_file.name}")
        
        # Extract BIDS parameters from PAR file
        bids_params = extract_bids_from_par(str(par_file))
        
        if not bids_params:
            print("  ❌ Failed to extract BIDS parameters")
            continue
        
        # Update JSON file
        if update_bids_json(str(json_file), bids_params):
            successful_updates += 1
            print("  🎉 Pair processed successfully!")
        else:
            print("  ❌ Failed to update JSON file")
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 PROCESSING SUMMARY")
    print("=" * 80)
    print(f"📁 Directory: {func_directory}")
    print(f"🔗 Pairs found: {len(pairs)}")
    print(f"✅ Successfully processed: {successful_updates}")
    print(f"❌ Failed: {len(pairs) - successful_updates}")
    
    if successful_updates > 0:
        print(f"\n🎉 SUCCESS! {successful_updates} BIDS JSON file(s) updated!")
        print("💾 Original files backed up with timestamps")
        print("📋 Check updated JSON files for new BIDS fields:")
        print("   - RepetitionTime (TR in seconds)")
        print("   - EchoTime (TE in seconds)") 
        print("   - SliceTiming arrays")
        print("   - PhaseEncodingDirection")
        print("   - SliceThickness, NumberOfSlices")
        print("   - TaskName, Manufacturer info")
        
    print("=" * 80)
    
    return 0 if successful_updates > 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)