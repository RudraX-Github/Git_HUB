# Quick Start Guide - Updated Features

## 🎯 Multiple Guard Detection (Now Works Simultaneously!)

### What Changed
- **Before**: Only 1 guard detected per frame even if multiple guards were visible
- **Now**: ALL visible guards detected at the same time in the same frame

### How It Works
1. Start camera (`▶ Start` button)
2. Select multiple guards from "📋 Select Targets" button
3. Click "🎬 Track" to start tracking
4. When both guards are visible in camera feed → **BOTH detected simultaneously**
5. Both guards tracked with bounding boxes and action detection at same time

### Technical Details
- Uses parallel face matching algorithm
- Cost matrix approach: compares all detected faces to all targets in one pass
- Greedy 1-to-1 assignment ensures no duplicate tracking
- Each frame processes ALL detected people at once

---

## 📱 Collapsible Sidebar (Maximize Camera Feed)

### How to Use Sidebar Toggle
1. **Expand (Default)**: Sidebar shows on right side (~280px wide)
   - Click button: `◄ Hide`
   - Shows: All controls, previews, status
   
2. **Collapse**: Sidebar minimizes to narrow strip
   - Click button: `► Show`
   - Camera feed expands to full screen width
   - Only toggle button visible on right edge

### Sidebar Sections (Scrollable)

**SYSTEM CONTROLS**
- ▶ Start - Open camera
- ⏹ Stop - Close camera
- 📸 Snap - Capture photo
- 🚪 Exit - Close application

**GUARD MANAGEMENT**
- ➕ Add - Add new guard with onboarding
- ❌ Remove - Delete guard profile
- 🔄 Refresh - Reload all guards

**DETECTION MODES**
- 🔔 Alert - Enable alert timeout mode
- 🚨 Fugitive - Search for specific person
- 🎯 Pro - Advanced person re-identification

**SETTINGS & ACTIONS**
- ⏱ Interval - Set alert timeout (HH:MM:SS)
- Action Dropdown - Select required pose
- 📋 Select - Choose which guards to track
- 🎬 Track - Start tracking selected guards

**TRACKED PERSONS** (Preview)
- Shows selected target thumbnails
- Guard preview panel
- Fugitive detection panel

**STATUS** (Bottom)
- FPS: Current frame rate
- MEM: Memory usage in MB

---

## 🎬 Typical Workflow

### Setup
1. Click `▶ Start` → Select camera
2. Click `➕ Add` → Onboard guards one by one
   - Face capture
   - 4 pose captures (Left Hand, Right Hand, Sit, Stand)
3. Click `📋 Select` → Check guards to monitor
4. Click `🎬 Track` → Start tracking selected guards

### Monitoring (Multiple Guards)
1. **Expanded Sidebar**: 
   - Full visibility of controls
   - Can quickly change settings
   - Preview thumbnails visible
   
2. **Collapsed Sidebar** (for live monitoring):
   - Click `◄ Hide` to collapse
   - Camera feed takes full screen
   - Click `► Show` to expand sidebar again

### Alert Mode (Multiple Guards)
1. Click `🔔 Alert` to enable
2. Set interval (e.g., 30 seconds)
3. Select action (e.g., "Hands Up")
4. Select guards to monitor
5. **Each guard is checked independently**
   - Guard A timeout: alert sound
   - Guard B performs action: alert resets for B only
   - Parallel monitoring = simultaneous detection

---

## ⚙️ Pro Tips

### Maximize Camera Feed
- Collapse sidebar (`◄ Hide`) for unobstructed live view
- Still access controls with `► Show` button
- Perfect for monitoring mode

### Quick Guard Selection
- Use `Select All` button in selection dialog
- Use `Clear All` to deselect everything
- Changes take effect after clicking `🎬 Track`

### Alert Mode with Multiple Guards
- Each guard has independent timer
- Performing required action resets ONLY that guard's timer
- Other guards continue their own timers
- Simultaneous action detection across all guards

### Memory Management
- Status shows `MEM: XXX MB` at sidebar bottom
- Auto-cleanup every ~10 seconds
- Long sessions (8+ hours) prompt for restart

---

## 🐛 Troubleshooting

### Multiple Guards Not Detecting Simultaneously
- Check guard face sizes are similar (closer to camera helps)
- Ensure lighting is good
- Try `🔄 Refresh` to reload guard profiles
- Check detection confidence in overlay (should be > 0.65)

### Sidebar Not Toggling
- Make sure camera is running (`▶ Start` first)
- Click `◄ Hide` button clearly
- If stuck, restart application

### Guard Preview Blank
- Add guards first with `➕ Add`
- Select guards with `📋 Select`
- Press `🎬 Track` to activate tracking
- Previews show only selected guards

---

## 📊 Display Information

### On-Screen Overlays (When Tracking)
- **Guard Name + Confidence**: "John (0.87)" - Face match confidence
- **Action + Pose Quality**: "Hands Up (P: 80%)" - Current pose and visibility
- **Alert Status**: "John (OK): 15.2s" - Remaining time in alert mode
- **Box Colors**:
  - 🟢 Green: High confidence (>0.85)
  - 🟠 Orange: Medium confidence (0.65-0.85)
  - 🔴 Red: Low confidence (<0.65)

---

## 📝 Keyboard Shortcuts
(None currently - all via GUI buttons)
Future: Consider Tab key for sidebar toggle

---

For detailed technical changes, see: `IMPROVEMENTS_CHANGELOG.md`
