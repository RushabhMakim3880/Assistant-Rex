import asyncio
import subprocess
import os
from collections import deque
import re

terminal_tools = [
    {
        "name": "run_terminal_command",
        "description": "Executes a shell command in the terminal. Use this to install packages, run scripts, manage git, or browse files via CLI.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {"type": "STRING", "description": "The shell command to execute (e.g., 'npm install', 'python script.py', 'dir')."},
                "cwd": {"type": "STRING", "description": "Optional working directory."}
            },
            "required": ["command"]
        }
    }
]

class TerminalAgent:
    def __init__(self, workspace_root=".", sandbox=None):
        self.workspace_root = os.path.abspath(workspace_root)
        self.sandbox = sandbox
        self.command_history = deque(maxlen=50)  # Ghost Terminal tracking
        self.error_patterns = {
            r"command not found": "typo or missing installation",
            r"No such file or directory": "incorrect path",
            r"npm ERR!": "npm error",
            r"SyntaxError": "Python syntax error",
            r"ModuleNotFoundError": "missing Python module",
            r"ENOENT": "file/command not found"
        }
        self.common_typos = {
            "npm rnu": "npm run",
            "pytohn": "python",
            "cd..": "cd ..",
            "pip insatll": "pip install",
            "gti": "git"
        }

    async def initialize(self):
        print(f"[TerminalAgent] Initialized in {self.workspace_root} (Ghost Terminal active)")
        if self.sandbox:
            print("[TerminalAgent] Sandbox Protection: ENABLED")

    async def run_command(self, command, cwd=None):
        """
        Executes a shell command and returns the output.
        Ghost Terminal: Tracks command and detects errors.
        Sandbox: Validates execution directory.
        """
        exec_cwd = cwd if cwd else self.workspace_root
        
        # Sandbox Validation
        if self.sandbox:
            try:
                self.sandbox.validate_path(exec_cwd)
            except PermissionError as e:
                return str(e)

        print(f"[TerminalAgent] Executing: {command} in {exec_cwd}")
        
        # Record command
        self.command_history.append({"cmd": command, "cwd": exec_cwd})
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=exec_cwd
            )

            # Wait for output
            stdout, stderr = await process.communicate()
            
            output = ""
            if stdout:
                output += stdout.decode('utf-8', errors='replace')
            if stderr:
                output += "\n[STDERR]\n" + stderr.decode('utf-8', errors='replace')
            
            # Ghost Terminal: Detect errors and suggest fixes
            if process.returncode != 0:
                suggestion = self._detect_and_suggest(command, output)
                if suggestion:
                    output += f"\n\n[Ghost Terminal Whisper] {suggestion}"
                
            return output.strip() if output.strip() else "[Command executed successfully with no output]"

        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def _detect_and_suggest(self, command, error_output):
        """Ghost Terminal: Analyzes error and suggests fixes."""
        # Check for common typos
        for typo, correction in self.common_typos.items():
            if typo in command:
                return f"Did you mean: {command.replace(typo, correction)}?"
        
        # Check for error patterns
        for pattern, hint in self.error_patterns.items():
            if re.search(pattern, error_output, re.IGNORECASE):
                if "command not found" in pattern:
                    return f"Command not found. Check spelling or install the required tool."
                elif "No such file" in pattern:
                    return f"File/directory doesn't exist. Verify the path."
                elif "ModuleNotFoundError" in pattern:
                    match = re.search(r"No module named '(\w+)'", error_output)
                    if match:
                        module = match.group(1)
                        return f"Install the module: pip install {module}"
        
        return None
    
    async def get_recent_commands(self, count=5):
        """Returns recent command history for context."""
        return list(self.command_history)[-count:]
    
    async def shutdown(self):
        print("[TerminalAgent] Shutdown complete.")
