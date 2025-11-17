import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import ttk
from threading import Thread
import joblib   # for scikit-learn models
import time

# Global variables
cap = None
running = False

# Load pre-trained HAR model (scikit-learn joblib example)
# Replace with your trained HAR model path
HAR_MODEL_PATH = "har_model.joblib"
try:
    har_model = joblib.load(HAR_MODEL_PATH)
    print("HAR model loaded successfully.")
except:
    har_model = None
    print("No HAR model found. Using rule-based fallback.")

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

def extract_features(landmarks):
    """Convert pose landmarks into a flat feature vector."""
    features = []
    for lm in landmarks:
        features.extend([lm.x, lm.y, lm.z, lm.visibility])
    return np.array(features)

def predict_action(features):
    """Predict action using HAR model or fallback rule."""
    if har_model is not None:
        try:
            label = har_model.predict([features])[0]
            return str(label)
        except Exception as e:
            print("Prediction error:", e)
    # Fallback rule: right wrist above nose = Wave
    rw_y = features[16*4+1]  # RIGHT_WRIST y
    nose_y = features[0*4+1] # NOSE y
    if rw_y < nose_y:
        return "Wave"
    return "Unknown"

def show_camera():
    global cap, running
    while running and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        action_label = "No Pose"
        if results.pose_landmarks:
            mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            features = extract_features(results.pose_landmarks.landmark)
            action_label = predict_action(features)

        cv2.putText(frame, f"Action: {action_label}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("HAR Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stop_camera()

# Tkinter GUI
root = tk.Tk()
root.title("Camera Control with HAR")
root.geometry("300x120")

ttk.Button(root, text="Start Camera", command=start_camera).pack(pady=10)
ttk.Button(root, text="Stop Camera", command=stop_camera).pack(pady=10)

root.mainloop()
