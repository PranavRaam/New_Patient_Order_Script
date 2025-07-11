#!/usr/bin/env python3
"""
Cleanup temporary files created during Azure setup
"""
import os
import shutil

def cleanup():
    """Remove temporary files and directories"""
    files_to_remove = [
        "download_training_samples.py",
        "cleanup_temp_files.py"
    ]
    
    dirs_to_remove = [
        "azure_training_samples"  # Remove after uploading to Azure
    ]
    
    print("🧹 Cleaning up temporary files...")
    
    # Remove files
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✓ Removed {file_path}")
        else:
            print(f"⚠ File not found: {file_path}")
    
    # Remove directories
    for dir_path in dirs_to_remove:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"✓ Removed directory {dir_path}")
        else:
            print(f"⚠ Directory not found: {dir_path}")
    
    print("\n✅ Cleanup complete!")
    print("📋 Keep Azure_Setup_Guide.md for reference")

if __name__ == "__main__":
    cleanup() 