import customtkinter as ctk
from PIL import Image
import os
from datetime import datetime

import config
import game_logic
import screens 

class MorpheusTerminal(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- UI Configuration ---
        self.title("DEFENSE INITIATIVE // Training Portal")
        self.geometry("1280x850")
        
        # Set modern theme defaults
        ctk.set_appearance_mode("Dark") 
        ctk.set_default_color_theme("blue") # Professional blue vs "Matrix" green
        
        # --- Asset Management ---
        self.bg_image = None
        self._load_resources()

        # --- Main Layout Container ---
        # Using a unified background color for a sleek, cohesive look
        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="#0F172A") # Deep Slate Blue/Grey
        self.container.pack(fill="both", expand=True)
        
        self.current_frame = None
        
        # Initialize
        self.show_login_screen()

    def _load_resources(self):
        """Centralized resource loading with error handling."""
        try:
            if os.path.exists(config.BACKGROUND_IMAGE):
                img = Image.open(config.BACKGROUND_IMAGE)
                # Using high-quality resampling for a professional look
                self.bg_image = ctk.CTkImage(
                    light_image=img, 
                    dark_image=img, 
                    size=(1920, 1080)
                )
        except Exception as e:
            print(f"[UI] Warning: Could not load background: {e}")

    def set_background(self):
        """Applies a subtle overlay to the background to ensure readability."""
        if self.bg_image and self.current_frame:
            bg_label = ctk.CTkLabel(self.current_frame, image=self.bg_image, text="")
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            
            # Add a semi-transparent 'Scrim' or overlay to make it look modern
            # This prevents the UI from looking cluttered if the BG is busy
            overlay = ctk.CTkFrame(self.current_frame, fg_color=("rgba(15, 23, 42, 0.8)"), corner_radius=0)
            overlay.place(x=0, y=0, relwidth=1, relheight=1)
            
            bg_label.lower()
            overlay.lower()

    def switch_frame(self, frame_class, **kwargs):
        """Enhanced frame switcher with cleanup and modern transitions."""
        if self.current_frame:
            if hasattr(self.current_frame, 'cleanup'):
                self.current_frame.cleanup()
            self.current_frame.destroy()

        # Initialize with standard padding for a 'contained' dashboard feel
        self.current_frame = frame_class(parent=self.container, controller=self, **kwargs)
        self.current_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Apply the refined background
        self.set_background()

    # --- ROUTING / NAVIGATION ---

    def show_login_screen(self):
        """Professional auth entrance."""
        self.switch_frame(screens.LoginScreen)

    def perform_login(self, alias):
        profile = game_logic.load_or_create_profile(alias)
        self.show_home_screen(profile)

    def show_home_screen(self, profile):
        """Main Dashboard: Overview of progress and stats."""
        self.switch_frame(screens.DashboardScreen, profile=profile)

    def show_training_hub(self, profile):
        """The Library: Selection of available training modules."""
        self.switch_frame(screens.ScenarioHubScreen, profile=profile)

    def show_briefing_room(self, profile, move_name, angles):
        """Pre-Session: Technical breakdown of the movement."""
        self.switch_frame(screens.BriefingRoomScreen, profile=profile, move_name=move_name, angles=angles)

    def launch_tracker(self, profile, video_file, json_path, move_name):
        """Seamless transition between the UI and the CV tracking engine."""
        if hasattr(self.current_frame, 'cleanup'): 
            self.current_frame.cleanup()
        
        self.withdraw() 
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_log = os.path.join(config.MISTAKES_FOLDER, f"log_{timestamp}.json")
        
        try:
            # Training logic execution
            game_logic.run_training_session(json_path, target_log)
            game_logic.update_xp_from_session(profile, move_name)
        except Exception as e:
            print(f"[SYSTEM ERROR] Session Interrupted: {e}")

        self.deiconify() 
        self.show_results_screen(profile, video_file)
        
    def show_results_screen(self, profile, video_file):
        """Post-Session: Data visualization and feedback."""
        self.switch_frame(screens.ResultsScreen, profile=profile, video_file=video_file)
    
    # In interface.py inside class MorpheusTerminal:

    def show_history_screen(self, profile):
        """Routes to the Mission Archive."""
        self.switch_frame(screens.HistoryScreen, profile=profile)

    def show_settings_screen(self, profile):
        """Routes to System Configuration."""
        self.switch_frame(screens.SettingsScreen, profile=profile)