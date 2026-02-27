import json
import os
import time
import cv2

try:
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 175) # Set a good talking speed
    HAS_VOICE = True
except ImportError:
    HAS_VOICE = False

LOG_PATH = 'stuck_coordinates_log.json'
REFERENCE_VIDEO_PATH = 'me3.mp4'

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

    # Group into body parts
    if any(x in joint_name for x in ['ear', 'nose']):
        return f"Head/Neck", f"Your head was {action_text}. Keep your spine neutral and don't crank your neck!"
    elif any(x in joint_name for x in ['finger', 'thumb', 'pinky', 'wrist']):
        return f"Hands/Grip", f"Your {joint_name} was {action_text}. Check your grip and hand placement."
    elif 'elbow' in joint_name:
        return f"Elbows", f"Your {joint_name} was {action_text}. Watch your elbow flare!"
    elif 'knee' in joint_name:
        return f"Knees", f"Your {joint_name} was {action_text}. Don't let your knees cave in!"
    elif any(x in joint_name for x in ['hip']):
        return f"Hips/Core", f"Your {joint_name} was {action_text}. Keep your core tight and hit depth!"
    else:
        return joint_name.title(), f"Your {joint_name} was {action_text}."

def coach_speak(text):
    """Speaks the text out loud if pyttsx3 is installed."""
    if HAS_VOICE:
        # Strip out emojis before speaking so the robot doesn't say "flexed biceps"
        clean_text = text.replace('💪', '').replace('🏋️', '').replace('👊', '').replace('📋', '').replace('▶', '').replace('📺', '')
        engine.say(clean_text)
        engine.runAndWait()

def show_video_at_frame(frame_index):
    """Pops up the reference video around the specific frame of the mistake."""
    if not os.path.exists(REFERENCE_VIDEO_PATH):
        print(f"  {Colors.FAIL}Couldn't find '{REFERENCE_VIDEO_PATH}' for playback. Skipping video.{Colors.ENDC}")
        return

    cap = cv2.VideoCapture(REFERENCE_VIDEO_PATH)
    
    # Start playback about 1.5 seconds (45 frames) before the target pose
    start_frame = max(0, frame_index - 45)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    print(f"  {Colors.GREEN}Loading tape... (Press 'q' on the video window to close early){Colors.ENDC}")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
            
        current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        
        cv2.putText(frame, "PERFECT FORM TARGET", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Flash a warning text when the exact frame you messed up on is playing
        if abs(current_frame - frame_index) < 10:
            cv2.putText(frame, "--- THIS IS THE TARGET POSE ---", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 5)
            
        cv2.imshow('AI Coach Replay', frame)
        
        # Stop playback about 1.5 seconds after the target pose
        if current_frame > frame_index + 45:
            break
            
        # Play at roughly 30fps
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def generate_report():
    if not os.path.exists(LOG_PATH):
        msg = "No mistake log found. Flawless set, bro! 💪"
        print(f"{Colors.GREEN}{Colors.BOLD}{msg}{Colors.ENDC}")
        coach_speak(msg)
        return

    with open(LOG_PATH, 'r') as f:
        mistakes = json.load(f)

    if not mistakes:
         msg = "Log is empty. Flawless set, bro! 💪"
         print(f"{Colors.GREEN}{Colors.BOLD}{msg}{Colors.ENDC}")
         coach_speak(msg)
         return

    print(f"\n{Colors.HEADER}{Colors.BOLD}=== 🏋️  AI COACH TAPE REVIEW ==={Colors.ENDC}")
    intro_msg = "Let's look at the tape from your last set..."
    print(intro_msg + "\n")
    coach_speak(intro_msg)
    time.sleep(1)

    # --- PHASE 1: THE SUMMARY ---
    issues_count = {}
    formatted_mistakes = []

    for m in mistakes:
        raw_joint = JOINT_NAMES.get(m['failed_joint_id'], f"joint {m['failed_joint_id']}")
        y_diff = m['wrong_y'] - m['right_y']
        x_diff = m['wrong_x'] - m['right_x']
        
        body_part, coach_cue = translate_to_gym_slang(raw_joint, y_diff, x_diff)
        
        # Count which body parts are failing the most
        issues_count[body_part] = issues_count.get(body_part, 0) + 1
        
        formatted_mistakes.append({
            'time': m['timestamp'],
            'match': m['score_at_fail'],
            'cue': coach_cue,
            'frame_index': m['frame_index']
        })

    print(f"{Colors.WARNING}📋 QUICK SUMMARY:{Colors.ENDC}")
    summary_msg = f"I caught {len(mistakes)} total form breakdowns."
    print(summary_msg)
    coach_speak(summary_msg)
    
    # Sort by the most frequent mistakes
    sorted_issues = sorted(issues_count.items(), key=lambda item: item[1], reverse=True)
    for part, count in sorted_issues:
        issue_msg = f"{part}: Messed up {count} times."
        print(f" - {issue_msg}")
        coach_speak(issue_msg)
    
    print("\n" + "-"*40)

    # --- PHASE 2: INTERACTIVE PLAY-BY-PLAY ---
    response = input(f"{Colors.BLUE}Wanna see the play-by-play breakdown? (y/n): {Colors.ENDC}").strip().lower()
    
    if response == 'y':
        print(f"\n{Colors.HEADER}Alright, here are the receipts:{Colors.ENDC}\n")
        coach_speak("Alright, here are the receipts.")
        
        # We'll skip consecutive duplicates to reduce spam
        last_cue = ""
        for i, m in enumerate(formatted_mistakes, 1):
            if m['cue'] == last_cue:
                continue # Skip if it's the exact same mistake as the last frame
                
            print(f"{Colors.FAIL}▶ {m['time']} (Match: {m['match']}%){Colors.ENDC}")
            print(f"  {m['cue']}")
            coach_speak(m['cue'])
            time.sleep(0.2) # Little delay makes it feel like it's reading it out
            
            # --- VIDEO PLAYBACK TRIGGER ---
            vid_response = input(f"  {Colors.BLUE}📺 See the perfect target pose tape for this? (y/n): {Colors.ENDC}").strip().lower()
            if vid_response == 'y':
                show_video_at_frame(m['frame_index'])
            print("") # Empty line for spacing
            
            last_cue = m['cue']
            
        outro = "That's it! Rest up and let's fix it on the next set. 👊"
        print(f"{Colors.GREEN}{Colors.BOLD}{outro}{Colors.ENDC}\n")
        coach_speak(outro)
    else:
        outro_short = "Got it. Keep those main cues in mind for the next set! 👊"
        print(f"\n{Colors.GREEN}{Colors.BOLD}{outro_short}{Colors.ENDC}\n")
        coach_speak(outro_short)

if __name__ == "__main__":
    generate_report()