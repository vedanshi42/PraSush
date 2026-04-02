from __future__ import annotations

from pathlib import Path

import cv2

from config import SCENE_IMAGE_PATH


class CameraInput:
    def __init__(self, index: int = 0) -> None:
        self.index = index
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    def capture_image(self, filename: Path | None = None) -> Path:
        output_path = filename or SCENE_IMAGE_PATH
        capture = cv2.VideoCapture(self.index)
        if not capture.isOpened():
            raise RuntimeError("Unable to open webcam. Make sure a camera is connected.")

        try:
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            for _ in range(5):
                capture.read()
            success, frame = capture.read()
            if not success:
                raise RuntimeError("Failed to capture camera frame.")
            if not cv2.imwrite(str(output_path), frame):
                raise RuntimeError(f"Failed to write captured frame to {output_path}.")
            return output_path
        finally:
            capture.release()

    def analyze_scene(self, image_path: Path) -> str:
        frame = cv2.imread(str(image_path))
        if frame is None:
            return "Scene analysis unavailable."

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        height, width = frame.shape[:2]
        brightness = int(gray.mean())
        face_count = len(faces)

        details = [
            f"Image size: {width}x{height}.",
            f"Brightness level: {brightness}.",
            f"Detected face count: {face_count}.",
        ]
        if face_count:
            details.append("A person is likely visible in front of the camera.")
        else:
            details.append("No clear face was detected, but the image may still contain a person or objects.")
        return " ".join(details)

    def close(self) -> None:
        return None
