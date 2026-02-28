import json
import os
import sys
import subprocess
from datetime import datetime
import config

def load_or_create_profile(alias):
    # Default Profile with Game Stats
    profile = {
        "alias": alias,
        "xp": 0,
        "level": 1,
        "high_scores": {},  # Format: {"MOVE_NAME": 85}
        "total_sessions": 0,
        "rank_title": config.RANKS[1]
    }
    
    if os.path.exists(config.PROFILE_FILE):
        try:
            with open(config.PROFILE_FILE, 'r') as f:
                data = json.load(f)
                if data.get("alias") == alias:
                    profile.update(data)
        except: pass
    
    # Ensure rank is synced
    profile["rank_title"] = get_rank_title(profile["level"])
    save_profile(profile)
    return profile

def save_profile(profile):
    with open(config.PROFILE_FILE, "w") as f:
        json.dump(profile, f)

def get_rank_title(level):
    # Find the highest rank less than or equal to current level
    titles = sorted(config.RANKS.keys())
    current_title = "UNKNOWN"
    for lvl in titles:
        if level >= lvl:
            current_title = config.RANKS[lvl]
    return current_title

def update_xp_from_session(profile, move_name):
    if os.path.exists(config.SESSION_STATS_PATH):
        try:
            with open(config.SESSION_STATS_PATH, 'r') as f:
                stats = json.load(f)
            
            xp_gained = stats.get("xp_gained", 0)
            score = int(stats.get("avg_accuracy", 0))
            
            profile['xp'] += xp_gained
            profile['total_sessions'] += 1
            
            # Update High Score
            current_best = profile['high_scores'].get(move_name, 0)
            if score > current_best:
                profile['high_scores'][move_name] = score
            
            # Level Up Logic
            # XP curve: Level * XP_PER_LEVEL (e.g., Lvl 1 needs 500, Lvl 2 needs 1000)
            req_xp = profile['level'] * config.XP_PER_LEVEL
            if profile['xp'] >= req_xp:
                profile['level'] += 1
                profile['xp'] = profile['xp'] - req_xp # Carry over excess XP
                profile['rank_title'] = get_rank_title(profile['level'])
            
            save_profile(profile)
            return xp_gained, score >= current_best  # Return if it was a new record
        except Exception as e:
            print(f"[LOGIC] XP Update Error: {e}")
    return 0, False

def get_available_moves():
    moves = {}
    if not os.path.exists(config.VIDEO_FOLDER): return moves
    
    files = [f for f in os.listdir(config.VIDEO_FOLDER) if f.lower().endswith(('.mp4', '.avi'))]
    for f in files:
        name_parts = os.path.splitext(f)[0].split('_')
        base = "_".join(name_parts[:-1]).upper() if len(name_parts) > 1 else os.path.splitext(f)[0].upper()
        code = name_parts[-1] if len(name_parts) > 1 else 'c'
        if base not in moves: moves[base] = {}
        moves[base][code] = f
    return moves

def check_skeleton_data(video_filename):
    json_name = f"{os.path.splitext(video_filename)[0]}_coords.json"
    return os.path.exists(os.path.join(config.SKELETON_FOLDER, json_name))

def is_move_locked(move_name, current_level):
    """Returns (is_locked, required_level)"""
    for key, req_lvl in config.MOVE_UNLOCKS.items():
        if key in move_name:
            if current_level < req_lvl:
                return True, req_lvl
    return False, 0

def run_training_session(json_path, target_log_path):
    print(f"[LOGIC] Running Tracker -> {target_log_path}")
    subprocess.run([sys.executable, config.LIVE_SCRIPT, json_path, target_log_path], check=False)
    
    if os.path.exists(target_log_path):
        print(f"[LOGIC] Running Coach...")
        subprocess.run([sys.executable, config.COACH_SCRIPT, target_log_path], check=False)

def get_latest_analysis():
    if not os.path.exists(config.MISTAKES_FOLDER): return None
    files = [os.path.join(config.MISTAKES_FOLDER, f) for f in os.listdir(config.MISTAKES_FOLDER) if f.endswith("_analysis.json")]
    if not files: return None
    return max(files, key=os.path.getmtime)