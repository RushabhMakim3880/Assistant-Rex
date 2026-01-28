import asyncio
import time
from pywinauto import Desktop, Application
import pywinauto.keyboard as keyboard

class CommunicationsAgent:
    def __init__(self, on_notification=None):
        self.on_notification = on_notification # Callback for UI alerts
        self.whatsapp_app = None
        self.phone_link_app = None
        self.running = False
        self.monitor_task = None

    async def initialize(self):
        print("[CommunicationsAgent] Initializing...")
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_notifications())

    async def _monitor_notifications(self):
        """Monitors for incoming communication notifications (Calls/Messages)."""
        print("[CommunicationsAgent] Notification Monitor Started.")
        last_seen_titles = set()
        
        while self.running:
            try:
                # 1. Check for Phone Link Call Overlay
                desktop = Desktop(backend="uia")
                
                # Broaden search to catch any window that might be a call or notification
                # Added '.*User.*' and similar patterns that Phone Link/WhatsApp popups use
                windows = desktop.windows(title_re=".*Phone Link.*|.*Call.*|.*Incoming.*|.*WhatsApp.*")
                for win in windows:
                    try:
                        title = win.window_text()
                        if not title: continue

                        # Potential Call Detection: Look for "Accept" or "Decline" buttons
                        # Relaxed timeout and added more patterns
                        accept_btn = win.child_window(title_re=".*Accept.*|.*Answer.*|.*Answer call.*", control_type="Button", found_index=0)
                        if accept_btn.exists(timeout=0.2):
                            if f"call_{title}" not in last_seen_titles:
                                print(f"[CommunicationsAgent] Found potential CALL window: {title}")
                                if self.on_notification:
                                    self.on_notification({
                                        "type": "call",
                                        "contact": title.split('-')[-1].strip() if '-' in title else "Unknown",
                                        "time": time.strftime("%I:%M %p")
                                    })
                                last_seen_titles.add(f"call_{title}")
                                break # Found one, good enough for this tick

                        # Special case for WhatsApp windows that are actually notifications (small windows)
                        # Regular WhatsApp window has title "WhatsApp" or "WhatsApp (1)"
                        # If a small window exists with "WhatsApp" in title, it might be the popup
                        if "WhatsApp" in title and "(" in title and ")" in title:
                            if title not in last_seen_titles:
                                print(f"[CommunicationsAgent] New WhatsApp Message detected: {title}")
                                if self.on_notification:
                                    self.on_notification({
                                        "type": "message",
                                        "contact": "WhatsApp",
                                        "message": title,
                                        "time": time.strftime("%I:%M %p")
                                    })
                                last_seen_titles.add(title)

                    except Exception:
                        continue 
                
                # Cleanup old titles periodically
                if len(last_seen_titles) > 20:
                    last_seen_titles.clear()

            except Exception as e:
                # print(f"[CommunicationsAgent] Top-level error: {e}")
                pass
            
            await asyncio.sleep(1.5) # Slightly faster polling

    def _get_whatsapp_window(self):
        try:
            app = Application(backend="uia").connect(title_re=".*WhatsApp.*", timeout=1)
            return app.window(title_re=".*WhatsApp.*")
        except:
            return None

    def _get_phone_link_window(self):
        try:
            app = Application(backend="uia").connect(title_re=".*Phone Link.*", timeout=1)
            return app.window(title_re=".*Phone Link.*")
        except:
            return None

    async def send_whatsapp_message(self, contact, message):
        """Sends a WhatsApp message via native Desktop app."""
        win = self._get_whatsapp_window()
        if not win:
            return "WhatsApp Desktop is not running."
        
        try:
            win.set_focus()
            # Conceptual: Search for contact
            # WhatsApp UI often has a search bar at the top
            search_box = win.child_window(title="Search or start new chat", control_type="Edit")
            if search_box.exists():
                search_box.set_focus()
                search_box.type_keys("^a{BACKSPACE}")
                search_box.type_keys(contact + "{ENTER}")
            else:
                keyboard.send_keys("^f") # Search
                await asyncio.sleep(0.5)
                keyboard.send_keys(contact + "{ENTER}")
            
            await asyncio.sleep(1)
            
            # Type and send
            # Type into the message box
            msg_box = win.child_window(title="Type a message", control_type="Edit")
            if msg_box.exists():
                msg_box.set_focus()
                msg_box.type_keys(message + "{ENTER}")
            else:
                keyboard.send_keys(message + "{ENTER}")
            return f"Message sent to {contact} on WhatsApp."
        except Exception as e:
            return f"Error sending WhatsApp message: {e}"

    async def send_sms(self, contact, message):
        """Sends an SMS via Windows Phone Link."""
        win = self._get_phone_link_window()
        if not win:
            return "Windows Phone Link is not running."
        
        try:
            win.set_focus()
            # Click on Messages Tab
            messages_tab = win.child_window(title="Messages", control_type="ListItem")
            if messages_tab.exists():
                messages_tab.click_input()
                await asyncio.sleep(0.5)
            
            # Click New Message
            new_msg_btn = win.child_window(title="New message", control_type="Button")
            if new_msg_btn.exists():
                new_msg_btn.click_input()
                await asyncio.sleep(0.5)
            
            # Type contact
            to_box = win.child_window(title="To", control_type="Edit")
            if to_box.exists():
                to_box.type_keys(contact + "{ENTER}")
                await asyncio.sleep(0.5)
                
            # Type message
            msg_box = win.child_window(title="Type a message", control_type="Edit")
            if msg_box.exists():
                msg_box.type_keys(message + "{ENTER}")
                return f"SMS sent to {contact} via Phone Link."
            
            return f"Could not find message box in Phone Link UI."
        except Exception as e:
            return f"Error sending SMS: {e}"

    async def handle_call(self, action="accept"):
        """Handles incoming calls by pressing the Answer/Decline buttons."""
        try:
            desktop = Desktop(backend="uia")
            # Search for 'Accept' or 'Answer' or 'Decline' buttons in the entire desktop (overlays)
            pattern = ".*Accept.*|.*Answer.*|.*Answer call.*" if action == "accept" else ".*Decline.*|.*Reject.*|.*End call.*"
            
            # Try to find the button directly across all windows
            for win in desktop.windows():
                try:
                    btn = win.child_window(title_re=pattern, control_type="Button", found_index=0)
                    if btn.exists(timeout=0.1):
                        btn.click_input()
                        return f"Call {action}ed successfully."
                except:
                    continue
                    
            return f"Could not find an active call window to {action}."
        except Exception as e:
            return f"Error handling call: {e}"

# Tool Definitions for Gemini
communication_tools = [
    {
        "name": "send_communication",
        "description": "Send a text message via WhatsApp or SMS (Phone Link).",
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {"type": "string", "enum": ["whatsapp", "sms"], "description": "The service to use."},
                "contact": {"type": "string", "description": "Name or phone number of the recipient."},
                "message": {"type": "string", "description": "The text content to send."}
            },
            "required": ["platform", "contact", "message"]
        }
    },
    {
        "name": "manage_call",
        "description": "Answer or decline an incoming phone/whatsapp call.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["accept", "decline"], "description": "Action to take."}
            },
            "required": ["action"]
        }
    }
]
