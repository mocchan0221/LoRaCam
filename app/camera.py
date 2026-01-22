import time
from picamera2 import Picamera2

class Camera:
    def __init__(self, width=1280, height=720, focus_val=0.0):
        self.width = width
        self.height = height
        self.focus_val = focus_val
        self.picam2 = None
        self._initialize()

    def _initialize(self):
        self.picam2 = Picamera2()
        config = self.picam2.create_video_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"}
        )
        self.picam2.configure(config)
        self.picam2.start()
        
        # フォーカス固定設定
        self.picam2.set_controls({
            "AfMode": 0,
            "LensPosition": self.focus_val
        })
        print(f"Camera initialized with Manual Focus: {self.focus_val}")

    def capture(self):
        """画像を撮影してnumpy配列(BGR)で返す"""
        return self.picam2.capture_array()

    def stop(self):
        if self.picam2:
            self.picam2.stop()