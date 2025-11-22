# Execution Guide - Nirikhsan Web Cam Guard Monitoring System

## Quick Start

### 1. Activate Virtual Environment
```powershell
# PowerShell - Navigate to workspace
cd D:\CUDA_Experiments\Git_HUB\Nirikhsan_Web_Cam

# Activate wave_env
& D:\CUDA_Experiments\wave_env\Scripts\Activate.ps1
```

### 2. Run the Application
```powershell
python Basic+Mediapose.py
```

---

## Interface Overview

### Left Panel (Blue Zone) - Control Panel

#### 🔵 Group 1: SYSTEM CONTROLS
- **▶ Start** - Initialize camera feed
- **⏹ Stop** - Terminate camera feed  
- **📸 Snap** - Capture photo (during onboarding)
- **🚪 Exit** - Close application

#### 👮 Group 2: GUARD MANAGEMENT
- **➕ Add** - Create new guard profile (face capture + 4 poses)
- **❌ Remove** - Delete guard and all associated data
- **🔄 Refresh** - Reload available guards from disk

#### 🎯 Group 3: DETECTION MODES
- **🔔 Alert** - Enable alert mode (15-30s timer per guard)
- **🚨 Fugitive** - Search for specific fugitive in live feed
- **🎯 Pro** - Person Re-ID mode (advanced tracking)

#### ⚙️ Group 4: SETTINGS & ACTIONS
- **⏱ Interval** - Set alert timer (opens H:M:S dialog)
- **✋ Action** - Select required action (Hands Up, Sit, Standing, etc.)
- **📋 Select Targets** - Choose which guards to track (dialog-based)
- **🎬 Track Selected** - Start tracking selected guards

### Right Panel (Green Zone) - Preview Panel
- **👤 Tracked Persons** - Shows selected guard thumbnails
- **👮 GUARD** - Large preview of first selected guard
- **🚨 FUGITIVE** - Fugitive preview (when mode active)

---

## Workflow: Adding a New Guard

### Step 1: Click "➕ Add Guard"
- Dialog appears asking for guard name
- Enter name (e.g., "John Smith")

### Step 2: Face Capture (Step 1/5)
- Stand in front of camera
- Green box appears when face detected
- Click **"📸 Snap Photo"** when ready

### Step 3-5: Pose Captures
- **Step 2/5:** Perform "One Hand Raised (Left)"
- **Step 3/5:** Perform "One Hand Raised (Right)"
- **Step 4/5:** Sit down
- **Step 5/5:** Stand up

Each step requires full body visibility (standing back from camera).

### Guard Files Created:
- `guard_profiles/target_John_Smith_face.jpg` - Face image
- `pose_references/John_Smith_poses.json` - Pose landmarks
- `capture_snapshots/John_Smith_capture_*.jpg` - Timestamped captures

---

## Workflow: Tracking Guards

### 1. Select Targets
- Click **"📋 Select Targets"**
- Dialog shows all available guards
- Check/uncheck to select
- Click **"Done"** to confirm

### 2. Configure Alert (Optional)
- Click **"⏱ Interval"**
- Set Hours, Minutes, Seconds
- Example: 0H, 5M, 0S = 300 seconds
- Click **"Set"**

### 3. Set Required Action
- Click **"✋ Action"** dropdown
- Select action: "Hands Up", "Sit", "Standing", etc.

### 4. Start Camera
- Click **"▶ Start"** to begin live feed

### 5. Enable Alert Mode
- Click **"🔔 Alert"** to activate alert mode
- Button changes to "Stop Alert Mode" (red)
- System will:
  - Track selected guards every frame
  - Monitor for required action
  - Sound alert if action not performed within interval
  - Log all actions to CSV

### 6. Stop & Save
- Click **"🔔 Alert"** again to disable
- Click **"⏹ Stop"** to stop camera
- Logs auto-save to `logs/events.csv`

---

## Fugitive Mode

### Setup
1. Click **"🚨 Fugitive"** button
2. File dialog opens - select image of fugitive
3. System extracts face encoding

### During Monitoring
- Live feed searches for fugitive continuously
- If found:
  - Red bounding box around fugitive
  - **15-second alert sound** plays (Fugitive.mp3)
  - Snapshot captured to `alert_snapshots/`
  - CSV log entry created: "FUGITIVE_DETECTED"

---

## Data & Files

### Directory Structure
```
D:\CUDA_Experiments\Git_HUB\Nirikhsan_Web_Cam\
├── Basic+Mediapose.py              # Main application
├── config.json                      # Configuration
├── logs/                            # Logging directory
│   ├── session.log                  # Session log
│   └── events.csv                   # Event database
├── guard_profiles/                  # Guard face images
│   └── target_[Name]_face.jpg
├── pose_references/                 # Pose landmarks
│   └── [Name]_poses.json
├── capture_snapshots/               # Timestamped captures
│   └── [Name]_capture_*.jpg
└── alert_snapshots/                 # Alert snapshots
    └── alert_[Name]_*.jpg
```

### CSV Database Format
```
Timestamp,Name,Action,Status,Image_Path,Confidence
2025-11-21 14:30:45,Guard_1,Hands Up,Action Performed,alert_snapshots/alert_Guard_1_20251121_143045.jpg,0.95
2025-11-21 14:35:12,Guard_2,Sit,Action Not Performed,alert_snapshots/alert_Guard_2_20251121_143512.jpg,0.88
2025-11-21 14:40:00,Guard_3,N/A,Guard Missing,N/A,0.00
2025-11-21 14:42:15,FUGITIVE_Guard_1,FUGITIVE_DETECTED,FUGITIVE ALERT,alert_snapshots/FUGITIVE_Guard_1_20251121_144215.jpg,0.92
```

---

## Configuration (config.json)

Modify behavior by editing `config.json`:

```json
{
  "detection": {
    "min_detection_confidence": 0.5,        // Lower = more detections
    "min_tracking_confidence": 0.5,
    "face_recognition_tolerance": 0.5,     // Lower = stricter matching
    "re_detect_interval": 60                // Frames between re-detection
  },
  "alert": {
    "default_interval_seconds": 10,
    "alert_cooldown_seconds": 2.5
  },
  "performance": {
    "gui_refresh_ms": 30,
    "pose_buffer_size": 12,                 // Pose averaging window
    "frame_skip_interval": 2,
    "enable_frame_skipping": true,
    "min_buffer_for_classification": 8
  },
  "logging": {
    "log_directory": "logs",
    "max_log_size_mb": 10,
    "auto_flush_interval": 50               // Log entries before save
  },
  "storage": {
    "alert_snapshots_dir": "alert_snapshots",
    "snapshot_retention_days": 30,          // Auto-delete old snapshots
    "guard_profiles_dir": "guard_profiles",
    "pose_references_dir": "pose_references",
    "capture_snapshots_dir": "capture_snapshots"
  }
}
```

---

## Troubleshooting

### Camera Not Starting
- **Issue:** "⏹ Stop" button remains disabled, no camera feed
- **Solution:** Check camera permissions in Windows Settings
- Verify `cv2` and `mediapipe` are installed in `wave_env`

### No Targets Available
- **Issue:** "Select Targets" dialog shows empty list
- **Solution:** Add at least one guard using "➕ Add" button
- Ensure face is clearly visible during capture

### Dynamic Bounding Box Not Showing
- **Issue:** Box appears but doesn't tightly frame person
- **Solution:** 
  - Step back so full body is visible
  - Improve lighting for better pose detection
  - Ensure MediaPipe pose model loads correctly

### Alert Sound Not Playing
- **Issue:** No sound during alert or fugitive detection
- **Solution:**
  1. Check audio files exist:
     - `D:\CUDA_Experiments\Git_HUB\Nirikhsan_Web_Cam\emergency-siren-351963.mp3`
     - `D:\CUDA_Experiments\Git_HUB\Nirikhsan_Web_Cam\Fugitive.mp3`
  2. Verify `pygame` or `pydub` installed: `pip install pygame`
  3. Check system volume not muted

### Multiple Guards Confusing (Bounding Box Mixup)
- **Issue:** Guards merge into single box
- **Solution:** Stand further apart (minimum 2 meters)
- Add more guards to increase distinction
- Improve lighting to aid face recognition

### CSV Logging Not Saving
- **Issue:** `logs/events.csv` not created or empty
- **Solution:**
  1. Enable alert mode (click "🔔 Alert")
  2. Perform actions or wait for timeouts
  3. Stop camera (click "⏹ Stop")
  4. Check `logs/` directory created and writable

---

## Performance Tips

1. **Optimize Detection Speed:**
   - Increase `frame_skip_interval` to 3-4 (skip more frames)
   - Reduce pose buffer size to 8
   - Lower `min_detection_confidence` to 0.4

2. **Improve Accuracy:**
   - Ensure good lighting (natural light recommended)
   - Clear background (reduce clutter)
   - Full body in frame for pose detection

3. **Memory Management:**
   - Set `snapshot_retention_days` to clean old files
   - Rotate logs periodically
   - Monitor `logs/` directory size

---

## Advanced: Manual Configuration

### Change Alert Duration
Edit line in `set_alert_interval_advanced()` default value:
```python
s_var = ctk.StringVar(value="10")  # Change 10 to your default seconds
```

### Change Alert Sound
Modify `play_siren_sound()` call - change `sound_file` parameter:
```python
status["alert_sound_thread"] = play_siren_sound(
    stop_event=status["alert_stop_event"], 
    duration_seconds=15,
    sound_file="custom_alert.mp3"  # Change filename
)
```

### Adjust Pose Detection Confidence
Edit config.json:
```json
"min_detection_confidence": 0.6  // Higher = more strict
```

---

## Support & Documentation

- **Main Script:** `Basic+Mediapose.py`
- **Improvements:** `IMPROVEMENTS_SUMMARY.md` (this directory)
- **Execution Guide:** `EXECUTION_GUIDE.md` (this file)
- **Config:** `config.json`
- **Logs:** `logs/events.csv` (runtime database)

---

**Last Updated:** November 21, 2025  
**Application Version:** Enhanced Build  
**Python Environment:** v3.11.9 (wave_env)
