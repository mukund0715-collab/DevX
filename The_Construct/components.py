import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import threading
import pyttsx3

# --- VIDEO PLAYER (FIXED DIMENSIONS) ---
class VideoPlayer(ctk.CTkLabel):
    def __init__(self, master, width=600, height=400, video_path=None):
        # Initialize the Label with a FIXED size. It will not shrink/grow.
        super().__init__(master, text="", width=width, height=height, fg_color="black")
        
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        # We store the FIXED target dimensions. These never change.
        self.fixed_width = width
        self.fixed_height = height
        
        # Playback Flags
        self.is_playing = False
        self.is_destroyed = False 
        self.after_id = None
        
        # Load the first frame immediately
        self.update_frame()

    def update_frame(self):
        if self.is_destroyed or not self.cap.isOpened(): return

        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop
            ret, frame = self.cap.read()

        if ret:
            # 1. Get Raw Video Dimensions
            h, w = frame.shape[:2]
            
            # 2. Calculate Scale to FIT inside the FIXED box (Maintain Aspect Ratio)
            # We compare video ratio to box ratio
            scale = min(self.fixed_width / w, self.fixed_height / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # 3. Resize the video frame
            frame_resized = cv2.resize(frame, (new_w, new_h))
            
            # 4. Create a Black Background (The "Canvas") of the FIXED size
            # This ensures the UI element stays exactly 700x400 (or whatever you set)
            canvas = Image.new("RGB", (self.fixed_width, self.fixed_height), (0, 0, 0))
            
            # 5. Paste video in the center
            paste_x = (self.fixed_width - new_w) // 2
            paste_y = (self.fixed_height - new_h) // 2
            
            # Convert OpenCV Image to PIL
            frame_pil = Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB))
            canvas.paste(frame_pil, (paste_x, paste_y))
            
            # 6. Display
            ctk_img = ctk.CTkImage(light_image=canvas, dark_image=canvas, 
                                   size=(self.fixed_width, self.fixed_height))
            self.configure(image=ctk_img)
            self.image = ctk_img 
            
        if self.is_playing and not self.is_destroyed:
            self.after_id = self.after(33, self.update_frame)

    def seek(self, frame_index):
        if not self.is_destroyed and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_index))
            self.is_playing = True
            self.update_frame()

    def play(self):
        if not self.is_playing:
            self.is_playing = True
            self.update_frame()

    def stop(self):
        self.is_playing = False
        self.is_destroyed = True
        if self.after_id: self.after_cancel(self.after_id)
        if self.cap.isOpened(): self.cap.release()

# --- VOICE COMMANDER ---
class VoiceCommander:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 160)
            voices = self.engine.getProperty('voices')
            for v in voices:
                if "Zira" in v.name or "female" in v.name.lower():
                    self.engine.setProperty('voice', v.id)
                    break
        except:
            print("Voice Engine Failed to Init")

    def speak(self, text):
        thread = threading.Thread(target=self._run_speech, args=(text,))
        thread.start()

    def _run_speech(self, text):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except: pass