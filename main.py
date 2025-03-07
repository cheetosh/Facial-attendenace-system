import cv2
import face_recognition_models  # Assuming you import this first as mentioned in point 1
import face_recognition
import os
import sqlite3
import pandas as pd
from datetime import datetime

# Load employee images and encode faces
def load_known_faces(folder_path):
    known_face_encodings = []
    known_face_names = []
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            # Load image and extract employee ID from the filename
            employee_id = os.path.splitext(filename)[0]  # Remove file extension
            
            # Load the employee image
            image_path = os.path.join(folder_path, filename)
            image = face_recognition.load_image_file(image_path)
            
            # Encode the face
            face_encoding = face_recognition.face_encodings(image)[0]
            
            # Append to the known faces list
            known_face_encodings.append(face_encoding)
            known_face_names.append(employee_id)
    
    return known_face_encodings, known_face_names

# Log attendance in SQLite database
def log_attendance_db(conn, c, employee_id):
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    date_today = datetime.now().strftime('%Y-%m-%d')
    c.execute('INSERT INTO attendance (employee_id, date, time) VALUES (?, ?, ?)', 
              (employee_id, date_today, time_now))
    conn.commit()

# Log attendance in Excel
def log_attendance_excel(employee_id):
    time_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    date_today = datetime.now().strftime('%Y-%m-%d')
    
    file_name = f'attendance_{date_today}.xlsx'
    try:
        df = pd.read_excel(file_name)
    except FileNotFoundError:
        df = pd.DataFrame(columns=["Employee ID", "Date", "Time"])
    
    new_record = {"Employee ID": employee_id, "Date": date_today, "Time": time_now}
    df = df.append(new_record, ignore_index=True)
    df.to_excel(file_name, index=False)

# Detect faces and mark attendance
def detect_and_mark_attendance(frame, known_face_encodings, known_face_names, conn, c):
    rgb_frame = frame[:, :, ::-1]  # Convert BGR to RGB
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        employee_id = "Unknown"
        
        # Use the first matched encoding for attendance
        if True in matches:
            match_index = matches.index(True)
            employee_id = known_face_names[match_index]
        
        # Log attendance
        log_attendance_db(conn, c, employee_id)
        log_attendance_excel(employee_id)
        
        # Draw a rectangle around the face and label the employee
        cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)
        cv2.putText(frame, employee_id, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
    
    return frame

# Process CCTV feed and mark attendance
def process_cctv_feed(camera_url, known_face_encodings, known_face_names):
    cap = cv2.VideoCapture(camera_url)
    
    if not cap.isOpened():
        print(f"Error opening video stream from {camera_url}")
        return
    
    conn, c = connect_to_db()

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Failed to grab frame from {camera_url}")
            break
        
        # Detect and recognize faces, mark attendance
        processed_frame = detect_and_mark_attendance(frame, known_face_encodings, known_face_names, conn, c)
        
        # Display the feed with face detection and recognition
        cv2.imshow(f'CCTV Camera: {camera_url}', processed_frame)
        
        # Break loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    conn.close()

# Connect to SQLite database
def connect_to_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (employee_id TEXT, date TEXT, time TEXT)''')
    conn.commit()
    return conn, c

# Load known faces from folder
folder_path = r'C:\Users\shubh\OneDrive\Desktop\attendace ssn\employees_photo\employees photo'  # Folder where employee images are stored
known_face_encodings, known_face_names = load_known_faces(folder_path)

# Define CCTV camera URLs
cctv_cameras = [
    "rtsp://username:password@camera_ip_1:554/stream",
    "rtsp://username:password@camera_ip_2:554/stream",
]

# Process each camera feed
for camera_url in cctv_cameras:
    process_cctv_feed(camera_url, known_face_encodings, known_face_names)
