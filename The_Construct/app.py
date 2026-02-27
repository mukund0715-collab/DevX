import customtkinter as ctk
import subprocess
import json
import os
import cv2

# --- THEME SETUP ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class MorpheusTerminal(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Project Morpheus: The Construct")
        self.geometry("900x600")
        
        # Data paths
        self.alias_file = "operator_profile.json"
        self.mistake_log = "stuck_coordinates_log.json"
        
        # Start at Login Screen
        self.current_frame = None
        self.show_login_screen()

    def show_frame(self, frame_class):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame_class(self)
        self.current_frame.pack(fill="both", expand=True)

    # ==========================================
    # SCREEN 1: THE LOGIN (Privacy First)
    # ==========================================
    def show_login_screen(self):
        frame = ctk.CTkFrame(self, fg_color="black")
        self.current_frame = frame
        frame.pack(fill="both", expand=True)

        title = ctk.CTkLabel(frame, text="PROJECT MORPHEUS", font=("Courier", 40, "bold"), text_color="#00FF41")
        title.pack(pady=(150, 20))

        sub = ctk.CTkLabel(frame, text="Secure Offline Biometric Terminal. No Cloud Connection Detected.", font=("Courier", 12), text_color="gray")
        sub.pack(pady=(0, 50))

        self.alias_entry = ctk.CTkEntry(frame, placeholder_text="Enter Operator Alias", width=300, font=("Courier", 16))
        self.alias_entry.pack(pady=10)

        btn = ctk.CTkButton(frame, text="INITIALIZE", font=("Courier", 16, "bold"), fg_color="#00FF41", text_color="black", hover_color="#00cc33", command=self.login)
        btn.pack(pady=20)

    def login(self):
        alias = self.alias_entry.get().strip() or "Neo"
        # Save local profile (Proves offline privacy capability)
        with open(self.alias_file, "w") as f:
            json.dump({"alias": alias, "sessions_completed": 0}, f)
        self.show_home_screen(alias)

    # ==========================================
    # SCREEN 2: THE DASHBOARD (Training Select)
    # ==========================================
    def show_home_screen(self, alias):
        frame = ctk.CTkFrame(self)
        self.current_frame.destroy()
        self.current_frame = frame
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkLabel(frame, text=f"Welcome, Operator {alias.upper()}", font=("Courier", 24, "bold"), text_color="#00FF41")
        header.pack(anchor="w", pady=20, padx=20)

        # Module Briefing Area
        briefing = ctk.CTkFrame(frame, fg_color="#1a1a1a")
        briefing.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(briefing, text="MODULE N0: PALM STRIKE", font=("Courier", 18, "bold")).pack(anchor="w", padx=20, pady=10)
        ctk.CTkLabel(briefing, text="Target: High-velocity defensive strike focusing on elbow extension.\nStatus: Ready.", justify="left").pack(anchor="w", padx=20, pady=(0, 20))

        # Action Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        tape_btn = ctk.CTkButton(btn_frame, text="[1] VIEW MASTER TAPE", font=("Courier", 14), command=self.play_master_tape)
        tape_btn.pack(side="left", padx=10)

        train_btn = ctk.CTkButton(btn_frame, text="[2] ENTER THE CONSTRUCT", font=("Courier", 16, "bold"), fg_color="#8b0000", hover_color="#ff0000", command=self.run_tracker)
        train_btn.pack(side="right", padx=10)

    # ==========================================
    # ACTION TRIGGERS (The Subprocess Magic)
    # ==========================================
    def play_master_tape(self):
        """Plays the video safely using OpenCV without crashing the UI"""
        cap = cv2.VideoCapture("me3.mp4") # Your reference video
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            cv2.putText(frame, "MASTER TAPE - Press 'Q' to close", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Module N0: Master", frame)
            if cv2.waitKey(30) & 0xFF == ord('q'): break
        cap.release()
        cv2.destroyAllWindows()

    def run_tracker(self):
        """Runs your existing live4.py script, waits for it to finish, then loads results"""
        # 1. Delete old log to ensure fresh results
        if os.path.exists(self.mistake_log):
            os.remove(self.mistake_log)
            
        # 2. Hide UI to simulate entering "The Matrix"
        self.withdraw() 
        
        # 3. RUN YOUR SCRIPT EXACTLY AS IT IS
        print("[SYSTEM] Booting live4.py...")
        subprocess.run(["python", "live4.py"])
        
        # 4. Bring UI back and show results
        self.deiconify() 
        self.show_results_screen()

    # ==========================================
    # SCREEN 3: AFTER-ACTION REPORT (AI Coach)
    # ==========================================
    def show_results_screen(self):
        frame = ctk.CTkFrame(self)
        self.current_frame.destroy()
        self.current_frame = frame
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="SYSTEM ANALYSIS COMPLETE", font=("Courier", 24, "bold"), text_color="#00FF41").pack(pady=20)

        # Output Box
        textbox = ctk.CTkTextbox(frame, width=800, height=350, font=("Courier", 14), fg_color="#1a1a1a", text_color="white")
        textbox.pack(pady=10)

        # Read the file live4.py just created!
        if os.path.exists(self.mistake_log):
            with open(self.mistake_log, 'r') as f:
                mistakes = json.load(f)
            
            textbox.insert("end", f"Detected {len(mistakes)} critical form deviations.\n\n")
            for m in mistakes:
                # You can format this to look exactly like your ai_coach.py output
                phase = m.get('action_phase', 'moving')
                textbox.insert("end", f"[!] Frame {m['frame_index']} | Score: {m['score_at_fail']}%\n")
                textbox.insert("end", f"    Phase: {phase}\n")
                textbox.insert("end", f"    Error: Joint {m['failed_joint_id']} misaligned.\n\n")
        else:
            textbox.insert("end", "PERFECT EXECUTION. No deviations detected.\nSystem access granted.")

        # Return Button
        ctk.CTkButton(frame, text="RETURN TO MENU", font=("Courier", 14), command=lambda: self.show_home_screen("Operator")).pack(pady=20)

if __name__ == "__main__":
    app = MorpheusTerminal()
    app.mainloop()