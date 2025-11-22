# Basic+Mediapose.py Modifications Summary

## Overview
Successfully integrated tracking logic, sleeping alert, action alert, and stillness alert from `Basic_v5.py` into `Basic+Mediapose.py` with full support for multiple monitoring modes.

## Changes Made

### 1. **Added Monitoring Mode Variables** (Line ~765-770)
   - `self.monitor_mode_var`: StringVar to store monitoring mode selection
   - `self.sleep_alert_delay_seconds`: Float for configurable sleep alert delay (default: 1.5s)
   - Initialized with "All Alerts (Action + Sleep)" as default mode

### 2. **Updated Targets Status Initialization** (Line ~1392)
   - Added sleep detection fields to `targets_status` dictionary:
     - `eye_counter_closed`: Counter for consecutive frames with closed eyes
     - `ear_threshold`: Eye Aspect Ratio threshold (starts at 0.22)
     - `open_ear_baseline`: Baseline for open eye EAR (starts at 0.30)
     - `is_sleeping`: Boolean flag for sleep state

### 3. **Added UI Controls** (Line ~963-970)
   - **Monitoring Mode Dropdown**: Select from:
     - "All Alerts (Action + Sleep)"
     - "Action Alerts Only"
     - "Sleeping Alerts Only"
   - **Sleep Timer Button**: Configurable button to set sleep alert delay

### 4. **Added Helper Function** (Line ~343-369)
   - `calculate_ear(landmarks, width, height)`: Calculates Eye Aspect Ratio
     - Uses 12 eye landmarks (6 per eye) for accurate detection
     - Returns averaged EAR for both eyes

### 5. **Added Sleep Alert Detection Method** (Line ~1556-1563)
   - `set_sleep_interval()`: Allows user to configure sleep detection delay
   - Range: 0.1 to 10.0 seconds
   - Updates button label with current setting

### 6. **Integrated Sleeping Alert Logic** (Line ~2630-2690)
   - **EAR-based Detection**: Monitors eye openness using Eye Aspect Ratio
   - **Adaptive Calibration**: 
     - Hard floor at 0.20 EAR threshold
     - Only recalibrates baseline when eyes are wide open (>0.35)
     - Prevents system from learning "closed eyes" as normal
   - **Dynamic Frame Calculation**: Converts delay seconds to frames based on FPS
   - **Visual Alerts**:
     - Thick red border (6px) around sleeping person's face
     - Center screen flashing "WAKE UP!" warning
   - **Audio Alert**: 10-second siren alert
   - **CSV Logging**: Records EAR value when sleeping detected

### 7. **Enhanced Action Alert Logic** (Line ~2737-2756)
   - Respects `monitoring_mode` setting:
     - Only triggers in "All Alerts (Action + Sleep)" or "Action Alerts Only"
   - Checks if person is NOT sleeping before alert reset
   - **Alert Stopping**: 
     - Stops siren when required action is performed
     - Stops siren from sleep alerts (both are independent)
   - Prevents duplicate logging with rate limiting (60s per target)

### 8. **Updated Stillness Alert Logic** (Line ~2829-2878)
   - **Monitoring Mode Check**: Only active in "All Alerts (Action + Sleep)" or "Action Alerts Only"
   - **Timeout Detection**: 
     - Triggers when person doesn't perform action within `alert_interval`
     - 2.5s cooldown between consecutive alerts
   - **Alert Sound**: 30-second siren with stop event capability
   - **Snapshot Capture**: Rate-limited to one per minute
   - **CSV Logging**: 
     - Records "ALERT TRIGGERED" or "ALERT CONTINUED"
     - Distinguishes between visible and missing targets

### 9. **Added Monitoring Mode Context** (Line ~2605-2606)
   - Retrieves `monitor_mode` value at start of main processing loop
   - Makes it available to both sleeping alert and action alert logic
   - Ensures consistent behavior across all three alert types

## Alert Behavior Summary

### Three Independent Alert Types:

**1. Sleeping Alert** (Monitor Mode: "All Alerts" or "Sleeping Alerts Only")
   - Triggers: Eyes closed > N seconds
   - Visual: Red border + center screen flashing
   - Audio: 10-second siren
   - Stops: Cannot be stopped (must wake up to reset)

**2. Action Alert** (Monitor Mode: "All Alerts" or "Action Alerts Only")
   - Triggers: When person performs required action
   - Audio: Stops immediately when action detected
   - Logging: One entry per action performance

**3. Stillness Alert** (Monitor Mode: "All Alerts" or "Action Alerts Only")
   - Triggers: Person doesn't perform action for `alert_interval` seconds
   - Visual: Status countdown on screen (green > yellow > red)
   - Audio: 30-second siren
   - Stops: Action is performed OR sleep detected
   - Logging: Tracks alert triggering and missing persons

## Key Features Preserved from Basic_v5.py

✅ Tracker initialization and updates with stability checks
✅ Multi-target face detection and matching (cost matrix)
✅ Overlap resolution with confidence weighting
✅ Dynamic body box calculation from face detection
✅ EAR-based sleeping detection with adaptive calibration
✅ Pose classification with buffer-based consistency
✅ CSV event logging with rate limiting
✅ Screenshot capture for alert events
✅ Audio alerts with stop event handling
✅ Alert mode toggle with automatic logging
✅ All three alert types independently configurable

## Testing Checklist

- [ ] Start camera and add guards
- [ ] Test "All Alerts (Action + Sleep)" mode
  - [ ] Person sleeps → red border + flashing warning + 10s siren
  - [ ] Person performs action → action logged, alert countdown resets
  - [ ] Action timeout → 30s siren + alert logged
- [ ] Test "Action Alerts Only" mode
  - [ ] Sleep detection disabled
  - [ ] Action and stillness alerts active
- [ ] Test "Sleeping Alerts Only" mode
  - [ ] Sleep detection active
  - [ ] Action and stillness alerts disabled
- [ ] Verify alerts stop when:
  - [ ] Required action is performed
  - [ ] Action is changed by user
  - [ ] Alert mode is disabled
- [ ] Check CSV logging for all three alert types
- [ ] Verify sleep timer adjustment works
- [ ] Monitor mode switching is smooth

## File Paths
- Modified: `/d/CUDA_Experiments/Git_HUB/Nirikhsan_Web_Cam/Upgrads/Basic+Mediapose.py`
- Original: `/d/CUDA_Experiments/Git_HUB/Nirikhsan_Web_Cam/Upgrads/Basic_v5.py`

## Notes
- All changes are backward compatible with existing Pro_Detection and Fugitive modes
- ReID and tracking logic remain unchanged
- UI uses CustomTkinter for modern appearance
- Sleep detection adaptive calibration prevents false positives
