import multiprocessing
import queue
import pyaudio
import time
import os
import numpy as np

# Signal to stop the process
STOP_SIGNAL = None
RESET_SIGNAL = "RESET"

class AudioEngine(multiprocessing.Process):
    """
    Dedicated process for Zero-Latency Audio Playback.
    Uses a Jitter Buffer strategy to ensure smooth playback across process boundaries.
    """
    def __init__(self, audio_queue, output_device_index=None, status_queue=None):
        super().__init__()
        self.audio_queue = audio_queue
        self.output_device_index = output_device_index
        self.status_queue = status_queue 
        self.buffer_threshold = 2 # Reduced threshold for faster response
        
        # Audio Config (Gemini Defaults)
        self.channels = 1
        self.rate = 24000 
        self.format = pyaudio.paInt16
        
    def _set_priority(self):
        """Set process priority to High for stable audio."""
        try:
            if os.name == 'nt':
                import psutil
                p = psutil.Process(os.getpid())
                p.nice(psutil.HIGH_PRIORITY_CLASS)
            else:
                os.nice(-10)
        except Exception as e:
            print(f"[AudioEngine] Could not set priority: {e}")

    def run(self):
        """Main loop in separate process."""
        self._set_priority()
        
        try:
            self.p = pyaudio.PyAudio()
            
            # Device Inspection
            try:
                if self.output_device_index is not None:
                    device_info = self.p.get_device_info_by_index(self.output_device_index)
                    if device_info.get('maxOutputChannels', 0) == 0:
                        self.output_device_index = None
                
                if self.output_device_index is None:
                    device_info = self.p.get_default_output_device_info()
            except:
                device_info = {"name": "Unknown", "maxOutputChannels": 2}
            
            max_channels = int(device_info.get('maxOutputChannels', 2))
            
            # Multi-channel robustness
            self.stream = None
            potential_channels = sorted(list(set([1, 2, max_channels])))
            for channel_count in potential_channels:
                if channel_count <= 0: continue
                try:
                    self.stream = self.p.open(
                        format=self.format,
                        channels=channel_count,
                        rate=self.rate,
                        output=True,
                        output_device_index=self.output_device_index,
                        frames_per_buffer=1024
                    )
                    self.channels = channel_count
                    break
                except: continue
            
            if not self.stream:
                raise Exception("Failed to open audio stream.")
            
            print(f"[AudioEngine] Process Ready (PID: {os.getpid()}) on device {self.output_device_index}")
            
            jitter_buffer = []
            is_playing = False
            
            while True:
                try:
                    # TIGHT TIMEOUT (5ms) to prevent audible gaps
                    chunk = self.audio_queue.get(timeout=0.005)
                except queue.Empty:
                    if is_playing and not jitter_buffer:
                        # Natural pause or underrun
                        # print("[AudioEngine] Jitter buffer underrun detected.")
                        pass
                    continue

                if chunk is STOP_SIGNAL:
                    break
                    
                if chunk == RESET_SIGNAL:
                    jitter_buffer = []
                    is_playing = False
                    # Stop current stream output for instant silence
                    try:
                        self.stream.stop_stream()
                        self.stream.start_stream()
                    except: pass
                    continue
                        
                # Queue data
                jitter_buffer.append(chunk)
                
                # Start playback once buffered
                if not is_playing:
                    if len(jitter_buffer) >= self.buffer_threshold:
                        is_playing = True
                        
                if is_playing:
                    while jitter_buffer:
                        data = jitter_buffer.pop(0)
                        
                        # Expand to stereo if the hardware requires it
                        if self.channels > 1:
                            mono_data = np.frombuffer(data, dtype=np.int16)
                            multi_data = np.repeat(mono_data, self.channels)
                            data = multi_data.tobytes()

                        try:
                            self.stream.write(data)
                        except Exception as e:
                            print(f"[AudioEngine] Write error: {e}")
                            break

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"[AudioEngine] CRITICAL ERROR: {e}")
        finally:
            print("[AudioEngine] Shutting down...")
            if hasattr(self, 'stream') and self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except: pass
            if hasattr(self, 'p'):
                self.p.terminate()

def create_audio_engine(output_device_index=None):
    audio_queue = multiprocessing.Queue()
    engine = AudioEngine(audio_queue, output_device_index=output_device_index)
    return engine, audio_queue
