import asyncio
import os
import time
import json
from datetime import datetime
from base_agent import BaseAgent

class SafetyAgent(BaseAgent):
    """
    The Safety Orchestrator for REX.
    Handles emergency shutdowns (Kill-Switch) and maintains the Security Audit Log.
    """
    def __init__(self, log_path="security_audit.log"):
        super().__init__()
        self.log_path = os.path.join(os.path.dirname(__file__), log_path)
        self.active_tasks = set()
        self.child_processes = []

    async def initialize(self):
        await super().initialize()
        await self.log_event("SYSTEM_BOOT", "SafetyAgent initialized", severity="INFO")

    async def log_event(self, event_type, details, severity="INFO", agent_name="SYSTEM"):
        """Records a security-relevant event to the audit log."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "agent": agent_name,
            "severity": severity,
            "details": details
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[SafetyAgent] Failed to write audit log: {e}")

    async def trigger_kill_switch(self):
        """
        Emergency Shutdown:
        1. Cancels all tracked asyncio tasks.
        2. Terminates any registered child processes.
        3. Logs the panic event.
        """
        await self.log_event("EMERGENCY_KILL", "User triggered global kill-switch", severity="CRITICAL")
        print("\n[SAFETY] 🛑 TRIGGERING GLOBAL KILL-SWITCH...")
        
        # Cancel tasks
        for task in self.active_tasks:
            if not task.done():
                task.cancel()
        
        # Kill processes
        import subprocess
        for proc in self.child_processes:
            try:
                if hasattr(proc, 'terminate'):
                    proc.terminate()
                elif isinstance(proc, int):
                    # If we only have PID
                    os.kill(proc, 9)
            except:
                pass
        
        self.active_tasks.clear()
        self.child_processes.clear()
        print("[SAFETY] 🔒 System Hardened. All autonomous actions stopped.")
        return "System Locked. Emergency Stop Complete."

    def track_task(self, task):
        self.active_tasks.add(task)
        task.add_done_callback(lambda t: self.active_tasks.discard(t))

    def track_process(self, proc):
        self.child_processes.append(proc)
