import pvporcupine
import pyaudio
import struct
import os

class SpeechAgent:
    """
    Handles Wake-Word detection and local Speech-to-Text preprocessing.
    Uses Porcupine for high-sensitivity "Hey Rex" detection.
    """
    def __init__(self, access_key=None, keyword_paths=None, sensitivities=None):
        self.access_key = access_key or os.getenv("PORCUPINE_ACCESS_KEY")
        self.keyword_paths = keyword_paths # List of .ppn file paths
        self.sensitivities = sensitivities or [0.7] # 0-1 (higher = more sensitive)
        
        self.porcupine = None
        self.pa = None
        self.stream = None

    def initialize(self):
        """Initializes the Porcupine engine."""
        if not self.access_key:
            print("[SpeechAgent] [WARN] No Porcupine access key provided. Wake-word disabled.")
            return False
            
        try:
            # We can use built-in keywords or custom ones
            # For 'Hey Rex', we might need a custom .ppn file. 
            # If not found, we fallback to 'Computer' or 'REX' if available.
            keywords = ['computer']
            if self.keyword_paths:
                 self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=self.keyword_paths,
                    sensitivities=self.sensitivities
                )
            else:
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=keywords,
                    sensitivities=self.sensitivities
                )
            return True
        except Exception as e:
            print(f"[SpeechAgent] Initialization error: {e}")
            return False

    def process_frame(self, pcm_frame):
        """Processes a frame of audio (must be of length self.porcupine.frame_length)."""
        if not self.porcupine:
            return -1
            
        result = self.porcupine.process(pcm_frame)
        return result

    def cleanup(self):
        if self.porcupine:
            self.porcupine.delete()
        if self.stream:
            self.stream.close()
        if self.pa:
            self.pa.terminate()

# Tool definitions? This agent is mostly a internal component
# But we could expose 'set_sensitivity'
speech_tools = [
    {
        "name": "set_wake_word_sensitivity",
        "description": "Adjusts how sensitive R.E.X. is to the 'Hey Rex' wake word.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "level": {"type": "NUMBER", "description": "Sensitivity level from 0.0 to 1.0"}
            },
            "required": ["level"]
        }
    }
]
