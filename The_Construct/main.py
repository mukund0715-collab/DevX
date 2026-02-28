import customtkinter as ctk
from interface import MorpheusTerminal
import os

# --- CRITICAL FIX FOR FFMPEG CRASH ---
# Forces OpenCV/FFmpeg to use a single thread, preventing the async_lock race condition.
os.environ["OPENCV_FFMPEG_THREADS"] = "1"
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0" # Optional: Helps on Windows

# ... rest of your code ...

# --- ENTRY POINT ---
if __name__ == "__main__":
    # Initialize the app theme settings
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    
    # Launch the main terminal
    app = MorpheusTerminal()
    app.mainloop()