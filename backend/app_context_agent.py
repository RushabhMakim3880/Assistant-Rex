import pywinauto
from pywinauto import Desktop
import psutil
import time
import os

class AppContextAgent:
    """
    Monitors application state, active windows, and UI readiness.
    Provides the ground truth for workflow verification.
    """
    def __init__(self):
        self.desktop = Desktop(backend="uia")
        self.last_known_app = None

    def get_active_window(self):
        """Returns the currently focused window object."""
        try:
            return self.desktop.window(active_only=True)
        except:
            return None

    def get_active_app_info(self):
        """Returns details about the active application."""
        win = self.get_active_window()
        if not win:
            return None
        
        try:
            title = win.window_text()
            pid = win.process_id()
            proc = psutil.Process(pid)
            name = proc.name().lower()
            
            return {
                "name": name,
                "title": title,
                "pid": pid,
                "executable": proc.exe()
            }
        except Exception as e:
            print(f"[AppContextAgent] Error getting app info: {e}")
            return None

    async def wait_for_app_ready(self, app_name_substring, timeout=15):
        """
        Polls until an application with a matching name is visible and focused.
        """
        start_time = time.time()
        print(f"[AppContextAgent] Waiting for '{app_name_substring}' to be ready...")
        
        while time.time() - start_time < timeout:
            info = self.get_active_app_info()
            if info:
                # Check if app name or title contains the substring
                if app_name_substring.lower() in info['name'] or app_name_substring.lower() in info['title'].lower():
                    print(f"[AppContextAgent] Target app '{info['name']}' is focused and ready.")
                    return True
            
            # If not focused, check if it exists in background and try to bring to foreground
            last_err = ""
            try:
                # Search for all windows to find a match
                for win in self.desktop.windows():
                    title = win.window_text().lower()
                    if app_name_substring.lower() in title:
                         print(f"[AppContextAgent] Found matching window '{title}'. Attempting to focus...")
                         try:
                             win.set_focus()
                             await asyncio.sleep(0.5)
                             return True
                         except Exception as e:
                             last_err = str(e)
            except Exception as e:
                last_err = str(e)
                
            if last_err:
                print(f"[AppContextAgent] Focus attempt warning: {last_err}")
                
            await asyncio.sleep(1)
        
        print(f"[AppContextAgent] Timeout: '{app_name_substring}' not ready.")
        return False

    def is_window_focused(self, name_pattern):
        """Checks if current focus matches pattern."""
        info = self.get_active_app_info()
        if not info: return False
        return name_pattern.lower() in info['name'] or name_pattern.lower() in info['title'].lower()

    def get_ui_hierarchy(self, win):
        """Returns a simplified list of UI elements in the window for high-level state checking."""
        # Note: Printing the full hierarchy is too slow; we just check for 'Edit' or 'Document' controls
        try:
            # Check if this is a text editor
            desc = win.descendants(control_type="Edit")
            if not desc:
                desc = win.descendants(control_type="Document")
            
            return {
                "has_editor": len(desc) > 0,
                "control_types": list(set([d.control_type() for d in desc[:10]]))
            }
        except:
            return {"has_editor": False}
