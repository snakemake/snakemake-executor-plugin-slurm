#!/usr/bin/env python3
"""
Post-build script to remove unwanted files from the wheel.
Run this after `poetry build` to clean up the wheel.
"""
import os
import shutil
import zipfile
import tempfile
from pathlib import Path


def cleanup_wheel():
    """Remove unwanted .py and .c files from the wheel, keeping only __init__.py and .so files."""
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("No dist/ directory found")
        return
    
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        print("No wheel files found in dist/")
        return
    
    for wheel_file in wheels:
        print(f"Cleaning up {wheel_file.name}...")
        
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            new_wheel = tmpdir / wheel_file.name
            
            files_to_keep = []
            files_to_remove = []
            
            # Read the wheel and filter files
            with zipfile.ZipFile(wheel_file, 'r') as zin:
                for item in zin.infolist():
                    # Keep only __init__.py and .so files in the package directory
                    if item.filename.startswith('snakemake_executor_plugin_slurm/'):
                        basename = os.path.basename(item.filename)
                        # Remove .py files (except __init__.py), .c files, and __pycache__
                        if (basename.endswith('.py') and basename != '__init__.py') or \
                           basename.endswith('.c') or \
                           '__pycache__' in item.filename:
                            files_to_remove.append(item.filename)
                            continue
                    files_to_keep.append(item)
            
            # Write the cleaned wheel
            with zipfile.ZipFile(wheel_file, 'r') as zin:
                with zipfile.ZipFile(new_wheel, 'w', zipfile.ZIP_DEFLATED) as zout:
                    for item in files_to_keep:
                        zout.writestr(item, zin.read(item.filename))
            
            # Replace original wheel with cleaned version
            shutil.move(str(new_wheel), str(wheel_file))
            
            if files_to_remove:
                print(f"Removed: {len(files_to_remove)} files")
                for f in files_to_remove:
                    print(f"  - {f}")
            else:
                print("No files to remove")
        
        print(f"✓ Cleaned {wheel_file.name}")


if __name__ == "__main__":
    cleanup_wheel()
