import json
import sys
import numpy as np
import os
from collections import deque

# --- CONFIGURATION ---
# Physics thresholds
SMOOTHING_WINDOW = 4       # Higher = smoother but more lag
MOVEMENT_THRESHOLD = 0.025 # How much a joint must move to trigger 'moving'
DEBOUNCE_FRAMES = 8        # Minimum duration for an action to be valid

JOINTS = {
    13: {"name": "left arm", "anchor": 11}, 
    14: {"name": "right arm", "anchor": 12},
    15: {"name": "left hand", "anchor": 11}, 
    16: {"name": "right hand", "anchor": 12},
    25: {"name": "left knee", "anchor": 23}, 
    26: {"name": "right knee", "anchor": 24}
}

# --- SMOOTHING HELPER ---
def smooth_data(frames, window_size):
    """Applies Moving Average to coordinate data to reduce jitter."""
    smoothed_frames = []
    history = deque(maxlen=window_size)
    
    for frame in frames:
        lms = frame['landmarks']
        if not lms: 
            smoothed_frames.append(frame) # Keep empty if empty
            continue
            
        history.append(lms)
        
        # Calculate average for this frame based on history
        avg_lms = []
        num_landmarks = len(lms)
        
        if len(history) > 0:
            for i in range(num_landmarks):
                # Average X, Y, Z
                avg_x = sum(h[i]['x'] for h in history) / len(history)
                avg_y = sum(h[i]['y'] for h in history) / len(history)
                avg_z = sum(h[i]['z'] for h in history) / len(history)
                avg_lms.append({'id': i, 'x': avg_x, 'y': avg_y, 'z': avg_z})
        
        smoothed_frames.append({'frame': frame['frame'], 'landmarks': avg_lms})
        
    return smoothed_frames

# --- MAIN ANALYSIS ---
def analyze(json_path):
    print(f"Analyzing physics in: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    raw_frames = data['coordinates']
    # 1. Apply Smoothing
    clean_frames = smooth_data(raw_frames, SMOOTHING_WINDOW)
    
    active_phases = {}
    completed_phases = []
    
    # 2. Iterate Frames
    for i in range(5, len(clean_frames)):
        curr_frame = clean_frames[i]
        prev_frame = clean_frames[i - 5] # Compare with 5 frames ago for velocity
        
        if not curr_frame['landmarks'] or not prev_frame['landmarks']:
            continue
            
        c_lms = curr_frame['landmarks']
        p_lms = prev_frame['landmarks']
        
        for idx, info in JOINTS.items():
            # Get positions
            curr_pos = np.array([c_lms[idx]['x'], c_lms[idx]['y']])
            prev_pos = np.array([p_lms[idx]['x'], p_lms[idx]['y']])
            
            # Anchor (Shoulder/Hip) positions to detect relative movement (extension)
            anchor_idx = info['anchor']
            curr_anchor = np.array([c_lms[anchor_idx]['x'], c_lms[anchor_idx]['y']])
            prev_anchor = np.array([p_lms[anchor_idx]['x'], p_lms[anchor_idx]['y']])
            
            # Metrics
            velocity = np.linalg.norm(curr_pos - prev_pos)
            dist_curr = np.linalg.norm(curr_pos - curr_anchor)
            dist_prev = np.linalg.norm(prev_pos - prev_anchor)
            extension_change = dist_curr - dist_prev
            vertical_change = curr_pos[1] - prev_pos[1] # Y is down in image coords
            
            action = None
            
            # --- LOGIC TREE ---
            if velocity > MOVEMENT_THRESHOLD:
                if extension_change > 0.02: action = f"extending {info['name']}"
                elif extension_change < -0.02: action = f"retracting {info['name']}"
                elif vertical_change < -0.02: action = f"raising {info['name']}"
                elif vertical_change > 0.02: action = f"lowering {info['name']}"
                
            # --- PHASE MANAGEMENT ---
            current_active = active_phases.get(info['name'])
            
            if current_active is None:
                if action:
                    active_phases[info['name']] = {"action": action, "start": i}
            else:
                if action != current_active['action']:
                    # Action ended or changed
                    duration = i - current_active['start']
                    if duration >= DEBOUNCE_FRAMES:
                        completed_phases.append({
                            "action": current_active['action'],
                            "start_frame": current_active['start'],
                            "end_frame": i - 1,
                            "duration": duration
                        })
                    
                    if action:
                        active_phases[info['name']] = {"action": action, "start": i}
                    else:
                        del active_phases[info['name']]

    # 3. Save Results
    base_name = os.path.splitext(os.path.basename(json_path))[0].replace("_coords", "")
    output_file = f"{base_name}_actions.json"
    
    final_output = {
        "source_coords": json_path,
        "action_phases": completed_phases
    }
    
    with open(output_file, 'w') as f:
        json.dump(final_output, f, indent=4)
        
    print(f"[Success] Found {len(completed_phases)} actions.")
    print(f"Saved analysis to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze(sys.argv[1])
    else:
        print("Please provide a coordinate JSON file.")