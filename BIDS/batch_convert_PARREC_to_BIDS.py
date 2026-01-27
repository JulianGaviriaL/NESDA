#!/usr/bin/env python3
"""
BIDS-convert subject 500518 (PAR/REC to NIfTI + JSON)
This script converts PAR/REC files (Philips MRI format) to
BIDS format using dcm2niix. It:Converts specific PAR/REC files from subject 500518
Only keeps EPI_REST (functional/resting-state scan) and B0 (fieldmap for distortion correction)
Outputs organized NIfTI (.nii.gz) and JSON files in BIDS structure
"""
from pathlib import Path
import json
import shutil
import subprocess
import re

# ---------- USER SETTINGS ----------------------------------------------------
par_root  = Path("D:/NESDA/W6/PAR_REC/500518")      # where the PAR/REC live
bids_root = Path("D:/NESDA/W6/BIDS_W3_v2")          # top-level BIDS folder
sub       = "sub-500518"
ses       = "ses-03"
dcm2niix_path = r"D:\software\dcm2niix\dcm2niix.exe"  # full path to dcm2niix
# -----------------------------------------------------------------------------

(bids_root / sub / ses / "func").mkdir(parents=True, exist_ok=True)
(bids_root / sub / ses / "fmap").mkdir(parents=True, exist_ok=True)

def par2nii(par: Path, out_dir: Path, prefix: str):
    """Convert PAR/REC to NIfTI + JSON via dcm2niix."""
    cmd = [
        dcm2niix_path,
        "-o", str(out_dir),
        "-f", prefix,
        "-z", "y",
        str(par)
    ]
    subprocess.run(cmd, check=True)
    return out_dir / f"{prefix}.nii.gz", out_dir / f"{prefix}.json"

# 1 Functional scan -----------------------------------------------------------
epi_par = par_root / "500518_3_EPI_REST_5_1.PAR"
if epi_par.exists():
    bold_nii, bold_json = par2nii(
        epi_par,
        bids_root / sub / ses / "func",
        f"{sub}_{ses}_task-rest_bold"
    )
    meta = json.loads(bold_json.read_text())
    meta["TaskName"] = "rest"
    bold_json.write_text(json.dumps(meta, indent=4))
    print(f"Converted func: {bold_nii.name}")

# 2 B0 field-map --------------------------------------------------------------
bo_par = par_root / "500518_3_B0_4_1.PAR"
if bo_par.exists():
    ph_nii, ph_json = par2nii(
        bo_par,
        bids_root / sub / ses / "fmap",
        f"{sub}_{ses}_phasediff"
    )
    # Rename magnitude images produced by dcm2niix
    for src in ph_nii.parent.glob("*magnitude*.nii.gz"):
        new_name = src.name.replace("magnitude", f"{sub}_{ses}_magnitude")
        src.rename(src.with_name(new_name))
        print(f"Converted fmap: {new_name}")

print("\nBIDS conversion finished - validate with bids-validator")
