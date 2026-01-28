import mss
import mss.tools
import pywinauto
import pyautogui
from pywinauto import Desktop
import os
import base64
import json
from datetime import datetime

class DesktopAgent:
    """
    Agent for inspecting the Windows Desktop environment.
    Capabilities:
    - Screenshot capture (Visual QA)
    - Active window detection
    - (Future) App launching/control
    """
    def __init__(self):
        self.sct = mss.mss()
        self.desktop = Desktop(backend="uia")

    async def get_screenshot(self, monitor_index=1):
        """
        Captures a screenshot of the specified monitor.
        Returns: Base64 encoded PNG string.
        """
        try:
            # mss monitors are 1-indexed (0 is all monitors combined)
            monitor = self.sct.monitors[monitor_index]
            
            # Capture
            sct_img = self.sct.grab(monitor)
            
            # Convert to PNG bytes
            png_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
            
            # Encode to Base64
            b64_str = base64.b64encode(png_bytes).decode('utf-8')
            
            # DEBUG: Save to disk to verify what REX sees
            try:
                with open("debug_screenshot.png", "wb") as f:
                    f.write(png_bytes)
                print(f"[DesktopAgent] Saved debug screenshot to debug_screenshot.png")
            except Exception as e:
                print(f"[DesktopAgent] Failed to save debug screenshot: {e}")

            return {"mime_type": "image/png", "data": b64_str}
            
        except Exception as e:
            print(f"[DesktopAgent] Screenshot error: {e}")
            return None

    async def get_active_window_info(self):
        """Returns details about the currently focused window."""
        try:
            window = self.desktop.window(active_only=True)
            if window:
                return {
                    "title": window.window_text(),
                    "rect": window.rectangle().mid_point(),
                    "process": window.process_id()
                }
        except Exception as e:
            print(f"[DesktopAgent] Active window error: {e}")
            return None

    async def get_current_time(self):
        """Returns the current system time."""
        return datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    async def shutdown(self):
        self.sct.close()

    # --- Autonomous Control Methods ---
    async def move_mouse(self, x, y):
        """Moves mouse to (x, y) coordinates."""
        try:
            # Add safety margin or check screen size? PyAuthGUI handles out of bounds usually (fails safe)
            # screen_width, screen_height = pyautogui.size()
            pyautogui.moveTo(x, y, duration=0.5) # Smooth move
            return True
        except Exception as e:
            print(f"[DesktopAgent] Move error: {e}")
            return False

    async def click(self, x=None, y=None, button='left', clicks=1):
        """Clicks at current or specified position."""
        try:
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            return True
        except Exception as e:
            print(f"[DesktopAgent] Click error: {e}")
            return False
            
    async def type_text(self, text, interval=0.01):
        """Types text at current cursor location."""
        try:
            pyautogui.write(text, interval=interval)
            return True
        except Exception as e:
            print(f"[DesktopAgent] Type error: {e}")
            return False

    async def press_key(self, key):
        """Presses a specific key (e.g. 'enter', 'esc')."""
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            print(f"[DesktopAgent] Press error: {e}")
            return False
            
    async def scroll(self, clicks):
        """Scrolls the mouse wheel (positive = up)."""
        try:
            pyautogui.scroll(clicks)
            return True
        except Exception as e:
            print(f"[DesktopAgent] Scroll error: {e}")
            return False

    async def launch_app(self, app_path_or_name, initial_content=None):
        """Launches an application and optionally types content into it."""
        try:
            print(f"[DesktopAgent] Launching: {app_path_or_name}")
            
            # 1. Launch the Application using Popen to capture PID
            # We prefer Popen over os.startfile to track the process
            import subprocess
            proc = subprocess.Popen(app_path_or_name, shell=True)
            print(f"[DesktopAgent] Process started with PID (approx if shell=True): {proc.pid}")
            
            # 2. If content is provided, Enter "Act-Wait-Type" Protocol
            if initial_content:
                print(f"[DesktopAgent] Initial content provided. Waiting for focus...")
                if await self._wait_for_focus(app_path_or_name, pid=proc.pid):
                    print(f"[DesktopAgent] Focus acquired. Typing content...")
                    # Small delay to ensure input queue is ready
                    await asyncio.sleep(0.5)
                    # Type with newlines handled? pyautogui does enter for \n
                    await self.type_text(initial_content.replace("\\n", "\n"), interval=0.01)
                else:
                    print(f"[DesktopAgent] [WARN] Failed to acquire focus for {app_path_or_name}. Content not typed.")
            
            return True
        except Exception as e:
            print(f"[DesktopAgent] Launch error: {e}")
            return False

    async def _wait_for_focus(self, app_name, pid=None, timeout=10):
        """
        Heuristic to wait for a window related to the app to appear and become active.
        Prioritizes PID matching if accurate, otherwise falls back to Smart Title Matching.
        """
        start_time = time.time()
        # Normalize app name for searching (e.g., 'notepad.exe' -> 'notepad')
        search_term = os.path.basename(app_name).lower().replace(".exe", "")
        
        print(f"[DesktopAgent] Waiting for focus: Term='{search_term}', PID={pid}")
        
        while time.time() - start_time < timeout:
            try:
                # Iterate through all top-level windows to find a match
                windows = self.desktop.windows()
                target_window = None
                
                for w in windows:
                    # 1. PID Match (Best if PID is accurate)
                    # Note: shell=True in Popen often returns the shell PID, not the child app PID.
                    # So PID matching might fail if shell=True is used for system commands.
                    # We only trust PID if it seems reasonable, but we rely heavily on Title Match as fallback.
                    
                    try:
                        w_pid = w.process_id()
                        w_title = w.window_text().lower()
                    except:
                        continue

                    # 2. Title Match (Robust Fallback)
                    # Windows 11 Notepad title is just "Untitled" or "filename". 
                    # But the *process name* via pywinauto/psutil would be better.
                    # We check if search_term is in title OR if title matches common patterns
                    
                    is_match = False
                    if search_term in w_title: 
                        is_match = True
                    elif search_term == "notepad" and ("untitled" in w_title or ".txt" in w_title):
                        # Specific heuristic for Windows 11 Notepad
                        is_match = True
                    
                    if is_match and w.is_visible():
                        target_window = w
                        break
                
                if target_window:
                    print(f"[DesktopAgent] Found target window: '{target_window.window_text()}'")
                    # Force focus
                    try:
                        if not target_window.is_active():
                            target_window.set_focus()
                        return True
                    except Exception as e:
                         print(f"[DesktopAgent] Focus exception: {e}")
                         # Might be race condition, retry loop
                         pass

            except Exception as e:
                print(f"[DesktopAgent] Wait loop error: {e}")
            
            await asyncio.sleep(0.5)
        
        return False

    async def close_app(self, process_name):
        """Closes an application by process name."""
        try:
            import os
            # Use taskkill on Windows for reliability
            os.system(f"taskkill /f /im {process_name}")
            return True
        except Exception as e:
            print(f"[DesktopAgent] Close error: {e}")
            return False

# Tool Definitions for Gemini
desktop_tools = [
    {
        "name": "get_desktop_screenshot",
        "description": "Captures a screenshot of the user's current desktop to answer questions about what is on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "get_active_window",
        "description": "Gets the title and info of the currently focused window.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "get_current_time",
        "description": "Returns the current system date and time. Use this to provide accurate time information to the user.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    }
]

desktop_tools.extend([
    {
        "name": "desktop_click",
        "description": "Clicks the mouse at specific coordinates or current location.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "x": {"type": "INTEGER", "description": "X coordinate (optional)"},
                "y": {"type": "INTEGER", "description": "Y coordinate (optional)"},
                "button": {"type": "STRING", "description": "left, right, or middle (default: left)"},
                "clicks": {"type": "INTEGER", "description": "Number of clicks (default: 1)"}
            },
        }
    },
    {
        "name": "desktop_type",
        "description": "Types text at the current cursor location.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {"type": "STRING", "description": "Text to type"},
                "interval": {"type": "NUMBER", "description": "Delay between keystrokes (default: 0.01)"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "desktop_scroll",
        "description": "Scrolls the mouse wheel.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "amount": {"type": "INTEGER", "description": "Scroll amount (positive=up, negative=down)"}
            },
            "required": ["amount"]
        }
    },
    {
        "name": "desktop_press_key",
        "description": "Presses a specific keyboard key (e.g., 'enter', 'esc', 'space', 'backspace').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING", "description": "Key name"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "launch_app",
        "description": "Launches an application. Optionally accepts 'initial_content' to type immediately after opening (e.g., for 'Open Notepad and write...').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_path_or_name": {"type": "STRING", "description": "The name or path of the app (e.g. 'notepad', 'calc')."},
                "initial_content": {"type": "STRING", "description": "Text to type into the application immediately after it opens."}
            },
            "required": ["app_path_or_name"]
        }
    },
    {
        "name": "close_app",
        "description": "Forcibly closes an application by its process name (e.g., 'notepad.exe').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "process_name": {"type": "STRING", "description": "The name of the process to kill."}
            },
            "required": ["process_name"]
        }
    }
])
