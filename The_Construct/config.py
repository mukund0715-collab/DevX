import os

# --- BASE SETTINGS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- FOLDER PATHS ---
VIDEO_FOLDER = os.path.join(BASE_DIR, "Raw_video")
SKELETON_FOLDER = os.path.join(BASE_DIR, "sck")
MISTAKES_FOLDER = os.path.join(BASE_DIR, "mistakes")

# --- FILE PATHS ---
PROFILE_FILE = os.path.join(BASE_DIR, "operator_profile.json")
SESSION_STATS_PATH = os.path.join(BASE_DIR, "session_stats.json")
BACKGROUND_IMAGE = os.path.join(BASE_DIR, "background.jpg")

# --- SCRIPT PATHS ---
LIVE_SCRIPT = os.path.join(BASE_DIR, "live.py")
COACH_SCRIPT = os.path.join(BASE_DIR, "ai_coach.py")

# --- GAMIFICATION SETTINGS ---
XP_PER_LEVEL = 500  # XP needed to level up

# Rank Titles (Level: Title)
RANKS = {
    1: "INITIATE",
    3: "OPERATIVE",
    5: "VANGUARD",
    10: "SHADOW",
    15: "SPECTRE",
    20: "MORPHEUS"
}

# Level Requirements to Unlock Moves (Substring: Level)
# If a video filename contains "KICK", you need Level 3 to open it.
MOVE_UNLOCKS = {
    "PUNCH": 1,    # Available immediately
    "DODGE": 2,    # Unlocks at Lvl 2
    "DUNK": 3,     # Unlocks at Lvl 3 (Escape Drills)
    "KICK": 5,     # Unlocks at Lvl 5
    "COMBO": 10    # Unlocks at Lvl 10
}

# --- INITIALIZATION ---
for folder in [VIDEO_FOLDER, SKELETON_FOLDER, MISTAKES_FOLDER]:
    os.makedirs(folder, exist_ok=True)