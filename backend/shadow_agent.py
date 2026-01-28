import os
import ctypes
import subprocess
import threading
import asyncio
import time
from typing import Optional

# Windows API Constants
DESKTOP_CREATEWINDOW = 0x0002
DESKTOP_ENUMERATE = 0x0040
DESKTOP_WRITEOBJECTS = 0x0080
DESKTOP_READOBJECTS = 0x0001
DESKTOP_SWITCHDESKTOP = 0x0100
GENERIC_ALL = 0x10000000

class ShadowAgent:
    """
    Manages an isolated Windows Desktop for R.E.X. autonomous tasks.
    Allows running UI-heavy tools without interrupting the user's focus.
    """
    def __init__(self, desktop_name: str = "REX_Shadow"):
        self.desktop_name = desktop_name
        self.h_desktop = None
        self.h_original_desktop = None
        self.running_processes = []
        self.sio = None
        self.mobile_bridge = None
        self._lock = threading.Lock()

    async def initialize(self):
        """Creates the virtual desktop if on Windows."""
        if os.name != "nt":
            print("[ShadowAgent] Shadow Desktop only supported on Windows.")
            return False

        try:
            # Create a new desktop
            # CreateDesktopW(lpszDesktop, lpszDevice, pDevMode, dwFlags, dwDesiredAccess, lpsa)
            self.h_desktop = ctypes.windll.user32.CreateDesktopW(
                self.desktop_name, None, None, 0, GENERIC_ALL, None
            )
            
            if not self.h_desktop:
                print(f"[ShadowAgent] Failed to create desktop '{self.desktop_name}': {ctypes.GetLastError()}")
                return False
            
            print(f"[ShadowAgent] Created virtual desktop: {self.desktop_name}")
            return True
        except Exception as e:
            print(f"[ShadowAgent] Initialization error: {e}")
            return False

    def run_in_shadow(self, command: str, cwd: Optional[str] = None):
        """
        Launches a process within the shadow desktop.
        Note: This uses a thread to handle the desktop context switching.
        """
        def _execute():
            # Get current thread's desktop
            h_thread_orig = ctypes.windll.user32.GetThreadDesktop(ctypes.windll.kernel32.GetCurrentThreadId())
            
            # Switch thread to shadow desktop
            if not ctypes.windll.user32.SetThreadDesktop(self.h_desktop):
                print(f"[ShadowAgent] Failed to set thread desktop: {ctypes.GetLastError()}")
                return

            print(f"[ShadowAgent] Launching on {self.desktop_name}: {command}")
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.lpDesktop = self.desktop_name
            
            process = subprocess.Popen(
                command, 
                shell=True, 
                cwd=cwd, 
                startupinfo=startupinfo
            )
            
            with self._lock:
                self.running_processes.append(process)
            
            process.wait()
            
            with self._lock:
                if process in self.running_processes:
                    self.running_processes.remove(process)
            
            print(f"[ShadowAgent] Process completed on {self.desktop_name}: {command}")
            self._broadcast_tasks()
            
            if self.mobile_bridge:
                asyncio.create_task(self.mobile_bridge.send_notification(
                    f"✅ Shadow Task Finished:\n`{command}`"
                ))

        threading.Thread(target=_execute, daemon=True).start()
        self._broadcast_tasks()

    def _broadcast_tasks(self):
        """Emits the current list of background tasks to the frontend."""
        if not self.sio:
            return
            
        with self._lock:
            tasks = [{"pid": p.pid, "name": "Shadow Process"} for p in self.running_processes]
            
        # Emit via background task safely
        asyncio.create_task(self.sio.emit('shadow_tasks_update', tasks))

    async def run_task(self, data):
        """Polymorphic entry point for ToolDispatcher."""
        command = data.get("command")
        if not command:
            return {"error": "No command provided for shadow execution."}
        
        self.run_in_shadow(command, cwd=data.get("cwd"))
        return {"status": "Task spawned in shadow desktop", "desktop": self.desktop_name}

    async def shutdown(self):
        """Cleans up processes and closes the desktop."""
        print("[ShadowAgent] Shutting down...")
        with self._lock:
            for p in self.running_processes:
                try:
                    p.terminate()
                except:
                    pass
        
        # Closing a desktop is tricky if windows are still open
        # We'll just release the handle for now
        if self.h_desktop:
            ctypes.windll.user32.CloseDesktop(self.h_desktop)
            self.h_desktop = None
