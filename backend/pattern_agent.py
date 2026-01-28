import json
import os
from datetime import datetime
from collections import Counter

class PatternAgent:
    """
    Tracks tool usage patterns and suggests workflows based on context.
    """
    def __init__(self, data_path="usage_patterns.json", persona_path="persona.json"):
        self.data_path = os.path.join(os.path.dirname(__file__), data_path)
        self.persona_path = os.path.join(os.path.dirname(__file__), persona_path)
        self.history = []
        self.persona = {
            "traits": {"conciseness": 0.5, "technicality": 0.7},
            "preferences": {"preferred_browser": "chrome", "favorite_tools": []},
            "tone": "helpful expert"
        }
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r') as f:
                    self.history = json.load(f)
            except:
                self.history = []
        
        if os.path.exists(self.persona_path):
            try:
                with open(self.persona_path, 'r') as f:
                    self.persona = json.load(f)
            except:
                pass

    def _save_data(self):
        try:
            if len(self.history) > 500:
                self.history = self.history[-500:]
            with open(self.data_path, 'w') as f:
                json.dump(self.history, f, indent=4)
            with open(self.persona_path, 'w') as f:
                json.dump(self.persona, f, indent=4)
        except:
            pass

    async def log_interaction(self, intent, tool_name, success=True):
        """Logs a tool interaction and updates preferences."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "hour": datetime.now().hour,
            "intent": intent,
            "tool": tool_name,
            "success": success
        }
        self.history.append(entry)
        
        # Update favorite tools
        tools = [h['tool'] for h in self.history if h['success']]
        counts = Counter(tools)
        self.persona["preferences"]["favorite_tools"] = [t for t, _ in counts.most_common(5)]
        
        self._save_data()

    async def reload_data(self):
        """Hot-loads state from disk (called by SyncAgent)."""
        print("[PatternAgent] Hot-reloading persona and history...")
        self._load_data()
        return True

    async def get_workflow_suggestions(self, current_app=None):
        """
        Analyzes history to suggest what the user might want to do next.
        """
        if not self.history:
            return []

        # Simple algorithm: Find most frequent intents for this hour
        current_hour = datetime.now().hour
        similar_hour_intents = [h['intent'] for h in self.history if abs(h['hour'] - current_hour) <= 1]
        
        if not similar_hour_intents:
            return []

        counts = Counter(similar_hour_intents)
        common = counts.most_common(3)
        
        suggestions = []
        for intent, _ in common:
            # Check if this intent is related to current_app if provided
            if current_app:
                # Heuristic: if current_app name is in the intent or tool was related
                related = any(current_app.lower() in h['intent'].lower() for h in self.history if h['intent'] == intent)
                if related:
                    suggestions.append(intent)
            else:
                suggestions.append(intent)

        return suggestions[:2] # Return top 2 suggestions

    def get_persona_context(self):
        """Generates a context string for LLM prompts based on learned persona."""
        favs = ", ".join(self.persona["preferences"]["favorite_tools"])
        context = f"You are R.E.X. Your learned tone is '{self.persona['tone']}'. "
        if favs:
            context += f"The user frequently uses tools: {favs}. "
        context += f"Aim for level {self.persona['traits']['conciseness']} conciseness."
        return context
