import cv2
import tkinter as tk
from tkinter import ttk
from threading import Thread

# Global variables
cap = None
running = False

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
        cv2.imshow("Live Camera Feed", frame)

        # Exit if 'q' pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    stop_camera()

# Tkinter GUI
root = tk.Tk()
root.title("Camera Control")

start_btn = ttk.Button(root, text="Start Camera", command=start_camera)
start_btn.pack(pady=10)

stop_btn = ttk.Button(root, text="Stop Camera", command=stop_camera)
stop_btn.pack(pady=10)

root.mainloop()
