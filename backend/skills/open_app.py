import os
import subprocess
import shlex
import sys

def open_application(app_name: str):
    """
    Opens an application by name.
    """
    print(f"[SKILL] Request to open app: {app_name}")
    
    # Common Windows Apps Mapping
    app_map = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "chrome": "start chrome", 
        "browser": "start chrome",
        "explorer": "explorer.exe",
        "spotify": "start spotify:", # Protocol handler
        "cmd": "start cmd",
        "terminal": "start powershell",
        "code": "code",
        "vscode": "code"
    }
    
    cmd = app_map.get(app_name.lower())
    
    try:
        if cmd:
            # Use shell=True for 'start' command or protocol handlers
            subprocess.Popen(cmd, shell=True)
            return f"Launched {app_name} ({cmd})"
        else:
            # Try generic start
            subprocess.Popen(f"start {app_name}", shell=True)
            return f"Attempted to launch {app_name} via system shell."
            
    except Exception as e:
        return f"Failed to launch {app_name}: {e}"
        
# Register for discovery
# Tool Definition
tool_definition = {
    "name": "open_application",
    "description": "Opens a desktop application by name (e.g., 'notepad', 'chrome', 'spotify').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app_name": {"type": "STRING", "description": "Name of the application to open."}
        },
        "required": ["app_name"]
    }
}
