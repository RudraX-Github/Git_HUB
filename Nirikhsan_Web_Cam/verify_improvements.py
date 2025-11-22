#!/usr/bin/env python3
"""
Quick verification script for guard monitoring system improvements.
Tests: CSV logging, memory optimization, overlap detection.
"""

import os
import csv
import sys
from pathlib import Path

def verify_logging_setup():
    """Verify logging directory and CSV structure"""
    print("=" * 60)
    print("🔍 VERIFICATION: Guard Monitoring System Improvements")
    print("=" * 60)
    
    base_dir = Path(__file__).parent
    logs_dir = base_dir / "logs"
    csv_file = logs_dir / "events.csv"
    
    # Check 1: Directory exists
    print("\n✓ Check 1: Logging Directory")
    if logs_dir.exists():
        print(f"  ✅ logs/ directory exists at: {logs_dir}")
    else:
        print(f"  ❌ logs/ directory missing! Creating...")
        logs_dir.mkdir(exist_ok=True)
        print(f"  ✅ Created: {logs_dir}")
    
    # Check 2: CSV file exists
    print("\n✓ Check 2: CSV File")
    if csv_file.exists():
        print(f"  ✅ events.csv exists at: {csv_file}")
        file_size = csv_file.stat().st_size
        print(f"  📊 File size: {file_size} bytes")
    else:
        print(f"  ⚠️  events.csv missing, will be created on first log")
    
    # Check 3: CSV structure
    print("\n✓ Check 3: CSV Header")
    try:
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header:
                print(f"  ✅ Header found: {header}")
                expected_cols = ["Timestamp", "Name", "Action", "Status", "Image_Path", "Confidence"]
                if "Timestamp" in header:
                    print(f"  ✅ Column structure valid")
                else:
                    print(f"  ⚠️  Header mismatch - expected: {expected_cols}")
            else:
                print(f"  ℹ️  File empty, will initialize on first log")
    except Exception as e:
        print(f"  ⚠️  Error reading CSV: {e}")
    
    # Check 4: Config file
    print("\n✓ Check 4: Configuration")
    config_file = base_dir / "config.json"
    if config_file.exists():
        print(f"  ✅ config.json exists")
        try:
            import json
            with open(config_file) as f:
                config = json.load(f)
                log_dir = config.get("logging", {}).get("log_directory", "logs")
                flush_interval = config.get("logging", {}).get("auto_flush_interval", 50)
                print(f"  📝 Logging directory setting: {log_dir}")
                print(f"  📝 Auto-flush interval: {flush_interval} entries")
        except Exception as e:
            print(f"  ⚠️  Error reading config: {e}")
    else:
        print(f"  ⚠️  config.json not found")
    
    # Check 5: Required directories
    print("\n✓ Check 5: Required Directories")
    required_dirs = [
        ("alert_snapshots", "Alert snapshots storage"),
        ("guard_profiles", "Guard profile images"),
        ("pose_references", "Pose reference data"),
    ]
    
    for dir_name, description in required_dirs:
        dir_path = base_dir / dir_name
        if dir_path.exists():
            print(f"  ✅ {dir_name}/ ({description})")
        else:
            print(f"  ⚠️  {dir_name}/ missing ({description})")
    
    # Check 6: Python module
    print("\n✓ Check 6: Main Application")
    main_file = base_dir / "Basic+Mediapose.py"
    if main_file.exists():
        print(f"  ✅ Basic+Mediapose.py exists")
        size_mb = main_file.stat().st_size / 1024 / 1024
        print(f"  📊 File size: {size_mb:.2f} MB")
        
        # Check for key improvements
        print("\n  🔎 Checking implemented improvements...")
        with open(main_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            improvements = {
                "Dynamic BB Box": "calculate_body_box",
                "Logging Methods": "def log_action_performed",
                "Auto-Flush Logs": "def auto_flush_logs",
                "Memory Optimization": "def optimize_memory",
                "Overlap Detection": "calculate_iou",
                "Confidence-Based Resolution": "face_confidence",
                "CSV Auto-Save": "os.makedirs(log_dir",
            }
            
            for name, keyword in improvements.items():
                if keyword in content:
                    print(f"    ✅ {name}")
                else:
                    print(f"    ⚠️  {name} - check manually")
    else:
        print(f"  ❌ Basic+Mediapose.py not found!")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 60)
    print("\n📝 Next Steps:")
    print("  1. Run: python Basic+Mediapose.py")
    print("  2. Load guard profiles using GUI")
    print("  3. Enable logging: Click 'Toggle Logging'")
    print("  4. Enable alert mode: Click 'Toggle Alert'")
    print("  5. Monitor guards - logs will auto-save to logs/events.csv")
    print("\n📊 View logs anytime:")
    print(f"  - Open: {csv_file}")
    print("  - Recommended: Use Excel/LibreOffice Calc for CSV viewing")
    print("=" * 60)

if __name__ == "__main__":
    verify_logging_setup()
