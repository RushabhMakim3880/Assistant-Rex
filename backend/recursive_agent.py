import os
import time
import asyncio
import psutil
import json
from datetime import datetime
from typing import Dict, Any, List

class RecursiveAgent:
    """
    The 'Self-Coding' agent. Monitors REX performance and proposes 
    architectural optimizations or minor feature additions.
    """
    def __init__(self, service_manager=None, project_root=None, sio=None):
        self.service_manager = service_manager
        self.project_root = project_root or os.getcwd()
        self.sio = sio
        self.performance_logs = []
        self._monitoring_task = None
        self.running = False

    async def initialize(self):
        """Starts the performance monitoring loop."""
        self.running = True
        self._monitoring_task = asyncio.create_task(self._monitor_performance())
        print("[RecursiveAgent] Self-monitoring active.")

    async def _monitor_performance(self):
        """Tracks CPU and Memory usage of REX agents over time."""
        while self.running:
            try:
                process = psutil.Process(os.getpid())
                # Gather stats for the current process and its children
                stats = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": process.cpu_percent(interval=1.0),
                    "memory_mb": process.memory_info().rss / (1024 * 1024),
                    "thread_count": process.num_threads()
                }
                
                self.performance_logs.append(stats)
                
                # Keep only last 100 logs
                if len(self.performance_logs) > 100:
                    self.performance_logs.pop(0)

                if self.sio:
                    asyncio.create_task(self.sio.emit('performance_stats', stats))

                await asyncio.sleep(60) # Log every minute
            except Exception as e:
                print(f"[RecursiveAgent] Monitoring error: {e}")
                await asyncio.sleep(10)

    async def run_analysis(self):
        """Analyzes logs and identifying potential improvements."""
        if not self.performance_logs:
            return "Not enough data for analysis yet."

        avg_cpu = sum(l['cpu_percent'] for l in self.performance_logs) / len(self.performance_logs)
        peak_mem = max(l['memory_mb'] for l in self.performance_logs)
        
        analysis = f"--- REX Performance Report ---\n"
        analysis += f"Average CPU: {avg_cpu:.2f}%\n"
        analysis += f"Peak Memory: {peak_mem:.2f} MB\n"
        
        if avg_cpu > 15:
            analysis += "Recommendation: Consider offloading heavy tool processing to Shadow Desktop.\n"
        if peak_mem > 500:
            analysis += "Recommendation: Analyze memory leaks in VisualMemoryAgent.\n"
            
        return analysis

    async def propose_self_patch(self, file_path: str):
        """
        Reads a file and suggests a 'cleanliness' or 'efficiency' patch.
        This is a framework for REX to improve itself.
        """
        if not os.path.exists(file_path):
            return {"error": f"File {file_path} not found."}

        # In a real scenario, we'd pass this code to a Gemini model
        # with a prompt like "Find 3 optimizations for this Python file".
        # For now, we return a simulated patch proposal.
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "file": file_path,
            "observation": "Detected non-async I/O in service-heavy loops.",
            "proposed_change": "Refactor local file reads to use threadpool offloading.",
            "impact": "Reduces main loop latency by ~15%."
        }

    async def run_task(self, data):
        """Polymorphic entry point."""
        action = data.get("action", "analyze")
        if action == "analyze":
            return await self.run_analysis()
        elif action == "patch":
            return await self.propose_self_patch(data.get("file_path"))
        return {"error": "Unknown recursive action."}

    async def shutdown(self):
        self.running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
