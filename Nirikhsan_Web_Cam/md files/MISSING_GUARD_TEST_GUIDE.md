# Missing Guard Detection - Quick Test Guide

## What Was Fixed

**Before**: Missing guard events only logged in alert mode  
**After**: Missing guard events logged automatically when logging is enabled (regardless of alert mode)

---

## Quick Test (5 minutes)

### Step 1: Enable Logging
```
1. Run: python Basic+Mediapose.py
2. Click "Toggle Logging" button (turns ON)
3. Alert mode should be OFF
```

### Step 2: Load Guards
```
1. Click "Load Profiles" button
2. Select 1-2 guards from the list
3. Click OK
4. Click "Select Targets"
5. Check at least one guard
6. Click OK
```

### Step 3: Test Missing Detection
```
1. Start camera feed (guards should be visible)
2. Watch live feed - guard's name should appear with status
3. Have a guard walk OUT of the camera frame
4. Observe: 
   - Guard name disappears from frame
   - Console may show: "🚨 GuardName MISSING from frame"
5. Check logs: Open logs/events.csv
6. Look for entry: "Guard Missing" status with timestamp
```

### Step 4: Test Reappearance
```
1. Have the guard walk BACK into camera frame
2. Guard should be re-detected
3. New CSV entry logged with action (Standing/Walking/etc)
```

---

## Expected CSV Output

### Before (Guard appears)
```csv
2025-01-15 14:32:15,Guard1,Standing,Action Performed,N/A,0.95
```

### During (Guard disappears)
```csv
2025-01-15 14:32:45,Guard1,N/A,Guard Missing,N/A,0.00
```

### After (Guard reappears)
```csv
2025-01-15 14:33:10,Guard1,Standing,Action Performed,N/A,0.93
```

---

## How to Read the Logs

```powershell
# View latest 10 entries
Get-Content "logs\events.csv" -Tail 10

# Or open in Excel/LibreOffice Calc
Start-Process "logs\events.csv"
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Nothing logged | Make sure "Toggle Logging" is ON |
| No "Guard Missing" entries | Guard must leave frame completely (out of camera range) |
| Duplicate entries | Normal - one per disappearance event |
| Guard not detected initially | Ensure guard face is in guard_profiles/ |

---

## Key Points

✅ **Works without alert mode** - No need to enable "Toggle Alert Mode"  
✅ **Requires logging** - "Toggle Logging" must be ON  
✅ **Automatic** - Detects missing as soon as guard leaves frame  
✅ **Prevents duplicates** - Won't log same missing event twice  
✅ **Detects reappearance** - Tracks when guard comes back  

---

## Advanced: Monitor in Real-Time

```powershell
# PowerShell: Watch logs file for changes
Get-Content "logs\events.csv" -Wait -Tail 5
```

Or use a terminal multiplexer:
```powershell
# Start VS Code terminal
# Open logs/events.csv in one pane
# Run Basic+Mediapose.py in another pane
# Observe entries added in real-time
```

---

## Quick Summary

The fix ensures that:
1. **Missing guards are logged** even without alert mode
2. **CSV has complete record** of all guard visibility changes
3. **Works independently** of alert mode setting
4. **No performance impact** - minimal overhead

**Status**: Ready to test! 🚀
