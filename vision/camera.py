import os
import cv2
import numpy as np
from logger import app_logger


class CameraInput:
    def __init__(self, index=0):
        self.index = index
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            error_msg = "Unable to open webcam. Make sure a camera is connected."
            app_logger.error(error_msg)
            raise RuntimeError(error_msg)
        app_logger.info(f"Camera initialized at index {index}")

    def capture_image(self, filename=None):
        filename = filename or os.path.join(os.path.dirname(__file__), "last_frame.jpg")
        success, frame = self.cap.read()
        if not success:
            error_msg = "Failed to capture camera frame."
            app_logger.error(error_msg)
            raise RuntimeError(error_msg)
        cv2.imwrite(filename, frame)
        app_logger.info(f"Image captured and saved to {filename}")
        return frame, filename

    def describe_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = int(np.mean(gray))
        color_mean = cv2.mean(frame)[:3]
        face_count = 0
        people_description = ""
        
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if os.path.exists(cascade_path):
            face_cascade = cv2.CascadeClassifier(cascade_path)
            # More sensitive parameters for better face detection
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))
            face_count = len(faces)
            if face_count > 0:
                people_description = f"{face_count} person(s) detected in view. "
        
        dominant = self._dominant_color(color_mean)
        lighting = "bright" if brightness > 150 else "dim" if brightness < 100 else "moderate"
        
        return (
            f"{people_description}The scene has {lighting} lighting (brightness {brightness}), "
            f"dominant color {dominant}. "
        )

    def _dominant_color(self, mean_color):
        blue, green, red = mean_color
        if red >= green and red >= blue:
            return "red tones"
        if green >= red and green >= blue:
            return "green tones"
        return "blue tones"

    def close(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
            app_logger.info("Camera released")
