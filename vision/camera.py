import os
import cv2
import numpy as np


class CameraInput:
    def __init__(self, index=0):
        self.index = index
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            raise RuntimeError("Unable to open webcam. Make sure a camera is connected.")

    def capture_image(self, filename=None):
        filename = filename or os.path.join(os.path.dirname(__file__), "last_frame.jpg")
        success, frame = self.cap.read()
        if not success:
            raise RuntimeError("Failed to capture camera frame.")
        cv2.imwrite(filename, frame)
        return frame, filename

    def describe_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = int(np.mean(gray))
        color_mean = cv2.mean(frame)[:3]
        face_count = 0
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if os.path.exists(cascade_path):
            face_cascade = cv2.CascadeClassifier(cascade_path)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
            face_count = len(faces)
        dominant = self._dominant_color(color_mean)
        return (
            f"The captured image has average brightness {brightness}, dominant color {dominant}, "
            f"and detected {face_count} face(s) in the scene."
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
