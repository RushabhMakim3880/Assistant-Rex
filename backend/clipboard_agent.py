import asyncio
import pyperclip
from datetime import datetime

class ClipboardAgent:
    def __init__(self, history_limit=10):
        self.history = []
        self.history_limit = history_limit
        self.last_text = ""
        self.is_running = False

    async def start_monitoring(self):
        """Starts the background loop to monitor clipboard changes."""
        self.is_running = True
        print("[ClipboardAgent] Monitoring started.")
        while self.is_running:
            try:
                # Use a thread for potentially blocking pyperclip call
                current_text = await asyncio.to_thread(pyperclip.paste)
                
                if current_text and current_text != self.last_text:
                    self.last_text = current_text
                    timestamp = datetime.now().strftime("%I:%M %p")
                    
                    # Store with metadata
                    entry = {
                        "text": current_text,
                        "time": timestamp,
                        "preview": (current_text[:100] + '...') if len(current_text) > 100 else current_text
                    }
                    
                    self.history.insert(0, entry)
                    
                    # Keep limit
                    if len(self.history) > self.history_limit:
                        self.history.pop()
                        
                    print(f"[ClipboardAgent] New entry detected ({timestamp})")
                    
            except Exception as e:
                print(f"[ClipboardAgent] Error: {e}")
                
            await asyncio.sleep(2) # Poll every 2 seconds

    def stop_monitoring(self):
        self.is_running = False

    def get_history(self):
        """Returns the recent clipboard history."""
        return self.history

    def get_current(self):
        """Returns the latest item."""
        return self.history[0] if self.history else None

    def clear_history(self):
        self.history = []
        self.last_text = ""

# Tool Definitions for Gemini
clipboard_tools = [
    {
        "name": "get_clipboard_summary",
        "description": "Returns a summary of the most recently copied text snippets from the system clipboard.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "recall_clipboard_item",
        "description": "Searches the clipboard history for a specific keyword or snippet.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword to search for in clipboard history."}
            },
            "required": ["query"]
        }
    }
]
