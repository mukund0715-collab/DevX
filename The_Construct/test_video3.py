import cv2
import json
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- 1. CONFIGURATION & SETUP ---
VIDEO_PATH = "Bmj/n0.mp4"
MODEL_PATH = 'pose_landmarker_heavy.task'
OUTPUT_FILE = 'n0_complete_data.json'

VISIBILITY_THRESHOLD = 0.5  
WINDOW = 5                  
TURN_THRESHOLD = 0.08
MIN_PHASE_FRAMES = 8

JOINTS_OF_INTEREST = {
    13: {"name": "left arm", "threshold": 0.08, "parent": 11},
    14: {"name": "right arm", "threshold": 0.08, "parent": 12},
    15: {"name": "left hand", "threshold": 0.05, "parent": 11},  
    16: {"name": "right hand", "threshold": 0.05, "parent": 12}, 
    25: {"name": "left knee", "threshold": 0.08, "parent": 23},
    26: {"name": "right knee", "threshold": 0.08, "parent": 24},
    27: {"name": "left foot", "threshold": 0.05, "parent": 23},  
    28: {"name": "right foot", "threshold": 0.05, "parent": 24}  
}

# --- 2. HELPER FUNCTIONS ---
def get_hip_center(landmarks):
    left_hip = landmarks[23]
    right_hip = landmarks[24]
    return np.array([(left_hip['x'] + right_hip['x'])/2, (left_hip['y'] + right_hip['y'])/2])

def get_joint_pos(landmarks, idx):
    return np.array([landmarks[idx]['x'], landmarks[idx]['y']])

# --- 3. MAIN PROCESSING LOOP ---
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO
)

all_video_data = [] # Stores X, Y, Z for every frame
last_good_positions = {}
active_phases = {}
completed_phases = [] # Stores Action Tags

with vision.PoseLandmarker.create_from_options(options) as landmarker:
    cap = cv2.VideoCapture(VIDEO_PATH)
    frame_idx = 0
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success: break

        timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.pose_landmarks:
            current_frame_landmarks = []
            
            # Step A: Visibility Filtering & Coordinate Storage
            for idx, lm in enumerate(result.pose_landmarks[0]):
                if lm.visibility >= VISIBILITY_THRESHOLD:
                    clean_pos = {'x': lm.x, 'y': lm.y, 'z': lm.z}
                    last_good_positions[idx] = clean_pos
                else:
                    clean_pos = last_good_positions.get(idx, {'x': lm.x, 'y': lm.y, 'z': lm.z})

                current_frame_landmarks.append({
                    'landmark_id': idx,
                    **clean_pos,
                    'visibility': lm.visibility 
                })
            
            # Append to our coordinate list
            all_video_data.append({
                'frame': frame_idx,
                'timestamp_ms': timestamp_ms,
                'landmarks': current_frame_landmarks
            })

            # Step B: Kinematic Action Tagging
            if frame_idx >= WINDOW:
                curr_lms = all_video_data[frame_idx]['landmarks']
                prev_lms = all_video_data[frame_idx - WINDOW]['landmarks']
                
                # Detect Body Turning
                curr_twist = curr_lms[11]['z'] - curr_lms[12]['z']
                prev_twist = prev_lms[11]['z'] - prev_lms[12]['z']
                is_turning = abs(curr_twist - prev_twist) > TURN_THRESHOLD
                torso_action = "turning the body" if is_turning else None
                
                # Torso tracking
                active_torso = active_phases.get("torso")
                if active_torso is None:
                    if torso_action: active_phases["torso"] = {"action": torso_action, "start_frame": frame_idx}
                else:
                    if torso_action != active_torso["action"]:
                        duration = frame_idx - active_torso["start_frame"]
                        if duration >= MIN_PHASE_FRAMES:
                            completed_phases.append({"start_frame": active_torso["start_frame"], "end_frame": frame_idx - 1, "action": active_torso["action"], "duration_frames": duration})
                        if torso_action: active_phases["torso"] = {"action": torso_action, "start_frame": frame_idx}
                        else: del active_phases["torso"]

                # Limb Evaluation
                for idx, info in JOINTS_OF_INTEREST.items():
                    joint_name = info["name"]
                    curr_pos = get_joint_pos(curr_lms, idx)
                    prev_pos = get_joint_pos(prev_lms, idx)
                    
                    if "left arm" in joint_name or "left hand" in joint_name: anchor_idx = 11
                    elif "right arm" in joint_name or "right hand" in joint_name: anchor_idx = 12
                    elif "left" in joint_name: anchor_idx = 23
                    else: anchor_idx = 24
                        
                    curr_anchor = get_joint_pos(curr_lms, anchor_idx)
                    prev_anchor = get_joint_pos(prev_lms, anchor_idx)
                    
                    d_dist = np.linalg.norm(curr_pos - curr_anchor) - np.linalg.norm(prev_pos - prev_anchor)
                    dy = curr_pos[1] - prev_pos[1]
                    total_movement = np.linalg.norm(curr_pos - prev_pos)
                    
                    current_action = None
                    if total_movement > info["threshold"]:
                        verb = "moving"
                        if d_dist > 0.02: verb = "extending"
                        elif d_dist < -0.02: verb = "retracting"
                        elif dy < -0.02: verb = "raising"
                        elif dy > 0.02: verb = "lowering"
                        current_action = f"{verb} the {joint_name}"
                        
                    if is_turning and ("arm" in joint_name or "hand" in joint_name) and "retracting" in str(current_action):
                        current_action = None
                        
                    currently_active = active_phases.get(joint_name)
                    if currently_active is None:
                        if current_action: active_phases[joint_name] = {"action": current_action, "start_frame": frame_idx}
                    else:
                        if current_action != currently_active["action"]:
                            duration = frame_idx - currently_active["start_frame"]
                            if duration >= MIN_PHASE_FRAMES:
                                completed_phases.append({"start_frame": currently_active["start_frame"], "end_frame": frame_idx - 1, "action": currently_active["action"], "duration_frames": duration})
                            if current_action: active_phases[joint_name] = {"action": current_action, "start_frame": frame_idx}
                            else: del active_phases[joint_name]

        cv2.imshow('Processing...', frame)
        frame_idx += 1
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

# --- 4. CLEANUP AND SAVE ---
for joint_name, active_phase in active_phases.items():
    completed_phases.append({"start_frame": active_phase["start_frame"], "end_frame": frame_idx - 1, "action": active_phase["action"]})

completed_phases.sort(key=lambda x: x["start_frame"])

# COMBINED DATA STRUCTURE
final_output = {
    "metadata": {
        "video_source": VIDEO_PATH,
        "total_frames": frame_idx
    },
    "action_phases": completed_phases,
    "coordinates": all_video_data
}

with open(OUTPUT_FILE, 'w') as f:
    json.dump(final_output, f, indent=4)

print(f"Done! Saved {len(completed_phases)} action tags and {len(all_video_data)} frames of coordinates to {OUTPUT_FILE}")