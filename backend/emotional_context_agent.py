from collections import deque
import time

class EmotionalContextAgent:
    """
    Analyzes user input patterns to detect emotional state.
    Adjusts R.E.X.'s personality and verbosity accordingly.
    """
    def __init__(self):
        self.message_history = deque(maxlen=10)
        self.current_state = "calm"
        self.last_message_time = time.time()
        
        # Emotional indicators
        self.frustrated_words = ["error", "broken", "wtf", "stupid", "damn", "fuck", "why", "wrong", "fix", "ugh"]
        self.excited_words = ["awesome", "yes", "great", "love", "perfect", "nice", "wow", "cool", "amazing"]
        self.stressed_words = ["urgent", "asap", "quickly", "hurry", "deadline", "help", "stuck"]
    
    async def initialize(self):
        print("[EmotionalContextAgent] Initialized and ready.")
    
    async def analyze_message(self, text):
        """
        Analyzes user message and updates emotional state.
        Returns: emotion (calm, frustrated, excited, stressed)
        """
        current_time = time.time()
        time_delta = current_time - self.last_message_time
        self.last_message_time = current_time
        
        # Record message
        self.message_history.append({
            "text": text.lower(),
            "length": len(text),
            "time_delta": time_delta
        })
        
        # Calculate rapid messaging (indicator of stress/frustration)
        recent_msgs = list(self.message_history)[-3:]
        rapid_messages = sum(1 for m in recent_msgs if m["time_delta"] < 5)
        
        # Calculate short messages (indicator of frustration)
        short_messages = sum(1 for m in recent_msgs if m["length"] < 20)
        
        # Word analysis
        text_lower = text.lower()
        frustrated_count = sum(1 for word in self.frustrated_words if word in text_lower)
        excited_count = sum(1 for word in self.excited_words if word in text_lower)
        stressed_count = sum(1 for word in self.stressed_words if word in text_lower)
        
        # Determine emotional state
        if frustrated_count >= 2 or (rapid_messages >= 2 and short_messages >= 2):
            self.current_state = "frustrated"
        elif stressed_count >= 1 and rapid_messages >= 2:
            self.current_state = "stressed"
        elif excited_count >= 1:
            self.current_state = "excited"
        else:
            self.current_state = "calm"
        
        print(f"[EmotionalContext] Detected: {self.current_state}")
        return self.current_state
    
    def get_personality_modifier(self):
        """
        Returns system instruction modifier based on emotional state.
        """
        modifiers = {
            "calm": "",  # Default personality
            "frustrated": "\nSir seems frustrated. Be extra patient, concise, and solution-focused. Skip the wit temporarily and focus on resolving the issue efficiently.",
            "excited": "\nSir seems excited! Match the energy with enthusiasm and positivity. Use more expressive language.",
            "stressed": "\nSir seems stressed or in a hurry. Be extremely concise and directive. Prioritize speed and clarity over charm."
        }
        return modifiers.get(self.current_state, "")
    
    async def shutdown(self):
        print("[EmotionalContextAgent] Shutdown complete.")
