import cv2
import json
import mediapipe as mp
import numpy as np
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- CONFIGURATION ---
JSON_PATH = '3d.json'
MODEL_PATH = 'pose_landmarker_heavy.task'
ERROR_LOG_PATH = 'stuck_coordinates_log.json' 
STUCK_TIMEOUT = 2.5  
VIS_THRESHOLD = 0.5 

WEIGHTS = {
    'head_neck': 0.05, 
    'shoulders': 0.10,
    'elbows': 0.10,
    'wrists_hands': 0.15,
    'torso_hips': 0.15, 
    'knees': 0.20, 
    'ankles_feet': 0.25
}

GROUPS = {
    'head_neck': [0, 7, 8],
    'shoulders': [11, 12],
    'elbows': [13, 14],
    'wrists_hands': [15, 16, 17, 18, 19, 20, 21, 22],
    'torso_hips': [23, 24],
    'knees': [25, 26],
    'ankles_feet': [27, 28, 29, 30, 31, 32]
}

def get_full_body_features(landmarks, is_json=False):
    points = np.array([[l['x'], l['y']] if is_json else [l.x, l.y] for l in landmarks])
    hip_center = (points[23] + points[24]) / 2.0
    return points - hip_center

def evaluate_groups(curr_full, curr_rel, targ_rel):
    group_scores = {}
    total_weighted_score = 0
    total_weight_used = 0
    
    for group, indices in GROUPS.items():
        visible_indices = [i for i in indices if curr_full[i].visibility > VIS_THRESHOLD]
        if len(visible_indices) < 2: 
            group_scores[group] = 100 
            continue 
            
        v1, v2 = curr_rel[visible_indices].flatten(), targ_rel[visible_indices].flatten()
        norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
        sim = (np.dot(v1, v2) / (norm1 * norm2)) * 100 if (norm1 * norm2) != 0 else 0
        
        group_scores[group] = sim
        total_weighted_score += sim * WEIGHTS[group]
        total_weight_used += WEIGHTS[group]
        
    final = (total_weighted_score / total_weight_used) if total_weight_used > 0 else 0
    return final, group_scores

# --- MAIN ---
with open(JSON_PATH, 'r') as f:
    target_data = json.load(f)
target_features = [get_full_body_features(f['landmarks'], True) for f in target_data]

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.PoseLandmarkerOptions(base_options=base_options, running_mode=vision.RunningMode.VIDEO)

error_log = [] 

with vision.PoseLandmarker.create_from_options(options) as landmarker:
    cap = cv2.VideoCapture(0)
    current_target_idx = 0
    last_advance_time = time.time()

    while cap.isOpened():
        success, frame = cap.read()
        if not success: break
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        result = landmarker.detect_for_video(mp_image, int(time.time() * 1000))

        if result.pose_landmarks:
            curr_full = result.pose_landmarks[0]
            curr_rel = get_full_body_features(curr_full)

            best_score, best_idx, best_group_breakdown = 0, current_target_idx, {}
            start_s = max(0, current_target_idx - 15)
            end_s = min(len(target_data), current_target_idx + 15)

            for i in range(start_s, end_s):
                score, breakdown = evaluate_groups(curr_full, curr_rel, target_features[i])
                if score > best_score:
                    best_score, best_idx, best_group_breakdown = score, i, breakdown

            # --- ADVANCE OR LOG MISTAKES ---
            if best_idx > current_target_idx:
                current_target_idx = best_idx
                last_advance_time = time.time()
            else:
                time_stuck = time.time() - last_advance_time
                if time_stuck > STUCK_TIMEOUT:
                    
                    # --- THE FIX: FIND THE BIGGEST PHYSICAL GAP ---
                    max_error_distance = -1
                    worst_group = "torso_hips" # Fallback
                    worst_landmark_idx = 24    # Fallback
                    targ_rel = target_features[current_target_idx]
                    
                    # We check EVERY group, not just the one with the lowest angle score
                    for group, indices in GROUPS.items():
                        for joint_idx in indices:
                            if curr_full[joint_idx].visibility > VIS_THRESHOLD:
                                # Calculate actual physical distance between your joint and target joint
                                dist = np.linalg.norm(curr_rel[joint_idx] - targ_rel[joint_idx])
                                if dist > max_error_distance:
                                    max_error_distance = dist
                                    worst_group = group
                                    worst_landmark_idx = joint_idx
                    
                    # Get the EXACT target coordinates from the ghost
                    targ_landmarks = target_data[current_target_idx]['landmarks']
                                
                    error_log.append({
                        "frame_index": current_target_idx,
                        "timestamp": time.strftime("%H:%M:%S"),
                        "failed_group": worst_group,
                        "failed_joint_id": int(worst_landmark_idx),
                        "wrong_x": round(float(curr_rel[worst_landmark_idx][0]), 4),
                        "right_x": round(float(targ_rel[worst_landmark_idx][0]), 4),
                        "wrong_y": round(float(curr_rel[worst_landmark_idx][1]), 4),
                        "right_y": round(float(targ_rel[worst_landmark_idx][1]), 4),
                        "score_at_fail": round(best_score, 2)
                    })
                    
                    current_target_idx = min(len(target_data)-1, current_target_idx + 15)
                    last_advance_time = time.time()

            # --- VISUALS ---
            ghost_lms = target_data[current_target_idx]['landmarks']
            for start, end in [(11,12), (12,24), (24,23), (23,11), (11,13), (13,15), (12,14), (14,16), (23,25), (25,27), (24,26), (26,28)]:
                p1 = (int(ghost_lms[start]['x'] * w), int(ghost_lms[start]['y'] * h))
                p2 = (int(ghost_lms[end]['x'] * w), int(ghost_lms[end]['y'] * h))
                cv2.line(frame, p1, p2, (255, 255, 0), 2)

            cv2.putText(frame, f"MATCH: {int(best_score)}%", (20, h-30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow('Tracking Data', frame)

        if current_target_idx >= len(target_data) - 1 or cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()

# --- SAVE TO ONLY ONE JSON FILE ---
with open(ERROR_LOG_PATH, 'w') as f:
    json.dump(error_log, f, indent=2)

print(f"Logged {len(error_log)} detailed incidents to {ERROR_LOG_PATH}")