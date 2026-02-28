import json
import os
import time
import cv2
import sys # <--- REQUIRED for app connection

try:
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 175) 
    HAS_VOICE = True
except ImportError:
    HAS_VOICE = False

# --- CONFIGURATION ---
LOG_PATH = 'stuck_coordinates_log.json'

# Receive the video path from app.py arguments
if len(sys.argv) > 1:
    REFERENCE_VIDEO_PATH = sys.argv[1]
else:
    REFERENCE_VIDEO_PATH = 'Raw_video/punches_c.mp4' # Default fallback if run alone

# --- TERMINAL COLORS ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

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
    """Converts robotic joint names into actual coaching cues."""
    advice = []
    
    # Y-Axis Logic (0 is ceiling, 1 is floor)
    if y_diff > 0.08: advice.append("too low")
    elif y_diff < -0.08: advice.append("too high")
        
    # X-Axis Logic (0 is left, 1 is right)
    if x_diff > 0.08: advice.append("drifting right")
    elif x_diff < -0.08: advice.append("drifting left")
        
    action_text = " and ".join(advice) if advice else "out of alignment"

    if any(x in joint_name for x in ['ear', 'nose']):
        return f"Head/Neck", f"Your head was {action_text}. Keep your spine neutral!"
    elif any(x in joint_name for x in ['finger', 'thumb', 'pinky', 'wrist']):
        return f"Hands/Grip", f"Your {joint_name} was {action_text}. Check your grip."
    elif 'elbow' in joint_name:
        return f"Elbows", f"Your {joint_name} was {action_text}. Watch your elbow flare!"
    elif 'knee' in joint_name:
        return f"Knees", f"Your {joint_name} was {action_text}. Don't let your knees cave in!"
    elif any(x in joint_name for x in ['hip']):
        return f"Hips/Core", f"Your {joint_name} was {action_text}. Keep your core tight!"
    else:
        return joint_name.title(), f"Your {joint_name} was {action_text}."

def coach_speak(text):
    if HAS_VOICE:
        clean_text = text.replace('💪', '').replace('🏋️', '').replace('👊', '').replace('📋', '').replace('▶', '').replace('📺', '')
        engine.say(clean_text)
        engine.runAndWait()

def show_video_at_frame(frame_index):
    if not os.path.exists(REFERENCE_VIDEO_PATH):
        print(f"  {Colors.FAIL}Couldn't find '{REFERENCE_VIDEO_PATH}'. Skipping.{Colors.ENDC}")
        return

    cap = cv2.VideoCapture(REFERENCE_VIDEO_PATH)
    start_frame = max(0, frame_index - 45)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    print(f"  {Colors.GREEN}Loading tape... (Press 'q' to close){Colors.ENDC}")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        
        cv2.putText(frame, "PERFECT FORM TARGET", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        if abs(current_frame - frame_index) < 10:
            cv2.putText(frame, "--- TARGET POSE ---", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 5)
            
        cv2.imshow('AI Coach Replay', frame)
        if current_frame > frame_index + 45: break
        if cv2.waitKey(30) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

def generate_report():
    if not os.path.exists(LOG_PATH):
        print(f"{Colors.GREEN}No log found. Clean set!{Colors.ENDC}")
        return

    with open(LOG_PATH, 'r') as f:
        mistakes = json.load(f)

    if not mistakes:
         msg = "Log is empty. Flawless set, bro! 💪"
         print(f"{Colors.GREEN}{Colors.BOLD}{msg}{Colors.ENDC}")
         coach_speak(msg)
         return

    print(f"\n{Colors.HEADER}{Colors.BOLD}=== 🏋️  AI COACH TAPE REVIEW ==={Colors.ENDC}")
    intro_msg = f"I caught {len(mistakes)} form errors."
    print(intro_msg)
    coach_speak(intro_msg)

    # Summary Loop
    formatted_mistakes = []
    for m in mistakes:
        raw_joint = JOINT_NAMES.get(m['failed_joint_id'], f"joint {m['failed_joint_id']}")
        y_diff = m['wrong_y'] - m['right_y']
        x_diff = m['wrong_x'] - m['right_x']
        body_part, coach_cue = translate_to_gym_slang(raw_joint, y_diff, x_diff)
        
        formatted_mistakes.append({
            'time': m['timestamp'], 'match': m['score_at_fail'],
            'cue': coach_cue, 'frame_index': m['frame_index']
        })

    # Interactive Breakdown
    response = input(f"{Colors.BLUE}Review the tape? (y/n): {Colors.ENDC}").strip().lower()
    if response == 'y':
        last_cue = ""
        for m in formatted_mistakes:
            if m['cue'] == last_cue: continue
            
            print(f"{Colors.FAIL}▶ {m['time']} (Match: {m['match']}%){Colors.ENDC}")
            print(f"  {m['cue']}")
            coach_speak(m['cue'])
            
            vid_response = input(f"  {Colors.BLUE}📺 See target video? (y/n): {Colors.ENDC}").strip().lower()
            if vid_response == 'y':
                show_video_at_frame(m['frame_index'])
            print("")
            last_cue = m['cue']

if __name__ == "__main__":
    generate_report()
