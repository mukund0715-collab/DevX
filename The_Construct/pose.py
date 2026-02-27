import cv2
import json

# 1. Load the stored JSON data
with open('3d.json', 'r') as f:
    video_frames_data = json.load(f)

# 2. Open the original video file
video_path = "me3.mp4"
cap = cv2.VideoCapture(video_path)

# 3. Connections List
CONNECTIONS = [
    (11, 12), (12, 24), (24, 23), (23, 11), # Torso
    (11, 13), (13, 15), (12, 14), (14, 16), # Arms
    (23, 25), (25, 27), (24, 26), (26, 28)  # Legs
]

frame_count = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success or frame_count >= len(video_frames_data):
        break

    h, w, _ = frame.shape

    # --- Resize for Screen Fit ---
    screen_max_width = 640 
    if w > screen_max_width:
        scale_ratio = screen_max_width / w
        frame = cv2.resize(frame, (int(w * scale_ratio), int(h * scale_ratio)))
        h, w = frame.shape[:2]

    # 4. Get the specific landmarks for this frame from JSON
    # This assumes the JSON was recorded frame-by-frame in order
    landmarks = video_frames_data[frame_count]['landmarks']

    # 5. Draw Skeleton
    for start_idx, end_idx in CONNECTIONS:
        pt1 = (int(landmarks[start_idx]['x'] * w), int(landmarks[start_idx]['y'] * h))
        pt2 = (int(landmarks[end_idx]['x'] * w), int(landmarks[end_idx]['y'] * h))
        cv2.line(frame, pt1, pt2, (0, 255, 0), 2) # Green skeleton

    # 6. Draw Joints
    for lm in landmarks:
        cx, cy = int(lm['x'] * w), int(lm['y'] * h)
        cv2.circle(frame, (cx, cy), 3, (0, 0, 255), -1) # Red joints

    # 7. Display and move to next frame
    cv2.imshow("JSON Data Over Video", frame)
    
    frame_count += 1
    
    # Press 'q' to exit
    if cv2.waitKey(25) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()