import cv2
import mediapipe as mp
import csv
import time
import tkinter as tk
from tkinter import font
from tkinter import simpledialog
from tkinter import messagebox 
from PIL import Image, ImageTk
import os 
import glob
import face_recognition
import numpy as np 
# MTCNN has been removed

# --- MP Tasks API Imports ---
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2 

# --- MP Drawing Imports ---
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# CSV setup
csv_file = "activity_log.csv"
with open(csv_file, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp", "Name", "Action", "Nose_X", "Nose_Y"])

# --- classify_action (Unchanged) ---
def classify_action(landmarks, h, w):
    try:
        nose = landmarks[0] 
        left_wrist = landmarks[15]
        right_wrist = landmarks[16]
        left_hip = landmarks[23]
        right_hip = landmarks[24]
        left_knee = landmarks[25]
        right_knee = landmarks[26]
        left_ankle = landmarks[27]
        right_ankle = landmarks[28]

        nose_y = nose.y * h
        lw_y = left_wrist.y * h
        rw_y = right_wrist.y * h
        lh_y = left_hip.y * h
        rh_y = right_hip.y * h
        lk_y = left_knee.y * h
        rk_y = right_knee.y * h
        la_y = left_ankle.y * h
        ra_y = right_ankle.y * h

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
    except Exception as e:
        print(f"Error in classification: {e}")
        return "Error"

# --- Tkinter Application Class ---
class PoseApp:
    def __init__(self, window_title="Pose Detection App"):
        self.root = tk.Tk()
        self.root.title(window_title)
        self.root.geometry("1200x950")
        
        self.cap = None
        self.unprocessed_frame = None 
        self.is_running = False
        self.is_logging = False
        self.last_logged_action = None
        
        self.is_in_capture_mode = False
        self.guide_center_x = 320
        self.guide_center_y = 240
        self.guide_axis_x = 100
        self.guide_axis_y = 130
        self.frame_w = 640 
        self.frame_h = 480 

        # Target Management
        self.target_map = {}
        self.selected_target_var = tk.StringVar(self.root)
        self.target_image_label = None

        # Face Recognition
        self.target_face_encoding = None
        self.target_name = "No Target"

        # --- High-Speed Tracking State ---
        self.tracker = None           
        self.is_tracking = False      
        self.tracked_box = None # (x1, y1, x2, y2)
        self.re_detect_counter = 0    
        self.RE_DETECT_INTERVAL = 30  
        self.last_known_confidence = 0.0
        self.RESIZE_SCALE = 0.5 # 320x240 for detection

        # --- Optimized Logging ---
        self.csv_writer = None
        self.csv_file_handle = None
        
        # --- MediaPipe Setup ---
        model_path = 'pose_landmarker_full.task'
        if not os.path.exists(model_path):
            messagebox.showerror("Error", f"Model file not found: {model_path}\nPlease download 'pose_landmarker_full.task'.")
            self.root.destroy()
            return
            
        try:
            base_options = mp_tasks.BaseOptions(model_asset_path=model_path)
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                # --- CRITICAL FIX: Must be 5 to find all poses to link from ---
                num_poses=5, 
                min_pose_detection_confidence=0.5,
                min_tracking_confidence=0.5)
            self.pose_landmarker = vision.PoseLandmarker.create_from_options(options)
            print("Pose Landmarker loaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load Pose Landmarker: {e}")
            self.root.destroy()
            return
            
        self.frame_timestamp_ms = 0 

        # --- GUI Setup (Unchanged) ---
        self.video_frame = tk.Frame(self.root, bg="black")
        self.video_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.video_label = tk.Label(self.video_frame)
        self.video_label.pack(expand=True)
        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(fill="x", padx=10, pady=5)
        btn_font = font.Font(family='Helvetica', size=12, weight='bold')
        self.btn_start = tk.Button(self.control_frame, text="Start Camera", command=self.start_camera, font=btn_font, bg="#4CAF50", fg="white", height=2)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_stop = tk.Button(self.control_frame, text="Stop Camera", command=self.stop_camera, font=btn_font, bg="#f44336", fg="white", height=2, state="disabled")
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_toggle_log = tk.Button(self.control_frame, text="Start Logging", command=self.toggle_logging, font=btn_font, bg="#2196F3", fg="white", height=2, state="disabled")
        self.btn_toggle_log.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_capture_target = tk.Button(self.control_frame, text="Capture Target", command=self.enter_capture_mode, font=btn_font, bg="#9C27B0", fg="white", height=2, state="disabled")
        self.btn_capture_target.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_snap = tk.Button(self.control_frame, text="Snap Photo", command=self.snap_photo, font=btn_font, bg="#FF9800", fg="white", height=2)
        self.btn_cancel_capture = tk.Button(self.control_frame, text="Cancel", command=self.exit_capture_mode, font=btn_font, bg="#757575", fg="white", height=2)
        self.target_frame = tk.Frame(self.root, height=200, relief="groove", bd=2)
        self.target_frame.pack(fill="x", padx=10, pady=10)
        self.target_select_frame = tk.Frame(self.target_frame)
        self.target_select_frame.pack(side="left", fill="y", padx=10, pady=10)
        tk.Label(self.target_select_frame, text="Select Target:", font=btn_font).pack(anchor="w")
        self.selected_target_var.set("No targets found")
        self.target_dropdown = tk.OptionMenu(self.target_frame, self.selected_target_var, "No targets found", command=self.on_target_select)
        self.target_dropdown.config(width=30, font=('Helvetica', 10))
        self.target_dropdown.pack(anchor="w", in_=self.target_select_frame, pady=5)
        self.btn_refresh = tk.Button(self.target_select_frame, text="Refresh List", command=self.load_targets, font=('Helvetica', 10, 'bold'), bg="#FF9800", fg="white")
        self.btn_refresh.pack(anchor="w", pady=10)
        self.target_display_frame = tk.Frame(self.target_frame, bg="black", width=250, height=200)
        self.target_display_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.target_display_frame.pack_propagate(False)
        self.target_image_label = tk.Label(self.target_display_frame, bg="black", text="Selected target appears here", fg="white")
        self.target_image_label.pack(expand=True)
        
        self.load_targets()
        self.root.mainloop()

    # --- Target Loading (Unchanged) ---
    def load_targets(self):
        print("[INFO] Loading targets...")
        self.target_map = {}
        target_files = glob.glob("target_*.jpg")
        display_names = []
        for f in target_files:
            try:
                base_name = f.replace(".jpg", "")
                parts = base_name.split('_')
                if len(parts) >= 4:
                    display_name = " ".join(parts[1:-2])
                    self.target_map[display_name] = f
                    display_names.append(display_name)
            except Exception as e:
                print(f"Error parsing filename {f}: {e}")

        menu = self.target_dropdown["menu"]
        menu.delete(0, "end")
        if not display_names:
            menu.add_command(label="No targets found", state="disabled")
            self.selected_target_var.set("No targets found")
            if self.target_image_label:
                self.target_image_label.config(image='', text="No targets found")
            self.target_face_encoding = None
            self.target_name = "No Target"
        else:
            display_names = sorted(list(set(display_names)))
            self.selected_target_var.set(display_names[0]) 
            for name in display_names:
                menu.add_command(label=name, command=lambda value=name: self.on_target_select(value))
            self.on_target_select(display_names[0])

    # --- on_target_select (Unchanged) ---
    def on_target_select(self, selected_name):
        self.is_tracking = False
        self.tracker = None
        self.last_known_confidence = 0.0 
        
        self.selected_target_var.set(selected_name)
        filename = self.target_map.get(selected_name)
        if not filename:
            print(f"[ERROR] No filename found for key: {selected_name}")
            return
        try:
            target_image_file = face_recognition.load_image_file(filename)
            encodings = face_recognition.face_encodings(target_image_file)
            
            if encodings:
                self.target_face_encoding = encodings[0]
                self.target_name = selected_name
                print(f"[INFO] Target face encoding loaded for: {self.target_name}")
            else:
                self.target_face_encoding = None
                self.target_name = "No Target"
                print(f"[ERROR] No face found in target image: {filename}")
                
            img = cv2.imread(filename) 
            target_w, target_h = 240, 190
            img_h, img_w = img.shape[:2]
            aspect_ratio = img_w / img_h
            if aspect_ratio > (target_w / target_h):
                new_w = target_w
                new_h = int(new_w / aspect_ratio)
            else:
                new_h = target_h
                new_w = int(new_h * aspect_ratio)
            resized_img = cv2.resize(img, (new_w, new_h))
            cv2image = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=pil_img)
            self.target_image_label.config(image=imgtk, text="")
            self.target_image_label.imgtk = imgtk
        except Exception as e:
            print(f"[ERROR] Failed to load target image {filename}: {e}")
            self.target_image_label.config(image='', text=f"Error loading {filename}")
            self.target_face_encoding = None
            self.target_name = "No Target"

    # --- Camera Controls (Unchanged) ---
    def start_camera(self):
        if not self.is_running:
            try:
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    messagebox.showerror("Error", "Cannot open camera")
                    return
                self.frame_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.frame_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"Camera started with resolution: {self.frame_w}x{self.frame_h}")

                self.is_running = True
                self.frame_timestamp_ms = 0
                self.btn_start.config(state="disabled")
                self.btn_stop.config(state="normal")
                self.btn_toggle_log.config(state="normal")
                self.btn_capture_target.config(state="normal")
            except Exception as e:
                print(f"Error starting camera: {e}")
        if self.is_running:
            self.update_video_feed()

    # --- stop_camera (Unchanged, includes CSV fix) ---
    def stop_camera(self):
        if self.is_running:
            self.is_running = False
            if self.cap:
                self.cap.release()
            
            self.is_tracking = False
            self.tracker = None

            if self.csv_file_handle:
                self.csv_file_handle.close()
                self.csv_file_handle = None
                self.csv_writer = None
                print("[INFO] Logging file closed.")

            if self.is_in_capture_mode:
                self.exit_capture_mode()
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.is_logging = False
            self.last_logged_action = None
            self.btn_toggle_log.config(text="Start Logging", bg="#2196F3", state="disabled")
            self.btn_capture_target.config(state="disabled")
            self.video_label.config(image='')
            self.unprocessed_frame = None

    # --- toggle_logging (Unchanged, includes CSV fix) ---
    def toggle_logging(self):
        self.is_logging = not self.is_logging
        self.last_logged_action = None
        
        if self.is_logging:
            try:
                self.csv_file_handle = open(csv_file, mode="a", newline="")
                self.csv_writer = csv.writer(self.csv_file_handle)
                self.btn_toggle_log.config(text="Stop Logging", bg="#E65100")
                print("[INFO] Logging Started (file open).")
            except Exception as e:
                print(f"[ERROR] Failed to open log file: {e}")
                self.is_logging = False
        else:
            if self.csv_file_handle:
                self.csv_file_handle.close()
                self.csv_file_handle = None
                self.csv_writer = None
            self.btn_toggle_log.config(text="Start Logging", bg="#2196F3")
            print("[INFO] Logging Stopped (file closed).")

    # --- Capture Mode Functions (Unchanged) ---
    def enter_capture_mode(self):
        if not self.is_running:
            return
        self.is_in_capture_mode = True
        self.btn_start.pack_forget()
        self.btn_stop.pack_forget()
        self.btn_toggle_log.pack_forget()
        self.btn_capture_target.pack_forget()
        self.btn_snap.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_cancel_capture.pack(side="left", fill="x", expand=True, padx=5)

    def exit_capture_mode(self):
        self.is_in_capture_mode = False
        self.btn_snap.pack_forget()
        self.btn_cancel_capture.pack_forget()
        self.btn_start.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_toggle_log.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_capture_target.pack(side="left", fill="x", expand=True, padx=5)
        if self.is_running:
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.btn_toggle_log.config(state="normal")
            self.btn_capture_target.config(state="normal")
        else:
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.btn_toggle_log.config(state="disabled")
            self.btn_capture_target.config(state="disabled")

    def snap_photo(self):
        if self.unprocessed_frame is None:
            messagebox.showwarning("Snap Error", "No frame available.")
            return

        rgb_frame = cv2.cvtColor(self.unprocessed_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        scale_x = self.frame_w / 640.0
        scale_y = self.frame_h / 480.0
        center_x = int(self.guide_center_x * scale_x)
        center_y = int(self.guide_center_y * scale_y)
        axis_x = int(self.guide_axis_x * scale_x)
        axis_y = int(self.guide_axis_y * scale_y)

        faces_in_guide = []
        for (top, right, bottom, left) in face_locations:
            face_center_x = (left + right) // 2
            face_center_y = (top + bottom) // 2
            if ((face_center_x - center_x)**2 / axis_x**2 + (face_center_y - center_y)**2 / axis_y**2) <= 1:
                faces_in_guide.append((top, right, bottom, left))

        if len(faces_in_guide) == 1:
            name = simpledialog.askstring("Input Name", "Enter a name for this target:", parent=self.root)
            if name and name.strip():
                safe_name = name.strip().replace(" ", "_")
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"target_{safe_name}_{timestamp}.jpg"
                try:
                    cv2.imwrite(filename, self.unprocessed_frame)
                    print(f"[INFO] Target image saved: {filename}")
                    self.load_targets() 
                    self.exit_capture_mode() 
                except Exception as e:
                    messagebox.showerror("Save Error", f"Could not save image: {e}")
            else:
                print("[INFO] Capture cancelled or no name provided.")
        elif len(faces_in_guide) > 1:
            messagebox.showwarning("Snap Error", "Multiple faces detected in the guide. Please ensure only one person is in the oval.")
        else:
            messagebox.showwarning("Snap Error", "No face detected in the guide. Please center your face and try again.")


    # --- Main Video Loop (Unchanged) ---
    def update_video_feed(self):
        if not self.is_running:
            return

        ret, frame = self.cap.read()
        if not ret:
            print("Error: Can't receive frame (stream end?).")
            self.stop_camera()
            return
            
        self.unprocessed_frame = frame.copy()
        
        if self.is_in_capture_mode:
            self.process_capture_frame(frame)
        else:
            self.process_tracking_frame_optimized(frame)
        
        if self.video_label.winfo_exists():
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.config(image=imgtk)

        self.root.after(10, self.update_video_feed) 

    # --- process_capture_frame (Unchanged) ---
    def process_capture_frame(self, frame):
        scale_x = self.frame_w / 640.0
        scale_y = self.frame_h / 480.0
        center = (int(self.guide_center_x * scale_x), int(self.guide_center_y * scale_y))
        axes = (int(self.guide_axis_x * scale_x), int(self.guide_axis_y * scale_y))
        cv2.ellipse(frame, center, axes, 0, 0, 360, (0, 255, 255), 2)
        cv2.putText(frame, "Center your face in the guide and press 'Snap Photo'", (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        return frame

    # --- ### THIS IS THE COMPLETELY REWRITTEN FUNCTION ### ---
    def process_tracking_frame_optimized(self, frame):
        """
        New logic:
        1. Find face box (using tracker or detection).
        2. Run pose detection on the FULL frame.
        3. Link pose to face box.
        """
        
        target_visible = False
        target_box_coords = None # (x1, y1, x2, y2)
        
        if self.is_tracking:
            self.re_detect_counter += 1
            if self.re_detect_counter > self.RE_DETECT_INTERVAL:
                self.is_tracking = False 
                self.tracker = None
                self.re_detect_counter = 0

        # -----------------------------------------------
        # --- PART 1: FIND THE TARGET'S FACE BOX ---
        # -----------------------------------------------
        
        # --- PATH 1.A: WE ARE ACTIVELY TRACKING (FAST) ---
        if self.is_tracking:
            success, box = self.tracker.update(frame)
            if success:
                target_visible = True 
                x, y, w, h = [int(v) for v in box]
                target_box_coords = (x, y, x + w, y + h) # (x1, y1, x2, y2)
            else:
                # Tracker failed, force re-detection
                self.is_tracking = False
                self.tracker = None
        
        # --- PATH 1.B: WE ARE DETECTING (SLOWER) ---
        else:
            if self.target_face_encoding is not None:
                # Use larger resize scale for better distance
                rgb_small_frame = cv2.resize(frame, (0, 0), fx=self.RESIZE_SCALE, fy=self.RESIZE_SCALE)
                rgb_small_frame = cv2.cvtColor(rgb_small_frame, cv2.COLOR_BGR2RGB)
                
                face_locations = face_recognition.face_locations(rgb_small_frame)
                
                if face_locations:
                    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                    face_distances = face_recognition.face_distance(face_encodings, self.target_face_encoding)
                    best_match_index = np.argmin(face_distances)
                    best_match_distance = face_distances[best_match_index]
                    
                    if best_match_distance < 0.55: 
                        target_visible = True
                        print("[INFO] Target found. Initializing tracker.")
                        (top, right, bottom, left) = face_locations[best_match_index]
                        
                        scale_up = 1 / self.RESIZE_SCALE
                        x1 = int(left * scale_up)
                        y1 = int(top * scale_up)
                        x2 = int(right * scale_up)
                        y2 = int(bottom * scale_up)
                        
                        target_box_coords = (x1, y1, x2, y2)
                        tracker_box = (x1, y1, x2 - x1, y2 - y1) # (x, y, w, h)
                        
                        try:
                            self.tracker = cv2.legacy.TrackerCSRT_create() 
                            self.tracker.init(frame, tracker_box)
                            self.is_tracking = True
                        except Exception as e:
                            print(f"--- ERROR: {e} ---")
                            print("Please ensure you have 'opencv-contrib-python' installed.")
                            self.stop_camera()
                            return frame

                        self.re_detect_counter = 0
                        self.last_known_confidence = (1.0 - best_match_distance) * 100

        # -----------------------------------------------
        # --- PART 2: RUN POSE DETECTION (FULL FRAME) ---
        # -----------------------------------------------
        
        rgb_full_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_full_frame)
        self.frame_timestamp_ms = int(time.time() * 1000)
        
        try:
            results = self.pose_landmarker.detect_for_video(mp_image, self.frame_timestamp_ms)
        except Exception as e:
            print(f"Error during pose detection: {e}")
            results = None 
        
        # -----------------------------------------------
        # --- PART 3: LINK POSE TO FACE & DISPLAY ---
        # -----------------------------------------------
        
        if not target_visible:
            if self.target_face_encoding is not None:
                cv2.putText(frame, "NO TARGET FOUND", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return frame # Nothing more to do
        
        # --- Target IS visible ---
        (x1, y1, x2, y2) = target_box_coords
        confidence_text = f"({self.last_known_confidence:.0f}%)"
        
        # Draw the face box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        target_pose_found = False
        if results and results.pose_landmarks:
            for pose_landmarks_list in results.pose_landmarks:
                nose = pose_landmarks_list[0]
                nose_x = int(nose.x * self.frame_w)
                nose_y = int(nose.y * self.frame_h)

                # Check if this pose's nose is inside the target's face box
                if (nose_x > x1 and nose_x < x2 and nose_y > y1 and nose_y < y2):
                    # --- LINK FOUND! ---
                    target_pose_found = True
                    
                    # Classify action using FULL FRAME dimensions
                    current_action = classify_action(pose_landmarks_list, self.frame_h, self.frame_w)
                    
                    # Draw text
                    cv2.putText(frame, f"{self.target_name} {confidence_text}: {current_action}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Draw pose
                    pose_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
                    for landmark_data in pose_landmarks_list:
                        landmark_proto = pose_landmarks_proto.landmark.add()
                        landmark_proto.x = landmark_data.x
                        landmark_proto.y = landmark_data.y
                        landmark_proto.z = landmark_data.z
                        if landmark_data.visibility is not None:
                            landmark_proto.visibility = landmark_data.visibility
                        if landmark_data.presence is not None:
                            landmark_proto.presence = landmark_data.presence
                    
                    target_landmark_spec = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2)
                    target_connection_spec = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2)
                    mp_drawing.draw_landmarks(
                        frame, pose_landmarks_proto, mp_pose.POSE_CONNECTIONS,
                        landmark_drawing_spec=target_landmark_spec,
                        connection_drawing_spec=target_connection_spec)
                    
                    # Log
                    if self.is_logging and current_action == "Wave Right":
                        if self.last_logged_action != (self.target_name, current_action):
                            if self.csv_writer:
                                # Log the FULL FRAME nose coordinates
                                self.csv_writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), self.target_name, current_action, nose_x, nose_y])
                                self.csv_file_handle.flush()
                            self.last_logged_action = (self.target_name, current_action)
                    if current_action != "Wave Right":
                        self.last_logged_action = None
                    
                    # We found the target's pose, stop looping
                    break
        
        if not target_pose_found:
            # Face is tracked, but pose not found (maybe occluded or out of frame)
            cv2.putText(frame, f"{self.target_name} {confidence_text}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return frame 

# --- Run the App ---
if __name__ == "__main__":
    app = PoseApp()