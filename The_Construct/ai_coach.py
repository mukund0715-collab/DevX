import json
import os
import sys

# --- CONFIGURATION ---
JOINT_NAMES = {
    0: 'nose', 7: 'left ear', 8: 'right ear',
    11: 'left shoulder', 12: 'right shoulder',
    13: 'left elbow', 14: 'right elbow',
    15: 'left wrist', 16: 'right wrist',
    17: 'left pinky', 18: 'right pinky',
    19: 'left index finger', 20: 'right index finger',
    21: 'left thumb', 22: 'right thumb',
    23: 'left hip', 24: 'right hip',
    25: 'left knee', 26: 'right knee',
    27: 'left ankle', 28: 'right ankle',
    29: 'left heel', 30: 'right heel',
    31: 'left toe', 32: 'right toe'
}

def translate_to_gym_slang(joint_name, y_diff, x_diff):
    advice = []
    if y_diff > 0.08: advice.append("too low")
    elif y_diff < -0.08: advice.append("too high")
    if x_diff > 0.08: advice.append("drifting right")
    elif x_diff < -0.08: advice.append("drifting left")
    
    action_text = " and ".join(advice) if advice else "out of alignment"

    if any(x in joint_name for x in ['ear', 'nose']):
        return "Head/Neck", f"Your head was {action_text}. Keep spine neutral!"
    elif any(x in joint_name for x in ['wrist', 'hand']):
        return "Hands", f"Your {joint_name} was {action_text}. Check guard."
    elif 'elbow' in joint_name:
        return "Elbows", f"Your {joint_name} was {action_text}. Watch flare!"
    elif 'knee' in joint_name:
        return "Knees", f"Your {joint_name} was {action_text}. Stay stable!"
    elif any(x in joint_name for x in ['hip']):
        return "Core", f"Your {joint_name} was {action_text}. Engage core!"
    else:
        return joint_name.title(), f"Your {joint_name} was {action_text}."

def analyze_session(log_path):
    print(f"[COACH] Analyzing: {log_path}")
    
    # Define output path immediately
    output_path = log_path.replace(".json", "_analysis.json")
    
    analysis_output = []

    # 1. READ LOG (Safely)
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r') as f:
                mistakes = json.load(f)
        except Exception as e:
            print(f"[COACH] Error reading log: {e}")
            mistakes = []
    else:
        print("[COACH] Log file not found.")
        mistakes = []

    # 2. PROCESS MISTAKES
    if mistakes:
        for m in mistakes:
            raw_joint = JOINT_NAMES.get(m.get('failed_joint_id', 0), "Joint")
            y_diff = m.get('wrong_y', 0) - m.get('right_y', 0)
            x_diff = m.get('wrong_x', 0) - m.get('right_x', 0)
            
            category, cue = translate_to_gym_slang(raw_joint, y_diff, x_diff)
            
            analysis_output.append({
                "frame": m['frame_index'],
                "time": m['timestamp'],
                "score": m.get('score_at_fail', 0),
                "category": category,
                "advice": cue
            })
    else:
        print("[COACH] No mistakes found (Perfect Form).")

    # 3. SAVE ANALYSIS (CRITICAL: Always save, even if empty!)
    try:
        with open(output_path, 'w') as f:
            json.dump(analysis_output, f, indent=2)
        print(f"[COACH] Analysis saved to: {output_path}")
    except Exception as e:
        print(f"[COACH] Critical Error saving analysis: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
        analyze_session(log_file)
    else:
        print("[COACH] No log file argument provided.")
