import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import ttk
from threading import Thread
from PIL import Image, ImageTk

# Globals
cap = None
running = False
video_label = None

# MediaPipe Pose setup
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_draw = mp.solutions.drawing_utils

def start_camera():
    global cap, running
    if not running:
        cap = cv2.VideoCapture(0)
        running = True
        Thread(target=show_camera).start()

def stop_camera():
    global cap, running, video_label
    running = False
    if cap is not None:
        cap.release()
        cap = None
    if video_label is not None:
        video_label.config(image='')
        video_label.image = None

def classify_action(landmarks, h, w):
    """
    Rule-based gesture recognition using MediaPipe Pose landmarks:
    - Wave Left: left wrist above nose
    - Wave Right: right wrist above nose
    - Jump: both ankles much lower than hips
    - Sit: hips lower than knees
    """
    nose = landmarks[mp_pose.PoseLandmark.NOSE.value]
    left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value]
    right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
    left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
    right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value]
    left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value]
    right_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value]

    # Convert normalized coords to pixel
    nose_y = nose.y * h
    lw_y = left_wrist.y * h
    rw_y = right_wrist.y * h
    lh_y = left_hip.y * h
    rh_y = right_hip.y * h
    lk_y = left_knee.y * h
    rk_y = right_knee.y * h
    la_y = left_ankle.y * h
    ra_y = right_ankle.y * h

    # Rules
    if lw_y < nose_y:
        return "Wave Left"
    elif rw_y < nose_y:
        return "Wave Right"
    elif (la_y - lh_y > 80) and (ra_y - rh_y > 80):
        return "Jump"
    elif (lh_y > lk_y) and (rh_y > rk_y):
        return "Sit"
    else:
        return "Unknown"

def show_camera():
    global cap, running, video_label
    
    if cap is None or not cap.isOpened():
        return
    
    while running and cap is not None and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        action_label = "No Pose"
        if results.pose_landmarks:
            mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            action_label = classify_action(results.pose_landmarks.landmark, h, w)

        cv2.putText(frame, f"Action: {action_label}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Convert frame to ImageTk format for Tkinter display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img_tk = ImageTk.PhotoImage(image=img)
        
        if video_label is not None:
            video_label.config(image=img_tk)
            video_label.image = img_tk  # Keep a reference

    stop_camera()

# Tkinter GUI
root = tk.Tk()
root.title("Camera Control with Pose-based Gestures")
root.geometry("800x700")

# Control frame at top
control_frame = ttk.Frame(root)
control_frame.pack(pady=10)

ttk.Button(control_frame, text="Start Camera", command=start_camera).pack(side=tk.LEFT, padx=5)
ttk.Button(control_frame, text="Stop Camera", command=stop_camera).pack(side=tk.LEFT, padx=5)

# Video display label
video_label = tk.Label(root, bg='black')
video_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

root.mainloop()
