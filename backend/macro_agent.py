import os
import time
import json
import base64
import threading
import asyncio
from pynput import mouse
from datetime import datetime
from google import genai
from google.genai import types

class MacroAgent:
    """
    Agent for recording and replaying visual workflows.
    Uses 'pynput' to record clicks and Gemini Vision to replay them robustly.
    """
    def __init__(self, desktop_agent, macros_dir="macros"):
        self.desktop = desktop_agent
        self.macros_dir = os.path.join(os.path.dirname(__file__), macros_dir)
        if not os.path.exists(self.macros_dir):
            os.makedirs(self.macros_dir)
        self.hotkey_listener = None
        self.running = False

    async def start_hotkey_listener(self, sio_handle=None):
        """Starts a background thread to listen for global hotkeys using pynput."""
        try:
            from pynput import keyboard
            self.running = True
            
            def on_trigger():
                print("[MacroAgent] Global Hotkey Triggered!")
                if sio_handle:
                    # Use threadsafe call for Socket.IO in a separate thread
                    asyncio.run_coroutine_threadsafe(
                        sio_handle.emit('macro_triggered', {'action': 'start_recording'}), 
                        asyncio.get_event_loop()
                    )

            # Bind 'Ctrl+Alt+R' to start recording
            # pynput hotkey format: <ctrl>+<alt>+r
            hotkeys = keyboard.GlobalHotKeys({
                '<ctrl>+<alt>+r': on_trigger
            })
            
            def run_listener():
                with hotkeys as h:
                    h.join()

            threading.Thread(target=run_listener, daemon=True).start()
            print("[MacroAgent] Hotkey listener (Ctrl+Alt+R) active via pynput.")
            
            while self.running:
                await asyncio.sleep(5)
        except Exception as e:
            print(f"[MacroAgent] Hotkey listener failed: {e}")
            
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.is_recording = False
        self.current_macro_name = None
        self.current_steps = []
        self.listener = None
        self.step_counter = 0

    async def start_recording(self, name):
        """Starts recording user clicks."""
        if self.is_recording:
            return "Already recording."
            
        self.current_macro_name = name
        self.current_macro_dir = os.path.join(self.macros_dir, name)
        if not os.path.exists(self.current_macro_dir):
            os.makedirs(self.current_macro_dir)
            
        self.current_steps = []
        self.step_counter = 0
        self.is_recording = True
        
        # Start Listener in non-blocking way
        # We need a separate thread because pynput blocks
        self.listener = mouse.Listener(on_click=self._on_click)
        self.listener.start()
        
        print(f"[MacroAgent] Started recording macro: {name}")
        return f"Started recording macro '{name}'. Perform your actions now. Say 'stop recording' when done."

    async def stop_recording(self):
        """Stops the recording and saves metadata."""
        if not self.is_recording:
            return "Not currently recording."
            
        if self.listener:
            self.listener.stop()
            self.listener = None
            
        self.is_recording = False
        
        # Save steps.json
        with open(os.path.join(self.current_macro_dir, "steps.json"), "w") as f:
            json.dump(self.current_steps, f, indent=4)
            
        msg = f"Macro '{self.current_macro_name}' saved with {len(self.current_steps)} steps."
        print(f"[MacroAgent] {msg}")
        return msg

    def _on_click(self, x, y, button, pressed):
        """Callback for pynput mouse listener."""
        if not pressed or not self.is_recording:
            return
            
        # We need to capture the visual context of this click *synchronously* effectively
        # But we are in a thread. We should call async method from here or just capture using mss directly?
        # mss is thread safe? Yes.
        try:
            timestamp = time.time()
            self.step_counter += 1
            step_filename = f"step_{self.step_counter}.png"
            step_path = os.path.join(self.current_macro_dir, step_filename)
            
            # Capture full screen first
            # We can't use self.desktop_agent.get_screenshot() because it's async
            # Use mss directly
            import mss
            import mss.tools
            
            with mss.mss() as sct:
                # Capture a crop around the click? 
                # Let's verify resolution. 
                # Crop 200x200 around x,y
                region = {"top": max(0, y - 100), "left": max(0, x - 100), "width": 200, "height": 200, "monitors": 0}
                
                # We need to find which monitor if multi-head. 
                # Assuming primary monitor or absolute coords. Pynput gives absolute.
                # MSS handles monitors. 
                
                # Ideally we save the *Context* (what button looks like)
                # So a crop is best.
                
                # Using monitor 1 for simplicity or grab specific region
                # sct.grab(region) is easier
                
                sct_img = sct.grab(region)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=step_path)

            step = {
                "id": self.step_counter,
                "action": "click",
                "x_original": x,
                "y_original": y,
                "button": str(button),
                "image": step_filename,
                "ts": timestamp
            }
            self.current_steps.append(step)
            print(f"[MacroAgent] Recorded step {self.step_counter}: Click at {x},{y}")
            
        except Exception as e:
            print(f"[MacroAgent] Recording Error: {e}")

    async def replay_macro(self, name):
        """Replays the macro using computer vision to find buttons."""
        macro_dir = os.path.join(self.macros_dir, name)
        if not os.path.exists(macro_dir):
            return f"Macro '{name}' not found."
            
        with open(os.path.join(macro_dir, "steps.json"), "r") as f:
            steps = json.load(f)
            
        print(f"[MacroAgent] Replaying '{name}' ({len(steps)} steps)...")
        results = []
        
        # Check dependencies
        if not self.desktop_agent:
            results.append("Error: Desktop functionality unavailable.")
            return "\n".join(results)

        for step in steps:

            # 1. Capture current screen
            current_screen = await self.desktop_agent.get_screenshot()
            if not current_screen:
                results.append(f"Step {step['id']}: Failed to capture screen.")
                continue
                
            # 2. Load step reference image
            step_img_path = os.path.join(macro_dir, step['image'])
            with open(step_img_path, "rb") as img_f:
                reference_bytes = img_f.read()
                
            # 3. Vision Matching with Retry Logic
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    prompt = "Locate the exact center of the UI element shown in the first image (the reference crop) within the second image (the full screen). Return JSON: {'x': int, 'y': int} representing the pixel coordinates on the full screen. If not found, return {'error': 'not found'}."
                    
                    response = await self.client.aio.models.generate_content(
                        model="gemini-2.0-flash-exp",
                        contents=[
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part.from_text(text=prompt),
                                    types.Part.from_bytes(data=reference_bytes, mime_type="image/png"),
                                    types.Part.from_bytes(data=base64.b64decode(current_screen["data"]), mime_type="image/png")
                                ]
                            )
                        ],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    
                    coords = json.loads(response.text)
                    
                    if "error" in coords:
                        results.append(f"Step {step['id']}: Element not found visually. Fallback to original coords.")
                        target_x, target_y = step["x_original"], step["y_original"]
                    else:
                        target_x, target_y = coords.get("x"), coords.get("y")
                        print(f"[MacroAgent] Vision located target at {target_x},{target_y} (Original: {step['x_original']},{step['y_original']})")
                    
                    # 4. Click
                    await self.desktop_agent.click(x=target_x, y=target_y)
                    results.append(f"Step {step['id']}: Clicked.")
                    break # Success
                    
                except Exception as e:
                    error_str = str(e)
                    if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                        retry_count += 1
                        wait_time = 2 ** retry_count + 1 # Exponential backoff: 3s, 5s, 9s
                        print(f"[MacroAgent] Quota exhausted (429). Retrying in {wait_time}s... (Attempt {retry_count}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        if retry_count == max_retries:
                             results.append(f"Step {step['id']}: Failed after retries (Quota Limit).")
                    else:
                        print(f"[MacroAgent] Replay Error step {step['id']}: {e}")
                        results.append(f"Step {step['id']}: Error {e}")
                        break

            # Rate Limit Protection: Wait 3 seconds between steps
            await asyncio.sleep(3.0)
                
        return "\n".join(results)
