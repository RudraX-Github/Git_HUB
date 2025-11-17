import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import ttk
from threading import Thread

# Global variables
cap = None
running = False

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
    global cap, running
    running = False
    if cap is not None:
        cap.release()
        cv2.destroyAllWindows()

def show_camera():
    global cap, running
    while running and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Convert BGR → RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb_frame)

        # Draw landmarks if detected
        if results.pose_landmarks:
            mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            # Example action rule: Right hand above head = "Wave"
            landmarks = results.pose_landmarks.landmark
            right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
            nose = landmarks[mp_pose.PoseLandmark.NOSE]

            if right_wrist.y < nose.y:  # wrist higher than nose
                cv2.putText(frame, "Action: Wave", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Live Camera Pose Detection", frame)

        # Exit if 'q' pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stop_camera()

# Tkinter GUI
root = tk.Tk()
root.title("Camera Control with Pose Detection")

start_btn = ttk.Button(root, text="Start Camera", command=start_camera)
start_btn.pack(pady=10)

stop_btn = ttk.Button(root, text="Stop Camera", command=stop_camera)
stop_btn.pack(pady=10)

root.mainloop()
