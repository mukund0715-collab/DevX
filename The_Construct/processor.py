import cv2
import json
import os
import sys
import mediapipe as mp
import subprocess
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- CONFIGURATION ---
VIDEO_PATH = "Raw_video/punches_c.mp4"
MODEL_PATH = 'pose_landmarker_heavy.task'

# Output naming
base_name = os.path.splitext(os.path.basename(VIDEO_PATH))[0]
COORD_FILE = f"{base_name}_coords.json"

# --- SETUP MEDIAPIPE ---
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO
)

print(f"--- Step 1: Extracting Coordinates from {VIDEO_PATH} ---")

raw_coordinates = []

with vision.PoseLandmarker.create_from_options(options) as landmarker:
    cap = cv2.VideoCapture(VIDEO_PATH)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_idx = 0
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success: break

        # Optional: Auto-rotate if video is stored sideways
        h, w = frame.shape[:2]
        if w > h:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

        # Convert to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
        
        # Detect
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        frame_data = {'frame': frame_idx, 'timestamp_ms': timestamp_ms, 'landmarks': []}
        
        if result.pose_landmarks:
            # Save raw data (we will smooth it in the next script)
            for i, lm in enumerate(result.pose_landmarks[0]):
                frame_data['landmarks'].append({
                    'id': i, 'x': lm.x, 'y': lm.y, 'z': lm.z, 'v': lm.visibility
                })
        
        raw_coordinates.append(frame_data)
        
        # Progress bar
        if frame_idx % 50 == 0:
            print(f"Processing frame {frame_idx}/{total_frames}...", end='\r')
            
        frame_idx += 1

    cap.release()

# --- SAVE COORDINATES ---
output_data = {
    "video_path": VIDEO_PATH,
    "total_frames": frame_idx,
    "coordinates": raw_coordinates
}

with open(COORD_FILE, 'w') as f:
    json.dump(output_data, f)

print(f"\n[Success] Coordinates saved to {COORD_FILE}")

# --- TRIGGER NEXT SCRIPT ---
# This automatically runs the analysis file
print(f"--- Step 2: Triggering Action Analysis ---")
subprocess.run(["python", "visualizer.py", COORD_FILE])