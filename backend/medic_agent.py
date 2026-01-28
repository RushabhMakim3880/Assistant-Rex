import os
import sys
import traceback
import subprocess
from google import genai
from google.genai import types

class MedicAgent:
    """
    The 'Ghost in the Shell'.
    Monitors for crashes, analyzes tracebacks, patches code, and restarts the system.
    """
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.0-flash-exp" # Fast coder model

    async def heal(self, error_trace, broken_file_path=None):
        """
        Analyzes the error, patches the file, and prepares for restart.
        """
        print(f"\n[MEDIC] 🚑 ALERT! Critical System Failure Detected.")
        print(f"[MEDIC] Analyzing trauma: {error_trace[-100:]}...") # Print last bit

        if not broken_file_path:
            # Try to infer file from traceback
            # Simple heuristic: find the last file in the stack that is inside our project (not lib)
            lines = error_trace.split('\n')
            for line in reversed(lines):
                if 'File "' in line and 'rex' in line.lower(): # Assuming 'rex' is in project path
                    try:
                        part = line.split('File "')[1]
                        path = part.split('",')[0]
                        if os.path.exists(path):
                            broken_file_path = path
                            break
                    except:
                        continue
        
        if not broken_file_path:
            print("[MEDIC] ❌ Could not locate the broken file. Automatic healing aborted.")
            return False

        print(f"[MEDIC] 🏥 Victim identified: {broken_file_path}")
        
        # Read the broken code
        try:
            with open(broken_file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
        except Exception as e:
            print(f"[MEDIC] Failed to read file: {e}")
            return False

        # Consult the LLM Surgeon
        prompt = f"""
        You are an expert Python debugger and system repair AI.
        My code just crashed. Here is the traceback and the file content.
        
        Traceback:
        {error_trace}
        
        File Content ({broken_file_path}):
        ```python
        {code_content}
        ```
        
        Your Mission:
        1. Identify the bug.
        2. Fix the bug in the code.
        3. Return the COMPLETE fixed file content.
        4. Do NOT remove any existing functionality, only fix the specific error.
        5. Return ONLY the code, mostly standard python. No markdown blocks if possible, or start with ```python.
        """
        
        try:
            print("[MEDIC] 🧠 Synthesizing patch...")
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            fixed_code = response.text
            
            # Clean up formatting
            if fixed_code.startswith("```python"):
                fixed_code = fixed_code[9:]
            elif fixed_code.startswith("```"):
                fixed_code = fixed_code[3:]
            if fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]
            
            # Verify it's not empty
            if not fixed_code.strip():
                print("[MEDIC] ⚠️ Generated patch was empty. Aborting.")
                return False

            # Create backup
            backup_path = broken_file_path + ".bak"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(code_content)
            print(f"[MEDIC] 💾 Backup saved to {backup_path}")

            # Apply Patch
            with open(broken_file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            
            print(f"[MEDIC] ✅ Patch applied successfully!")
            return True

        except Exception as e:
            print(f"[MEDIC] 💀 Surgery failed: {e}")
            return False

    def restart_system(self):
        """Restarts the current process."""
        print("[MEDIC] 🔄 Initiating Emergency Restart sequence...")
        python = sys.executable
        os.execl(python, python, *sys.argv)
