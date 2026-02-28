import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import os
import json
import threading
import time
import config
import components
import game_logic

# --- HELPER: VIDEO BACKGROUND ENGINE ---
class VideoBackgroundLabel(ctk.CTkLabel):
    """
    A Label that continuously loops a video file.
    Must be placed at the very back of the visual stack.
    """
    def __init__(self, master, video_path, width, height):
        super().__init__(master, text="")
        self.video_path = video_path
        self.target_width = width
        self.target_height = height
        self.cap = cv2.VideoCapture(video_path)
        self.running = True
        self.update_video()

    def update_video(self):
        if not self.running: return
        
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop
            ret, frame = self.cap.read()

        if ret:
            # OpenCV is BGR, Pillow needs RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Resize to fill screen (expensive operation, handle with care)
            frame = cv2.resize(frame, (self.target_width, self.target_height))
            
            img = Image.fromarray(frame)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(self.target_width, self.target_height))
            
            self.configure(image=ctk_img)
            self.image = ctk_img # Keep reference
            
        # 33ms = ~30 FPS
        self.after(33, self.update_video)

    def stop(self):
        self.running = False
        if self.cap.isOpened():
            self.cap.release()

# --- HELPER: MODERN CARD ---
class ModernCard(ctk.CTkFrame):
    """A standard container with a 'Glass' look."""
    def __init__(self, parent, **kwargs):
        # Dark slate with slight transparency effect requires solid color in Tkinter
        # We simulate it with a very dark blue/grey
        super().__init__(parent, fg_color="#1e293b", corner_radius=15, border_width=1, border_color="#334155", **kwargs)

# --- 1. LOGIN SCREEN ---
class LoginScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="black") # Initial BG
        self.controller = controller
        
        # 1. Start Video Background
        # Ensure you have a 'bg_loop.mp4' in your assets, or fallback to black
        bg_video = os.path.join("assets", "background_loop.mp4") 
        if os.path.exists(bg_video):
            self.bg = VideoBackgroundLabel(self, bg_video, 1280, 850)
            self.bg.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            self.bg = None
            ctk.CTkLabel(self, text="", fg_color="#0F172A").place(x=0, y=0, relwidth=1, relheight=1)

        # 2. Login Card (Centered)
        # We use a frame inside the frame to create the "Floating" look
        self.card = ctk.CTkFrame(self, fg_color="#0F172A", border_color="#38BDF8", border_width=2, corner_radius=20, width=400, height=500)
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        self.card.pack_propagate(False) # Force size

        # Branding
        ctk.CTkLabel(self.card, text="DEFENSE\nINITIATIVE", font=("Roboto", 36, "bold"), text_color="white").pack(pady=(60, 10))
        ctk.CTkLabel(self.card, text="// TACTICAL TRAINING OS", font=("Roboto Mono", 12), text_color="#94A3B8").pack(pady=(0, 40))

        # Input
        self.alias_entry = ctk.CTkEntry(self.card, placeholder_text="OPERATOR ID", width=280, height=50, 
                                      font=("Roboto Mono", 14), justify="center", 
                                      fg_color="#1E293B", border_color="#334155", text_color="white")
        self.alias_entry.pack(pady=10)
        
        # Button
        ctk.CTkButton(self.card, text="AUTHENTICATE", font=("Roboto", 14, "bold"), height=50, width=280,
                      fg_color="#0EA5E9", hover_color="#0284C7", text_color="white", corner_radius=8,
                      command=self._on_login).pack(pady=30)

    def _on_login(self):
        alias = self.alias_entry.get().strip() or "OPERATOR"
        if self.bg: self.bg.stop() # Stop video to save resources for next screen
        self.controller.perform_login(alias)


# --- 2. DASHBOARD SCREEN ---
class DashboardScreen(ctk.CTkFrame):
    def __init__(self, parent, controller, profile):
        super().__init__(parent, fg_color="#0F172A") # Deep Slate BG
        self.controller = controller
        
        # --- Sidebar ---
        sidebar = ctk.CTkFrame(self, fg_color="#1E293B", width=250, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        
        # User Profile in Sidebar
        ctk.CTkLabel(sidebar, text="OPERATOR", font=("Roboto Mono", 10), text_color="#94A3B8").pack(anchor="w", padx=20, pady=(30,0))
        ctk.CTkLabel(sidebar, text=profile['alias'].upper(), font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", padx=20, pady=5)
        
        # Rank Badge
        rank_frame = ctk.CTkFrame(sidebar, fg_color="#0EA5E9", height=30, corner_radius=5)
        rank_frame.pack(anchor="w", padx=20, pady=(0, 20))
        ctk.CTkLabel(rank_frame, text=f"  {profile.get('rank_title', 'RECRUIT')}  ", font=("Roboto", 11, "bold"), text_color="white").pack()

        # Navigation Buttons (Sidebar)
        self._create_nav_btn(sidebar, "DASHBOARD", True)
        self._create_nav_btn(sidebar, "HISTORY", False)
        self._create_nav_btn(sidebar, "SETTINGS", False)

        # --- Main Content Area ---
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="right", fill="both", expand=True, padx=40, pady=40)

        # Header Stats
        stats_grid = ctk.CTkFrame(content, fg_color="transparent")
        stats_grid.pack(fill="x", pady=(0, 30))
        
        self._create_stat_card(stats_grid, "LEVEL", str(profile['level']), "#38BDF8", 0)
        self._create_stat_card(stats_grid, "TOTAL XP", f"{profile['xp']}", "#A78BFA", 1)
        self._create_stat_card(stats_grid, "SESSIONS", "12", "#34D399", 2)

        # Big CTA
        ctk.CTkLabel(content, text="ACTIVE MODULES", font=("Roboto", 18, "bold"), text_color="#E2E8F0").pack(anchor="w", pady=(20, 10))
        
        hero_btn = ctk.CTkButton(content, text="ENTER TRAINING SIMULATION", font=("Roboto", 16, "bold"), 
                                 height=80, fg_color="#0EA5E9", hover_color="#0284C7", corner_radius=10,
                                 image=None, # Add an icon here if you want
                                 command=lambda: controller.show_training_hub(profile))
        hero_btn.pack(fill="x")

    def _create_nav_btn(self, parent, text, active):
        fg = "#334155" if active else "transparent"
        ctk.CTkButton(parent, text=text, fg_color=fg, hover_color="#334155", 
                      anchor="w", height=45, font=("Roboto", 12, "bold"), corner_radius=0, width=250).pack()

    def _create_stat_card(self, parent, label, value, color, col_idx):
        card = ModernCard(parent)
        card.grid(row=0, column=col_idx, padx=10, sticky="ew")
        parent.grid_columnconfigure(col_idx, weight=1)
        
        ctk.CTkLabel(card, text=label, font=("Roboto Mono", 10), text_color="#94A3B8").pack(anchor="w", padx=15, pady=(15,0))
        ctk.CTkLabel(card, text=value, font=("Roboto", 28, "bold"), text_color=color).pack(anchor="w", padx=15, pady=(0, 15))


# --- 3. SCENARIO HUB ---
class ScenarioHubScreen(ctk.CTkFrame):
    def __init__(self, parent, controller, profile):
        super().__init__(parent, fg_color="#0F172A")
        self.controller = controller
        self.profile = profile

        # Header
        header = ctk.CTkFrame(self, fg_color="#1E293B", height=70, corner_radius=0)
        header.pack(fill="x")
        
        ctk.CTkButton(header, text="← BACK", width=80, fg_color="transparent", text_color="#94A3B8", 
                      command=lambda: controller.show_home_screen(profile)).pack(side="left", padx=20)
        ctk.CTkLabel(header, text="SIMULATION LIBRARY", font=("Roboto", 18, "bold")).pack(side="left", padx=10)

        # Grid Content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Grid System
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        moves = game_logic.get_available_moves()
        row = 0
        col = 0
        for move_name, angles in moves.items():
            self._create_move_card(scroll, move_name, angles, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

    def _create_move_card(self, parent, name, angles, r, c):
        is_locked, req_lvl = game_logic.is_move_locked(name, self.profile['level'])
        
        card = ModernCard(parent)
        card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
        
        # Status Dot
        status_color = "#EF4444" if is_locked else "#10B981"
        ctk.CTkLabel(card, text="●", text_color=status_color, font=("Arial", 16)).pack(anchor="ne", padx=15, pady=5)

        # Title
        display_name = name.replace("_", " ").upper()
        ctk.CTkLabel(card, text=display_name, font=("Roboto", 20, "bold"), text_color="white").pack(padx=15, pady=(0, 5), anchor="w")
        
        # Details
        sub_text = f"REQUIRED LEVEL: {req_lvl}" if is_locked else f"DATA STREAMS: {len(angles)}"
        ctk.CTkLabel(card, text=sub_text, font=("Roboto Mono", 10), text_color="gray").pack(padx=15, anchor="w")

        # Action Button
        state = "disabled" if is_locked else "normal"
        btn_text = "LOCKED" if is_locked else "INITIALIZE"
        btn_fg = "#334155" if is_locked else "#0EA5E9"
        
        ctk.CTkButton(card, text=btn_text, fg_color=btn_fg, state=state, width=200, height=40,
                      font=("Roboto", 12, "bold"),
                      command=lambda: self.controller.show_briefing_room(self.profile, name, angles)).pack(pady=20)


# --- 4. BRIEFING ROOM ---
class BriefingRoomScreen(ctk.CTkFrame):
    def __init__(self, parent, controller, profile, move_name, angles):
        super().__init__(parent, fg_color="#0F172A")
        self.controller = controller
        self.profile = profile
        self.move_name = move_name
        self.angles = angles
        self.angle_map = {'c': 'FRONT', 'l': 'LEFT', 'r': 'RIGHT'}
        
        # Layout: Split Screen
        self.grid_columnconfigure(0, weight=1) # Left: Info
        self.grid_columnconfigure(1, weight=2) # Right: Video
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL ---
        left_panel = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=0)
        left_panel.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkButton(left_panel, text="← ABORT", fg_color="transparent", text_color="#EF4444", anchor="w",
                      command=lambda: controller.show_training_hub(profile)).pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(left_panel, text=move_name.replace("_", " "), font=("Roboto", 28, "bold"), wraplength=300).pack(padx=20, anchor="w")
        ctk.CTkLabel(left_panel, text="Select Optical Feed:", font=("Roboto Mono", 12), text_color="gray").pack(padx=20, pady=(40, 10), anchor="w")

        # Angle Selector
        self.selected_angle = ctk.StringVar(value="FRONT")
        human_angles = [self.angle_map.get(k, k.upper()) for k in angles.keys()]
        ctk.CTkSegmentedButton(left_panel, values=human_angles, variable=self.selected_angle, 
                               selected_color="#0EA5E9", command=self._switch_angle).pack(padx=20, fill="x")

        # Start Button at bottom
        self.start_btn = ctk.CTkButton(left_panel, text="START TRACKING", height=60, 
                                       font=("Roboto", 16, "bold"), fg_color="#10B981", hover_color="#059669",
                                       state="disabled") # Enabled via logic
        self.start_btn.pack(side="bottom", fill="x", padx=20, pady=20)

        # --- RIGHT PANEL ---
        self.video_container = ctk.CTkFrame(self, fg_color="black")
        self.video_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.player = None
        
        # Initialize first angle
        self._switch_angle(human_angles[0])

    def _switch_angle(self, value):
        code = next((k for k, v in self.angle_map.items() if v == value), value.lower())
        video_file = self.angles.get(code)
        
        if self.player: 
            self.player.stop()
            self.player.destroy()

        video_path = os.path.join(config.VIDEO_FOLDER, video_file)
        self.player = components.VideoPlayer(self.video_container, width=800, height=500, video_path=video_path)
        self.player.pack(expand=True)
        self.player.play()
        
        # Activate Button Logic
        if game_logic.check_skeleton_data(video_file):
             json_path = os.path.join(config.SKELETON_FOLDER, f"{os.path.splitext(video_file)[0]}_coords.json")
             self.start_btn.configure(state="normal", command=lambda: self.controller.launch_tracker(self.profile, video_file, json_path, self.move_name))
        else:
             self.start_btn.configure(state="disabled", text="DATA MISSING")

    def cleanup(self):
        if self.player: self.player.stop()


# --- 5. RESULTS SCREEN (VOICE ENABLED) ---
class ResultsScreen(ctk.CTkFrame):
    def __init__(self, parent, controller, profile, video_file, session_log):
        super().__init__(parent, fg_color="#0F172A")
        self.controller = controller
        self.voice = components.VoiceCommander()
        self.mistakes = self._load_mistakes(session_log)
        self.debrief_active = False
        
        # Top Header
        header = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=0, height=60)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="MISSION DEBRIEF", font=("Roboto", 20, "bold"), text_color="white").pack(side="left", padx=20)
        
        ctk.CTkButton(header, text="CLOSE", width=80, fg_color="#334155", 
                      command=lambda: controller.show_home_screen(profile)).pack(side="right", padx=20)

        # Content Split
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 1. Left: Data Stream
        self.log_panel = ctk.CTkScrollableFrame(content, width=350, fg_color="#1E293B", label_text="ANOMALY LOG", label_font=("Roboto Mono", 12))
        self.log_panel.pack(side="left", fill="y", padx=(0, 20))
        
        # 2. Right: Visuals
        right_panel = ctk.CTkFrame(content, fg_color="black")
        right_panel.pack(side="right", fill="both", expand=True)
        
        # Video
        video_path = os.path.join(config.VIDEO_FOLDER, video_file)
        self.review_player = components.VideoPlayer(right_panel, width=640, height=360, video_path=video_path)
        self.review_player.pack(pady=20)
        
        # Coach Controls
        controls = ctk.CTkFrame(right_panel, fg_color="#0F172A")
        controls.pack(fill="x", padx=20)
        
        self.status_lbl = ctk.CTkLabel(controls, text="AI COACH READY", font=("Roboto Mono", 14), text_color="#0EA5E9")
        self.status_lbl.pack(pady=10)
        
        self.btn_debrief = ctk.CTkButton(controls, text="▶ START AUDIO DEBRIEF", height=50, 
                                         font=("Roboto", 14, "bold"), fg_color="#0EA5E9", hover_color="#0284C7",
                                         command=self.start_voice_debrief)
        self.btn_debrief.pack(pady=10)

        # Populate List
        self._populate_list()

    def _load_mistakes(self, log_path):
        try:
            with open(log_path, 'r') as f:
                data = json.load(f)
            return data.get("mistakes", [])
        except: return []

    def _populate_list(self):
        if not self.mistakes:
            ctk.CTkLabel(self.log_panel, text="PERFECT RUN", text_color="#10B981").pack(pady=20)
            return

        for i, m in enumerate(self.mistakes):
            card = ctk.CTkFrame(self.log_panel, fg_color="#0F172A", border_width=1, border_color="#334155")
            card.pack(fill="x", pady=5)
            m['ui_card'] = card # Store ref
            
            ctk.CTkLabel(card, text=f"{m['timestamp']}s | {m['error']}", font=("Roboto Mono", 11, "bold"), text_color="#F87171").pack(anchor="w", padx=10, pady=5)
            ctk.CTkLabel(card, text=self._get_advice(m['error']), font=("Arial", 11), text_color="#94A3B8", wraplength=280).pack(anchor="w", padx=10, pady=(0, 5))

    def _get_advice(self, error):
        # Quick map for advice text
        if "elbow" in error.lower(): return "Raise elbow to shield level."
        if "hands" in error.lower(): return "Keep guard up."
        return "Check form."

    def start_voice_debrief(self):
        if self.debrief_active: return
        self.debrief_active = True
        self.btn_debrief.configure(state="disabled", text="COACHING IN PROGRESS...")
        threading.Thread(target=self._run_coach_logic).start()

    def _run_coach_logic(self):
        self.voice.speak(f"Analysis complete. Found {len(self.mistakes)} issues.")
        time.sleep(1)

        for m in self.mistakes:
            if not self.debrief_active: break
            
            # Highlight UI
            m['ui_card'].configure(border_color="#0EA5E9", border_width=2)
            self.status_lbl.configure(text=f"REVIEWING: {m['error'].upper()}")
            
            # Seek Video
            target = max(0, float(m['timestamp']) * 30 - 30) # Approx frame conversion
            self.review_player.seek(int(target))
            
            # Speak
            advice = self._get_advice(m['error'])
            self.voice.speak(f"At {m['timestamp']} seconds. {advice}")
            
            time.sleep(4)
            m['ui_card'].configure(border_color="#334155", border_width=1)

        self.status_lbl.configure(text="DEBRIEF COMPLETE")
        self.btn_debrief.configure(state="normal", text="REPLAY DEBRIEF")
        self.debrief_active = False

    def cleanup(self):
        self.debrief_active = False
        if self.review_player: self.review_player.stop()
        
# --- UPDATE: DASHBOARD SCREEN ---
class DashboardScreen(ctk.CTkFrame):
    def __init__(self, parent, controller, profile):
        super().__init__(parent, fg_color="#0F172A")
        self.controller = controller
        self.profile = profile # Save profile for navigation
        
        # --- Sidebar ---
        sidebar = ctk.CTkFrame(self, fg_color="#1E293B", width=250, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        
        # Profile Header
        ctk.CTkLabel(sidebar, text="OPERATOR", font=("Roboto Mono", 10), text_color="#94A3B8").pack(anchor="w", padx=20, pady=(30,0))
        ctk.CTkLabel(sidebar, text=profile['alias'].upper(), font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", padx=20, pady=5)
        
        rank_frame = ctk.CTkFrame(sidebar, fg_color="#0EA5E9", height=30, corner_radius=5)
        rank_frame.pack(anchor="w", padx=20, pady=(0, 20))
        ctk.CTkLabel(rank_frame, text=f"  {profile.get('rank_title', 'RECRUIT')}  ", font=("Roboto", 11, "bold"), text_color="white").pack()

        # --- NAVIGATION (NOW WORKING) ---
        # We pass the command to switch screens
        self._create_nav_btn(sidebar, "DASHBOARD", True, None) 
        self._create_nav_btn(sidebar, "HISTORY LOGS", False, lambda: controller.show_history_screen(profile))
        self._create_nav_btn(sidebar, "SYSTEM SETTINGS", False, lambda: controller.show_settings_screen(profile))

        # --- Main Content ---
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="right", fill="both", expand=True, padx=40, pady=40)

        # ... (Rest of Dashboard stats code remains the same) ...
        # (Just ensure you copy the Hero Button code from previous response)
        
        ctk.CTkLabel(content, text="ACTIVE MODULES", font=("Roboto", 18, "bold"), text_color="#E2E8F0").pack(anchor="w", pady=(20, 10))
        ctk.CTkButton(content, text="ENTER TRAINING SIMULATION", font=("Roboto", 16, "bold"), 
                        height=80, fg_color="#0EA5E9", hover_color="#0284C7", corner_radius=10,
                        command=lambda: controller.show_training_hub(profile)).pack(fill="x")

    def _create_nav_btn(self, parent, text, active, cmd):
        """Creates a sidebar button with a command."""
        fg = "#334155" if active else "transparent"
        text_color = "white" if active else "#94A3B8"
        
        btn = ctk.CTkButton(parent, text=text, fg_color=fg, hover_color="#334155", text_color=text_color,
                            anchor="w", height=45, font=("Roboto", 12, "bold"), corner_radius=0, width=250,
                            command=cmd) # Apply the command here
        btn.pack()


# --- NEW: HISTORY SCREEN ---
class HistoryScreen(ctk.CTkFrame):
    def __init__(self, parent, controller, profile):
        super().__init__(parent, fg_color="#0F172A")
        
        # Header
        header = ctk.CTkFrame(self, fg_color="#1E293B", height=70, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkButton(header, text="← DASHBOARD", width=100, fg_color="transparent", text_color="#94A3B8", 
                      command=lambda: controller.show_home_screen(profile)).pack(side="left", padx=20)
        ctk.CTkLabel(header, text="MISSION ARCHIVES", font=("Roboto", 18, "bold"), text_color="white").pack(side="left", padx=10)

        # Scrollable List
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40, pady=20)

        # Load logs from 'mistakes' folder
        import glob
        log_files = sorted(glob.glob(os.path.join(config.MISTAKES_FOLDER, "log_*.json")), reverse=True)

        if not log_files:
            ctk.CTkLabel(scroll, text="NO MISSION DATA FOUND", font=("Roboto Mono", 14), text_color="gray").pack(pady=50)
        else:
            for log in log_files:
                self._create_log_entry(scroll, log)

    def _create_log_entry(self, parent, log_path):
        try:
            with open(log_path, 'r') as f:
                data = json.load(f)
            
            # Extract data safely
            date_str = os.path.basename(log_path).replace("log_", "").replace(".json", "")
            # Format: 20231020_120000 -> 2023-10-20 12:00
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[9:11]}:{date_str[11:13]}"
            
            mistake_count = len(data.get("mistakes", []))
            grade = "S" if mistake_count == 0 else "A" if mistake_count < 3 else "B" if mistake_count < 6 else "F"
            grade_color = "#10B981" if grade in ["S", "A"] else "#F59E0B" if grade == "B" else "#EF4444"

            # UI Card
            card = ctk.CTkFrame(parent, fg_color="#1E293B", corner_radius=10)
            card.pack(fill="x", pady=5)

            # Left: Date & ID
            ctk.CTkLabel(card, text=formatted_date, font=("Roboto Mono", 12), text_color="gray").pack(side="left", padx=15)
            
            # Right: Grade
            grade_lbl = ctk.CTkLabel(card, text=f"GRADE: {grade}", font=("Roboto", 16, "bold"), text_color=grade_color)
            grade_lbl.pack(side="right", padx=20, pady=15)
            
            # Middle: Summary
            ctk.CTkLabel(card, text=f"{mistake_count} ANOMALIES DETECTED", font=("Roboto", 12, "bold"), text_color="white").pack(side="left", padx=20)

        except Exception as e:
            print(f"Error loading log {log_path}: {e}")


# --- NEW: SETTINGS SCREEN ---
class SettingsScreen(ctk.CTkFrame):
    def __init__(self, parent, controller, profile):
        super().__init__(parent, fg_color="#0F172A")
        
        # Header
        header = ctk.CTkFrame(self, fg_color="#1E293B", height=70, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkButton(header, text="← DASHBOARD", width=100, fg_color="transparent", text_color="#94A3B8", 
                      command=lambda: controller.show_home_screen(profile)).pack(side="left", padx=20)
        ctk.CTkLabel(header, text="SYSTEM CONFIGURATION", font=("Roboto", 18, "bold"), text_color="white").pack(side="left", padx=10)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=40, pady=40)

        # Settings Groups
        self._create_section(content, "AUDIO & FEEDBACK")
        self._create_toggle(content, "Enable AI Coach Voice", True)
        self._create_toggle(content, "Tactical Sound Effects", True)
        
        self._create_section(content, "HARDWARE")
        self._create_dropdown(content, "Camera Input Source", ["Webcam 1 (Default)", "Webcam 2 (External)", "IP Camera Stream"])
        self._create_toggle(content, "Low Latency Mode (Beta)", False)

        self._create_section(content, "ACCOUNT")
        ctk.CTkButton(content, text="RESET ALL PROGRESS", fg_color="#7F1D1D", hover_color="#991B1B", 
                      text_color="#FECACA", width=200, anchor="w", command=self._reset_logic).pack(anchor="w", pady=10)
        
        ctk.CTkLabel(content, text=f"FIRMWARE VERSION: 2.4.1 // USER: {profile['alias']}", font=("Roboto Mono", 10), text_color="#475569").pack(side="bottom", anchor="w")

    def _create_section(self, parent, title):
        ctk.CTkLabel(parent, text=title, font=("Roboto", 14, "bold"), text_color="#0EA5E9").pack(anchor="w", pady=(20, 10))
        ctk.CTkFrame(parent, height=2, fg_color="#334155").pack(fill="x", pady=(0, 10))

    def _create_toggle(self, parent, text, default_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        
        switch = ctk.CTkSwitch(frame, text=text, font=("Roboto", 12), progress_color="#0EA5E9", fg_color="#334155")
        if default_val: switch.select()
        switch.pack(side="left")

    def _create_dropdown(self, parent, text, values):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(frame, text=text, font=("Roboto", 12), width=150, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(frame, values=values, fg_color="#1E293B", button_color="#334155", text_color="white").pack(side="left", padx=10)

    def _reset_logic(self):
        # Placeholder for reset logic
        print("System Reset Initiated")