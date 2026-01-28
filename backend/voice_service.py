import asyncio
import os
import time
import struct
import math
import traceback
import pyaudio

class VoiceService:
    """
    Handles audio input, VAD (Voice Activity Detection), and wake-word monitoring.
    Extracted from rex.py for modularity.
    """
    def __init__(self, settings=None, on_transcription=None, on_vad_trigger=None):
        self.settings = settings or {}
        self.on_transcription = on_transcription
        self.on_vad_trigger = on_vad_trigger
        
        self.running = False
        self.paused = False
        self.audio_stream = None
        self.p = None
        
        # Audio Config
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk_size = 1024
        
        # VAD State
        self.vad_threshold = self.settings.get("vad_threshold", 100)
        self.silence_duration = 0.5
        self._is_speaking = False
        self._silence_start_time = None
        
        # Device Config
        self.input_device_index = self.settings.get("input_device_index")
        self.input_device_name = self.settings.get("input_device_name")

    async def start(self, out_queue=None):
        self.running = True
        self.p = pyaudio.PyAudio()
        
        device_index = self._resolve_device()
        
        try:
            self.audio_stream = await asyncio.to_thread(
                self.p.open,
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size,
            )
        except Exception as e:
            print(f"[VoiceService] ERROR: Failed to open audio stream: {e}")
            return

        asyncio.create_task(self._listen_loop(out_queue))

    async def _listen_loop(self, out_queue):
        while self.running:
            if self.paused:
                await asyncio.sleep(0.1)
                continue
            
            try:
                data = await asyncio.to_thread(self.audio_stream.read, self.chunk_size, exception_on_overflow=False)
                
                # RMS Calculation
                count = len(data) // 2
                shorts = struct.unpack(f"<{count}h", data) if count > 0 else []
                rms = 0
                if count > 0:
                    sum_squares = sum(s**2 for s in shorts)
                    rms = int(math.sqrt(sum_squares / count))
                
                if out_queue:
                    await out_queue.put({"data": data, "mime_type": "audio/pcm"})
                
                # VAD Logic
                if rms > self.vad_threshold:
                    self._silence_start_time = None
                    if not self._is_speaking:
                        self._is_speaking = True
                        if self.on_vad_trigger:
                            await self.on_vad_trigger(rms)
                else:
                    if self._is_speaking:
                        if self._silence_start_time is None:
                            self._silence_start_time = time.time()
                        elif time.time() - self._silence_start_time > self.silence_duration:
                            self._is_speaking = False
                            self._silence_start_time = None
                            
            except Exception as e:
                print(f"[VoiceService] Error in loop: {e}")
                await asyncio.sleep(0.1)

    def _resolve_device(self):
        """Simple device resolver based on index or name."""
        if self.input_device_index is not None:
            return self.input_device_index
        return None # Default

    async def stop(self):
        self.running = False
        if self.audio_stream:
            self.audio_stream.close()
        if self.p:
            self.p.terminate()

    def set_paused(self, paused):
        self.paused = paused
