# DevX
An offline, privacy-first AI self-defense training terminal for women. Features interactive biometric tutorials, real-time posture correction, emergency quick-reference tools, and local certification—all without compromising user video data to the cloud.

🟢 Offline AI Self-Defense Trainer

A Zero-Setup, Privacy-First AI Self-Defense Trainer for Women.

📖 Project Overview

Offline AI Self-Defense Trainer is a zero-setup, biometric coaching terminal designed to teach women self-defense without compromising their privacy. By acting as a "mathematical mirror," the system uses local computer vision to compare a user's physical movements against a professional martial artist's perfect form in real-time.

It provides instant, sub-millisecond voice feedback on physical form—all completely offline, without ever saving or uploading a single frame of video to the cloud. Simply download, double-click, and train.

🚨 The Problem: Privacy vs. Protection

Traditional AI fitness or self-defense applications require users to upload videos of themselves to cloud servers for processing. For a women's safety application, this is a massive privacy risk. Women should not have to compromise their digital privacy or record themselves inside their homes to learn basic self-defense.

Furthermore, relying on cloud-based Large Language Models (LLMs) for computer vision feedback introduces severe latency, ruining the real-time physical training experience.

💡 The Solution: A Standalone Biometric Executable

This application is a 100% local, zero-cloud self-defense training terminal packaged as a standalone Windows executable. Users do not need to install Python, configure environments, or download libraries. They simply double-click and train.

Instead of recording the user, the application acts as a mathematical mirror. It extracts skeletal data locally in real-time, calculates the vector differences using weighted joint heuristics, and immediately discards the video frame. No video is ever saved. No data ever leaves the local machine.

✨ Core Architecture & Innovation

1. The Deployment Engine (Zero-Install Architecture)

The application uses a custom executable-intercept architecture (sys.argv routing). Instead of running multiple separate Python scripts, the main .exe intercepts system arguments to spawn secure, isolated sub-processes for the computer vision engine and the text-to-speech coach.

All AI model weights (pose_landmarker_heavy.task) and semantic data (n0_complete_data.json) are bundled directly into the application's runtime directory using sys._MEIPASS relative routing.

2. Offline Semantic Action Tagging

To eliminate latency, the "Master Tapes" (reference videos) are processed entirely offline before being bundled into the software.

Raw math is automatically converted into grouped Semantic Action Phases (e.g., Frames 15-26: "extending the right hand"). This gives the AI Coach immediate context without requiring heavy live computation.

3. The Live Training Environment (live4.py)

When the user enters the trainer, the system evaluates their form in real-time.

Scale & Position Invariance: The engine translates all coordinates to be relative to the user's hip-center. This ensures a 5'2" user can be accurately scored against a 6'2" master, regardless of where they stand in the room.

Custom Joint Weighting: Not all joints matter equally in self-defense. Our evaluation engine uses a custom distribution matrix (e.g., Ankles/Feet: 0.25, Knees: 0.20, Shoulders: 0.10), prioritizing lower-body stability over head position.

4. The Deterministic AI Sensei (ai_coach1.py)

Instead of an LLM, we built a deterministic, math-based AI Coach.

Sub-Millisecond Feedback: It reads local logs and uses relative X/Y differentials to generate exact physical corrections.

Text-to-Speech (TTS): Integrated with pyttsx3, the coach audibly speaks the corrections, spawning in a dedicated hacker-style terminal window.

Instant Tape Review: The coach allows the user to press a button and instantly launch an OpenCV window showing the exact frame of the master tape where they made their mistake.

🛠️ Tech Stack

Core Engine: Python 3.10+

Computer Vision: Google MediaPipe Vision Tasks & OpenCV (cv2)

Kinematics: NumPy (Cosine Similarity, Euclidean geometry)

User Interface: CustomTkinter

Accessibility: PyTTSx3 (Offline Text-to-Speech)

Deployment: PyInstaller / Auto-py-to-exe

🚀 How to Run (For End Users & Judges)

You do not need Python installed to run this application!

Download the provided application folder.

Double-click the standalone executable (app.exe).

Enter an "Operator Alias" (Notice: No cloud password required, proving zero cloud auth).

Select Module N0: Palm Strike.

Click "View Master Tape" to see the reference movement.

Click "Start Training" to activate the webcam tracker. Perform the move.

When the session ends, click Launch AI Coach for audio feedback and exact geometric corrections!

💻 Instructions for Developers (Building from Source)

1. Clone & Install

git clone [https://github.com/your-username/ai-self-defense-trainer.git](https://github.com/your-username/ai-self-defense-trainer.git)
cd ai-self-defense-trainer
pip install opencv-python mediapipe numpy customtkinter pyttsx3 Pillow auto-py-to-exe



2. Ensure Assets are Present
Make sure pose_landmarker_heavy.task, me3.mp4, and n0_complete_data.json are in the root directory.

3. Test Run

python app.py



4. Build the Executable

Run auto-py-to-exe in your terminal.

Script Location: app.py

Onefile: Select One Directory (Crucial for OpenCV/MediaPipe performance).

Console Window: Select Window Based (hide the console).

Additional Files: Add pose_landmarker_heavy.task, n0_complete_data.json, and me3.mp4.

Click Convert .py to .exe.

🔮 Future Scope

Hardware Acceleration: Compiling the math engine with PyTorch/CUDA for faster processing on low-end hardware.

Expanded Curriculum: Adding a library of 50+ self defense techniques via our automated offline JSON pipeline.

Dynamic Time Warping (DTW): Expanding the frame matching algorithm to allow users to perform the moves at slightly different speeds than the master tape without losing their sync score.
