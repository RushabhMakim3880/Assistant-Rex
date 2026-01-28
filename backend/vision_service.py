import asyncio
import base64
import mss
import PIL.Image
import io

class VisionService:
    """
    Handles screen capture and visual context management.
    Extracted from rex.py for modularity.
    """
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.video_mode = "screen" # screen | camera
        self._latest_image_payload = None

    async def capture_frame(self):
        """Captures the current screen and returns a base64 encoded JPG."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1] # Primary monitor
                screenshot = await asyncio.to_thread(sct.grab, monitor)
                
                img = PIL.Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Resize for performance and token reduction
                img.thumbnail((1280, 720))
                
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=70)
                b64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                self._latest_image_payload = {"mime_type": "image/jpeg", "data": b64_data}
                return self._latest_image_payload
        except Exception as e:
            print(f"[VisionService] Error capturing frame: {e}")
            return None

    def get_latest_payload(self):
        return self._latest_image_payload
