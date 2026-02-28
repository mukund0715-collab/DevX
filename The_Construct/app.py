import customtkinter as ctk
import subprocess
import json
import os
import sys
import cv2
from PIL import Image, ImageTk
from datetime import datetime

# --- CONFIGURATION ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green") 

# --- CRITICAL: ABSOLUTE PATHS ---
# This ensures the app finds your scripts no matter where you run it from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Folders
VIDEO_FOLDER = os.path.join(BASE_DIR, "Raw_video")
SKELETON_FOLDER = os.path.join(BASE_DIR, "sck")
MISTAKES_FOLDER = os.path.join(BASE_DIR, "mistakes")

# Files
PROFILE_FILE = os.path.join(BASE_DIR, "operator_profile.json")
SESSION_STATS_PATH = os.path.join(BASE_DIR, "session_stats.json")

# Scripts
LIVE_SCRIPT = os.path.join(BASE_DIR, "live.py")
COACH_SCRIPT = os.path.join(BASE_DIR, "ai_coach.py")

print(f"[SYSTEM] App initialized at: {BASE_DIR}")

# --- VIDEO PLAYER WIDGET ---
class VideoPlayer(ctk.CTkLabel):
    def __init__(self, master, width, height, video_path):
        super().__init__(master, text="", width=width, height=height, fg_color="black")
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.target_width = width
        self.target_height = height
        self.is_playing = False
        self.after_id = None
        self.update_frame()

    def update_frame(self):
        if not self.cap.isOpened(): return
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop video
            ret, frame = self.cap.read()

        if ret:
            # Resize with Aspect Ratio (No Stretching!)
            h, w = frame.shape[:2]
            scale = min(self.target_width / w, self.target_height / h)
            new_w, new_h = int(w * scale), int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h))
            
            # Center on Black Background
            canvas = Image.new("RGB", (self.target_width, self.target_height), (0, 0, 0))
            paste_x, paste_y = (self.target_width - new_w) // 2, (self.target_height - new_h) // 2
            frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            canvas.paste(frame_pil, (paste_x, paste_y))
            
            ctk_img = ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(self.target_width, self.target_height))
            self.configure(image=ctk_img)
            self.image = ctk_img 
            
        if self.is_playing:
            self.after_id = self.after(33, self.update_frame)

    def seek(self, frame_index):
        """Jump to specific frame and pause"""
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_index))
        self.is_playing = True
        self.update_frame()
        # Optional: Auto-pause after 2 seconds could go here

    def play(self):
        self.is_playing = True
        self.update_frame()

    def stop(self):
        self.is_playing = False
        if self.after_id: self.after_cancel(self.after_id)
        self.cap.release()

# --- MAIN APPLICATION ---
class MorpheusTerminal(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PROJECT MORPHEUS // SELF-DEFENSE INITIATIVE")
        self.geometry("1200x800")
        
        self.bg_image = None
        bg_path = os.path.join(BASE_DIR, "background.jpg")
        if os.path.exists(bg_path):
            img = Image.open(bg_path)
            self.bg_image = ctk.CTkImage(light_image=img, dark_image=img, size=(1920, 1080))

        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.current_frame = None
        self.show_login_screen()

    def set_background(self, parent_frame):
        if self.bg_image:
            bg_label = ctk.CTkLabel(parent_frame, image=self.bg_image, text="")
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    def clear_screen(self):
        if self.current_frame:
            for child in self.current_frame.winfo_children():
                if isinstance(child, VideoPlayer): child.stop()
            self.current_frame.destroy()

    # --- 1. LOGIN ---
    def show_login_screen(self):
        self.clear_screen()
        frame = ctk.CTkFrame(self.container, fg_color="black")
        self.current_frame = frame
        frame.pack(fill="both", expand=True)
        self.set_background(frame)

        box = ctk.CTkFrame(frame, fg_color="#000000", border_width=2, border_color="#00FF41", corner_radius=10)
        box.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(box, text="PROJECT MORPHEUS", font=("Courier", 40, "bold"), text_color="#00FF41").pack(padx=50, pady=(40, 10))
        ctk.CTkLabel(box, text="SELF-DEFENSE TRAINING SYSTEM", font=("Courier", 14), text_color="#008F11").pack(pady=(0, 40))

        self.alias_entry = ctk.CTkEntry(box, placeholder_text="ENTER TRAINEE NAME", width=300, font=("Courier", 16))
        self.alias_entry.pack(pady=10)
        ctk.CTkButton(box, text="BEGIN TRAINING", font=("Courier", 16, "bold"), fg_color="#00FF41", text_color="black", 
                      command=self.login).pack(pady=40)

    def login(self):
        alias = self.alias_entry.get().strip() or "Trainee"
        profile = {"alias": alias, "xp": 0, "level": 1}
        
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE, 'r') as f:
                    data = json.load(f)
                    if data.get("alias") == alias: 
                        profile.update(data)
            except: pass
        
        with open(PROFILE_FILE, "w") as f: json.dump(profile, f)
        self.show_home_screen(profile)

    # --- 2. DASHBOARD ---
    def show_home_screen(self, profile):
        self.clear_screen()
        frame = ctk.CTkFrame(self.container, fg_color="#101010")
        self.current_frame = frame
        frame.pack(fill="both", expand=True)
        self.set_background(frame)

        header = ctk.CTkFrame(frame, fg_color="black", border_width=1, border_color="#333333")
        header.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(header, text=f"OPERATOR: {profile['alias'].upper()}", font=("Courier", 24, "bold"), text_color="white").pack(side="left", padx=20, pady=15)
        
        stats = ctk.CTkFrame(header, fg_color="transparent")
        stats.pack(side="right", padx=20)
        ctk.CTkLabel(stats, text=f"LVL {profile['level']}", font=("Courier", 20, "bold"), text_color="#00FF41").pack(side="right", padx=15)
        ctk.CTkLabel(stats, text=f"XP: {profile['xp']}", font=("Courier", 16), text_color="gray").pack(side="right")

        ctk.CTkButton(frame, text="OPEN DEFENSE SCENARIOS >>", font=("Courier", 20, "bold"), height=60,
                      fg_color="#00FF41", text_color="black", command=lambda: self.show_training_hub(profile)).place(relx=0.5, rely=0.5, anchor="center")

    # --- 3. SCENARIO HUB ---
    def show_training_hub(self, profile):
        self.clear_screen()
        frame = ctk.CTkFrame(self.container, fg_color="#101010")
        self.current_frame = frame
        frame.pack(fill="both", expand=True)
        self.set_background(frame)

        nav = ctk.CTkFrame(frame, height=50, fg_color="transparent")
        nav.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(nav, text="< BACK", width=80, fg_color="#333333", command=lambda: self.show_home_screen(profile)).pack(side="left")

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40, pady=20)

        if not os.path.exists(VIDEO_FOLDER): os.makedirs(VIDEO_FOLDER)
        files = [f for f in os.listdir(VIDEO_FOLDER) if f.lower().endswith(('.mp4', '.avi'))]
        moves = {}
        for f in files:
            name_parts = os.path.splitext(f)[0].split('_')
            base = "_".join(name_parts[:-1]).upper() if len(name_parts) > 1 else os.path.splitext(f)[0].upper()
            code = name_parts[-1] if len(name_parts) > 1 else 'c'
            if base not in moves: moves[base] = {}
            moves[base][code] = f

        for move_name, angles in moves.items():
            self.create_hub_card(scroll, move_name, angles, profile)

    def create_hub_card(self, parent, name, angles, profile):
        card = ctk.CTkFrame(parent, fg_color="#000000", border_width=1, border_color="#333333")
        card.pack(fill="x", pady=10)
        
        display_name = name.replace("DUNK", "ESCAPE DRILL").replace("PUNCH", "STRIKE DEFENSE")
        ctk.CTkLabel(card, text=display_name, font=("Courier", 22, "bold"), text_color="white").pack(side="left", padx=30, pady=20)
        
        is_ready = False
        for code, vid in angles.items():
            if os.path.exists(os.path.join(SKELETON_FOLDER, f"{os.path.splitext(vid)[0]}_coords.json")): is_ready = True

        state = "normal" if is_ready else "disabled"
        color = "#00FF41" if is_ready else "gray"
        ctk.CTkButton(card, text="TRAIN", font=("Courier", 14, "bold"), width=150, fg_color=color, text_color="black",
                      state=state, command=lambda: self.show_briefing_room(profile, name, angles)).pack(side="right", padx=30)

    # --- 4. BRIEFING ROOM ---
    def show_briefing_room(self, profile, move_name, angles):
        self.clear_screen()
        frame = ctk.CTkFrame(self.container, fg_color="#101010")
        self.current_frame = frame
        frame.pack(fill="both", expand=True)
        self.set_background(frame)

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(top, text="< ABORT", width=80, fg_color="#8b0000", command=lambda: self.show_training_hub(profile)).pack(side="left")
        ctk.CTkLabel(top, text=f"SCENARIO: {move_name}", font=("Courier", 24, "bold"), text_color="#00FF41").pack(side="left", padx=20)

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=40, pady=10)

        left_panel = ctk.CTkFrame(content, width=300, fg_color="#000000", border_width=1, border_color="#333333")
        left_panel.pack(side="left", fill="y", padx=(0, 20))
        
        angle_map = {'c': 'FRONT', 'l': 'LEFT', 'r': 'RIGHT'}
        codes = list(angles.keys())
        human_angles = [angle_map.get(k, k.upper()) for k in codes]
        self.selected_angle = ctk.StringVar(value=human_angles[0])
        
        video_frame_container = ctk.CTkFrame(content, fg_color="black", border_width=2, border_color="#00FF41")
        video_frame_container.pack(side="right", fill="both", expand=True)
        
        self.player = None
        self.start_btn = None
        self.status_lbl = None

        def switch_angle(value):
            code = next((k for k, v in angle_map.items() if v == value), value.lower())
            video_file = angles.get(code)
            video_path = os.path.join(VIDEO_FOLDER, video_file)
            json_path = os.path.join(SKELETON_FOLDER, f"{os.path.splitext(video_file)[0]}_coords.json")
            
            if self.player: 
                self.player.stop()
                self.player.destroy()
            
            if os.path.exists(video_path):
                self.player = VideoPlayer(video_frame_container, width=700, height=400, video_path=video_path)
                self.player.pack(expand=True, pady=20)
                self.player.play()
            
            if os.path.exists(json_path):
                self.status_lbl.configure(text="SYSTEM: READY", text_color="#00FF41")
                self.start_btn.configure(text="START DRILL", state="normal", fg_color="#00FF41", 
                                    command=lambda: self.run_tracker(profile, video_file, json_path))
            else:
                self.status_lbl.configure(text="SYSTEM: JSON MISSING", text_color="red")
                self.start_btn.configure(text="DATA ERROR", state="disabled", fg_color="gray")

        ctk.CTkSegmentedButton(left_panel, values=human_angles, variable=self.selected_angle, command=switch_angle).pack(pady=20, padx=20)
        self.status_lbl = ctk.CTkLabel(left_panel, text="CHECKING...", font=("Courier", 14))
        self.status_lbl.pack(pady=20)
        self.start_btn = ctk.CTkButton(left_panel, text="START DRILL", font=("Courier", 18, "bold"), height=50)
        self.start_btn.pack(side="bottom", pady=40, padx=20, fill="x")
        switch_angle(human_angles[0])

    # --- 5. ACTION: RUN TRACKER ---
    def run_tracker(self, profile, video_file, json_path):
        if self.player: self.player.stop()
        self.withdraw()
        
        if not os.path.exists(MISTAKES_FOLDER): os.makedirs(MISTAKES_FOLDER)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_log = os.path.join(MISTAKES_FOLDER, f"log_{timestamp}.json")
        
        print(f"\n[APP] Launching Tracker...")
        print(f"[APP] Target Log: {target_log}")

        try:
            # Run Live Tracker (Pass the target log path)
            subprocess.run([sys.executable, LIVE_SCRIPT, json_path, target_log], check=False)
            
            # Run AI Coach
            if os.path.exists(target_log):
                print("[APP] Log found. Running Coach...")
                subprocess.run([sys.executable, COACH_SCRIPT, target_log], check=False)
            else:
                print("[APP] Target log not found immediately. Proceeding to discovery.")

            # Update XP
            if os.path.exists(SESSION_STATS_PATH):
                with open(SESSION_STATS_PATH, 'r') as f:
                    stats = json.load(f)
                profile['xp'] += stats.get("xp_gained", 0)
                if profile['xp'] > profile['level'] * 100:
                    profile['level'] += 1
                    profile['xp'] = 0
                with open(PROFILE_FILE, "w") as pf: json.dump(profile, pf)

        except Exception as e:
            print(f"[APP] Process Error: {e}")

        self.deiconify()
        # Find newest analysis file automatically
        self.show_results_screen(profile, video_file)

    # --- 6. RESULTS (AUTO-DISCOVERY) ---
    def show_results_screen(self, profile, video_file):
        self.clear_screen()
        frame = ctk.CTkFrame(self.container, fg_color="#050505")
        self.current_frame = frame
        frame.pack(fill="both", expand=True)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(header, text="A.I. COACH FEEDBACK", font=("Courier", 30, "bold"), text_color="#00FF41").pack(side="left")
        ctk.CTkButton(header, text="FINISH SESSION", fg_color="#440000", 
                      command=lambda: self.show_home_screen(profile)).pack(side="right")

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=10)

        left_scroll = ctk.CTkScrollableFrame(content, width=400, label_text="DETECTED ERRORS", label_fg_color="#00FF41", label_text_color="black")
        left_scroll.pack(side="left", fill="both", padx=(0, 20))

        right_panel = ctk.CTkFrame(content, fg_color="black", border_width=1, border_color="#333333")
        right_panel.pack(side="right", fill="both", expand=True)
        
        video_path = os.path.join(VIDEO_FOLDER, video_file)
        review_player = VideoPlayer(right_panel, width=600, height=400, video_path=video_path)
        review_player.pack(expand=True)
        
        # --- AUTO-DISCOVERY LOGIC ---
        analysis_path = None
        if os.path.exists(MISTAKES_FOLDER):
            files = [os.path.join(MISTAKES_FOLDER, f) for f in os.listdir(MISTAKES_FOLDER) if f.endswith("_analysis.json")]
            if files:
                newest_file = max(files, key=os.path.getmtime)
                print(f"[APP] Loaded Analysis: {newest_file}")
                analysis_path = newest_file

        if analysis_path and os.path.exists(analysis_path):
            try:
                with open(analysis_path, 'r') as f:
                    mistakes = json.load(f)
                
                if not mistakes:
                    ctk.CTkLabel(left_scroll, text="PERFECT FORM.\nNO ERRORS DETECTED.", font=("Courier", 18), text_color="#00FF41").pack(pady=50)
                else:
                    for m in mistakes:
                        self.create_mistake_card(left_scroll, m, review_player)
            except Exception as e:
                ctk.CTkLabel(left_scroll, text=f"FILE ERROR: {e}", text_color="red").pack(pady=20)
        else:
             ctk.CTkLabel(left_scroll, text="NO RECENT ANALYSIS FOUND.", text_color="red", font=("Courier", 16)).pack(pady=20)

    def create_mistake_card(self, parent, mistake, player):
        card = ctk.CTkFrame(parent, fg_color="#111111", border_width=1, border_color="#333333")
        card.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text=f"{mistake['category'].upper()}", font=("Courier", 14, "bold"), text_color="white").pack(side="left")
        ctk.CTkLabel(row1, text=f"@{mistake['time']}", font=("Courier", 12), text_color="gray").pack(side="right")
        
        ctk.CTkLabel(card, text=mistake['advice'], font=("Arial", 12), text_color="#cccccc", wraplength=350, justify="left").pack(anchor="w", padx=10)
        
        target_frame = max(0, mistake['frame'] - 30)
        ctk.CTkButton(card, text="REVIEW CLIP", height=25, fg_color="#222222", hover_color="#00FF41", 
                      command=lambda: player.seek(target_frame)).pack(fill="x", padx=10, pady=10)

if __name__ == "__main__":
    app = MorpheusTerminal()
    app.mainloop()
