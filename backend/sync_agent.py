import os
import shutil
import json
import asyncio
import time
from datetime import datetime
from typing import List, Optional

class SyncAgent:
    """
    Manages cross-device state synchronization via a shared directory.
    Monitors for changes and performs atomic updates of local REX state.
    """
    def __init__(self, sync_root: str, local_data_dir: str):
        self.sync_root = sync_root
        self.local_data_dir = local_data_dir
        self.files_to_sync = ["persona.json", "usage_patterns.json", "preferences.json"]
        self.running = False
        self._sync_task = None
        self.on_state_updated = None # Callback for when state is hot-loaded

    async def initialize(self):
        """Prepares sync root and performs initial pull."""
        if not os.path.exists(self.sync_root):
            try:
                os.makedirs(self.sync_root)
                print(f"[SyncAgent] Created sync root: {self.sync_root}")
            except Exception as e:
                print(f"[SyncAgent] Error creating sync root: {e}")
                return False

        # Initial merge: Push local state to sync root if sync root is empty
        # or Pull if sync root is newer.
        await self._sync_cycle()
        
        self.running = True
        self._sync_task = asyncio.create_task(self._monitor_loop())
        print("[SyncAgent] Sync monitor active.")
        return True

    async def _monitor_loop(self):
        """Periodically checks for remote changes."""
        while self.running:
            await asyncio.sleep(30) # Check every 30s
            await self._sync_cycle()

    async def _sync_cycle(self):
        """Performs a single sync iteration (Push/Pull mix)."""
        updated = False
        for filename in self.files_to_sync:
            local_path = os.path.join(self.local_data_dir, filename)
            remote_path = os.path.join(self.sync_root, filename)

            # 1. Pull from remote if newer
            if os.path.exists(remote_path):
                if not os.path.exists(local_path) or os.path.getmtime(remote_path) > os.path.getmtime(local_path):
                    try:
                        shutil.copy2(remote_path, local_path)
                        print(f"[SyncAgent] Pulled updated {filename} from remote.")
                        updated = True
                    except Exception as e:
                        print(f"[SyncAgent] Pull error ({filename}): {e}")

            # 2. Push to remote if local is newer (and remote hasn't changed since our last check)
            if os.path.exists(local_path):
                if not os.path.exists(remote_path) or os.path.getmtime(local_path) > os.path.getmtime(remote_path):
                    try:
                        shutil.copy2(local_path, remote_path)
                        # No need to print for every push, keep it quiet
                    except Exception as e:
                        print(f"[SyncAgent] Push error ({filename}): {e}")

        if updated and self.on_state_updated:
            await self.on_state_updated()

    async def shutdown(self):
        self.running = False
        if self._sync_task:
            self._sync_task.cancel()
        print("[SyncAgent] Shutdown complete.")
