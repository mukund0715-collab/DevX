import cv2
import json
import mediapipe as mp
import numpy as np
import time
import sys
import os
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- CONFIGURATION ---
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720

# --- ARGUMENT HANDLING ---
if len(sys.argv) > 1:
    JSON_PATH = sys.argv[1]
else:
    JSON_PATH = 'sck/punches_c_coords.json' 

if len(sys.argv) > 2:
    ERROR_LOG_PATH = sys.argv[2]
else:
    if not os.path.exists("mistakes"): os.makedirs("mistakes")
    ERROR_LOG_PATH = 'mistakes/debug_session.json'

os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)

MODEL_PATH = 'pose_landmarker_heavy.task'
STUCK_TIMEOUT = 2.5 
VIS_THRESHOLD = 0.5 

# Weights & Groups
WEIGHTS = {
    'head_neck': 0.05, 'shoulders': 0.10, 'elbows': 0.10,
    'wrists_hands': 0.15, 'torso_hips': 0.20, 'knees': 0.20, 'ankles_feet': 0.20
}

GROUPS = {
    'head_neck': [0, 7, 8], 'shoulders': [11, 12], 'elbows': [13, 14],
    'wrists_hands': [15, 16, 17, 18, 19, 20, 21, 22], 'torso_hips': [23, 24],
    'knees': [25, 26], 'ankles_feet': [27, 28, 29, 30, 31, 32]
}

CONNECTIONS = [
    (11, 12), (12, 24), (24, 23), (23, 11), 
    (11, 13), (13, 15), (12, 14), (14, 16), 
    (23, 25), (25, 27), (24, 26), (26, 28)  
]

def get_full_body_features(landmarks, is_json=False):
    points = np.array([[l['x'], l['y']] if is_json else [l.x, l.y] for l in landmarks])
    hip_center = (points[23] + points[24]) / 2.0
    return points - hip_center

def evaluate_groups(curr_full, curr_rel, targ_rel):
    total_weighted_score = 0
    total_weight_used = 0
    for group, indices in GROUPS.items():
        visible_indices = [i for i in indices if curr_full[i].visibility > VIS_THRESHOLD]
        if len(visible_indices) < 2: continue 
        v1, v2 = curr_rel[visible_indices].flatten(), targ_rel[visible_indices].flatten()
        norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
        sim = (np.dot(v1, v2) / (norm1 * norm2)) * 100 if (norm1 * norm2) != 0 else 0
        total_weighted_score += sim * WEIGHTS[group]
        total_weight_used += WEIGHTS[group]
    return (total_weighted_score / total_weight_used) if total_weight_used > 0 else 0

def resize_and_pad(image, target_w, target_h):
    h, w = image.shape[:2]
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    
    resized = cv2.resize(image, (new_w, new_h))
    canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
    
    return canvas, x_offset, y_offset, scale

# --- MAIN ---
try:
    with open(JSON_PATH, 'r') as f:
        data = json.load(f)
        target_data = data['coordinates'] if 'coordinates' in data else data
except FileNotFoundError:
    sys.exit()

target_features = [get_full_body_features(f['landmarks'], True) for f in target_data]

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.PoseLandmarkerOptions(base_options=base_options, running_mode=vision.RunningMode.VIDEO)

error_log = [] 
total_score_accumulated = 0
frames_tracked = 0

# --- ROBUST CAMERA INITIALIZATION ---
print("[LIVE] Initializing Camera...")
cap_live = cv2.VideoCapture(0, cv2.CAP_DSHOW) # Try DirectShow (Index 0)

if not cap_live.isOpened():
    print("[LIVE] Camera 0 failed. Trying Camera 1...")
    cap_live = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if not cap_live.isOpened():
    print("[LIVE] CRITICAL ERROR: No Camera Found.")
    # Create a dummy black frame so it doesn't crash, just shows black
    # This allows you to debug without hardware
    class DummyCap:
        def isOpened(self): return True
        def read(self): return True, np.zeros((720, 1280, 3), dtype=np.uint8)
        def release(self): pass
        def set(self, prop, val): pass
    cap_live = DummyCap()

# Set Resolution
cap_live.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap_live.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

WINDOW_NAME = 'PROJECT MORPHEUS // LIVE LINK'
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, TARGET_WIDTH, TARGET_HEIGHT)

with vision.PoseLandmarker.create_from_options(options) as landmarker:
    current_target_idx = 0
    last_advance_time = time.time()

    while cap_live.isOpened():
        ret_l, raw_frame = cap_live.read()
        if not ret_l: break
        
        raw_frame = cv2.flip(raw_frame, 1)
        frame, offset_x, offset_y, scale = resize_and_pad(raw_frame, TARGET_WIDTH, TARGET_HEIGHT)
        h, w, _ = frame.shape

        # Mini-Map (Portrait)
        if current_target_idx < len(target_data):
            pip_w = w // 8
            pip_h = int(pip_w * (16/9)) 
            pip_x = 30
            pip_y = 30
            
            cv2.rectangle(frame, (pip_x, pip_y), (pip_x + pip_w, pip_y + pip_h), (0, 0, 0), -1)
            cv2.rectangle(frame, (pip_x, pip_y), (pip_x + pip_w, pip_y + pip_h), (0, 255, 65), 1)

            ghost_lms = target_data[current_target_idx]['landmarks']
            for start, end in CONNECTIONS:
                p1_x = int(ghost_lms[start]['x'] * pip_w) + pip_x
                p1_y = int(ghost_lms[start]['y'] * pip_h) + pip_y
                p2_x = int(ghost_lms[end]['x'] * pip_w) + pip_x
                p2_y = int(ghost_lms[end]['y'] * pip_h) + pip_y
                
                if (pip_x <= p1_x <= pip_x + pip_w) and (pip_y <= p1_y <= pip_y + pip_h):
                    cv2.line(frame, (p1_x, p1_y), (p2_x, p2_y), (0, 255, 65), 1) 
            cv2.putText(frame, "GUIDE", (pip_x + 5, pip_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 65), 1)

        # Tracking
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        result = landmarker.detect_for_video(mp_image, int(time.time() * 1000))

        best_score = 0 
        if result.pose_landmarks:
            curr_full = result.pose_landmarks[0]
            curr_rel = get_full_body_features(curr_full)

            best_idx = current_target_idx
            start_s = max(0, current_target_idx - 10)
            end_s = min(len(target_data), current_target_idx + 10)

            for i in range(start_s, end_s):
                score = evaluate_groups(curr_full, curr_rel, target_features[i])
                if score > best_score:
                    best_score, best_idx = score, i

            if best_idx > current_target_idx:
                current_target_idx = best_idx
                last_advance_time = time.time()
                total_score_accumulated += best_score
                frames_tracked += 1
            else:
                time_stuck = time.time() - last_advance_time
                if time_stuck > STUCK_TIMEOUT:
                    targ_rel = target_features[current_target_idx]
                    
                    max_error_distance = -1
                    worst_group = "torso_hips"
                    worst_landmark_idx = 24
                    
                    for group, indices in GROUPS.items():
                        for joint_idx in indices:
                            if curr_full[joint_idx].visibility > VIS_THRESHOLD:
                                dist = np.linalg.norm(curr_rel[joint_idx] - targ_rel[joint_idx])
                                if dist > max_error_distance:
                                    max_error_distance = dist
                                    worst_group = group
                                    worst_landmark_idx = joint_idx
                    
                    error_log.append({
                        "frame_index": current_target_idx,
                        "timestamp": time.strftime("%H:%M:%S"),
                        "failed_joint_id": int(worst_landmark_idx),
                        "failed_group": worst_group,
                        "wrong_x": float(curr_rel[worst_landmark_idx][0]),
                        "right_x": float(targ_rel[worst_landmark_idx][0]),
                        "wrong_y": float(curr_rel[worst_landmark_idx][1]),
                        "right_y": float(targ_rel[worst_landmark_idx][1]),
                        "score_at_fail": int(best_score)
                    })
                    
                    current_target_idx = min(len(target_data)-1, current_target_idx + 20)
                    last_advance_time = time.time()

        color = (0, 255, 0) if best_score > 80 else (0, 0, 255)
        cv2.putText(frame, f"SCORE: {int(best_score)}%", (20, h - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

        cv2.imshow(WINDOW_NAME, frame)
        
        if current_target_idx >= len(target_data) - 5: break
        if cv2.waitKey(1) & 0xFF == ord('q'): break

cap_live.release()
cv2.destroyAllWindows()

# Save Logs
with open(ERROR_LOG_PATH, 'w') as f:
    json.dump(error_log, f, indent=2)

# Save Stats
avg = (total_score_accumulated / frames_tracked) if frames_tracked > 0 else 0
xp = int(avg * 0.5) + (len(target_data) // 10)

with open('session_stats.json', 'w') as f:
    json.dump({"xp_gained": xp, "avg_accuracy": round(avg, 1)}, f)
