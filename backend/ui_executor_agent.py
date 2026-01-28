import pyautogui
import time
import pyperclip
import os

class UIExecutorAgent:
    """
    Handles robust UI interactions including shortcuts, text injection, 
    and multi-step command sequences.
    """
    def __init__(self, context_agent):
        self.context = context_agent
        pyautogui.PAUSE = 0.5
        pyautogui.FAILSAFE = True

    async def type_into_editor(self, text, app_context=None):
        """
        Types text into the currently focused editor. 
        Uses clipboard for large blocks to ensure speed and accuracy.
        """
        if app_context:
            if not self.context.is_window_focused(app_context):
                print(f"[UIExecutor] Focus lost on {app_context}. Aborting type.")
                return False

        # If text is large, use clipboard
        if len(text) > 100:
            print("[UIExecutor] Large text block detected. Using clipboard paste.")
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
        else:
            pyautogui.write(text, interval=0.01)
        
        return True

    async def save_file(self, path):
        """
        Generic file saving workflow using Ctrl+S and typing the path.
        """
        print(f"[UIExecutor] Attempting to save file to: {path}")
        
        # Trigger Save dialog
        pyautogui.hotkey('ctrl', 's')
        time.sleep(1)
        
        # Type path
        pyautogui.write(path)
        time.sleep(0.5)
        pyautogui.press('enter')
        
        # Check for 'Overwrite' prompt (heuristic)
        # If the filename already existed, Notepad/VSCode might ask for confirmation
        # This is a risk point - we assume success for now or would need image recogn.
        time.sleep(1)
        return True

    async def open_new_file(self):
        """Triggers Ctrl+N"""
        pyautogui.hotkey('ctrl', 'n')
        time.sleep(0.5)
        return True

    async def trigger_shortcut(self, *keys):
        """Triggers a combination of keys."""
        pyautogui.hotkey(*keys)
        return True
