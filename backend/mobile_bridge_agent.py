import os
import asyncio
import aiohttp
import json
from typing import Optional

class MobileBridgeAgent:
    """
    Connects REX to the user's mobile device via Telegram.
    Provides push notifications for long-running tasks and remote status checks.
    """
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None, service_manager=None):
        # Tokens should ideally be set in environment variables or preferences
        self.token = token or os.getenv("REX_TELEGRAM_TOKEN")
        self.chat_id = chat_id or os.getenv("REX_TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.token}" if self.token else None
        self.session = None
        self.service_manager = service_manager
        self.running = False
        self.last_update_id = 0
        self._poll_task = None

    async def initialize(self):
        """Initializes the aiohttp session and starts polling."""
        if not self.token or not self.chat_id:
            print("[MobileBridgeAgent] Telegram Token/ChatID missing. Mobile notifications disabled.")
            return False
        
        self.session = aiohttp.ClientSession()
        self.running = True
        self._poll_task = asyncio.create_task(self._poll_updates())
        print(f"[MobileBridgeAgent] Two-way bridge active for ChatID: {self.chat_id}")
        return True

    async def _poll_updates(self):
        """Long-polling for incoming Telegram messages."""
        while self.running:
            try:
                if not self.api_url or not self.session:
                    await asyncio.sleep(5)
                    continue

                params = {"offset": self.last_update_id + 1, "timeout": 30}
                async with self.session.get(f"{self.api_url}/getUpdates", params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for update in data.get("result", []):
                            self.last_update_id = update["update_id"]
                            if "message" in update:
                                await self._handle_message(update["message"])
                    else:
                        await asyncio.sleep(5)
            except Exception as e:
                print(f"[MobileBridgeAgent] Polling error: {e}")
                await asyncio.sleep(10)

    async def _handle_message(self, message):
        """Processes incoming messages and security gating."""
        sender_id = str(message.get("from", {}).get("id", ""))
        text = message.get("text", "")

        if sender_id != self.chat_id:
            print(f"[MobileBridgeAgent] Unauthorized access attempt from {sender_id}")
            return

        print(f"[MobileBridgeAgent] Received from mobile: {text}")

        # Command Dispatcher
        if text.startswith("/"):
            await self._handle_command(text)
        else:
            # Basic natural language passthrough to REX
            await self._process_generic_intent(text)

    async def _handle_command(self, text):
        """Processes specialized commands."""
        cmd = text.split()[0].lower()
        
        if cmd == "/status":
            system = await self.service_manager.get_service("system")
            if system:
                stats = system.get_stats()
                # Simplified status for mobile
                report = f"🌡 CPU: {stats.get('cpu_temp', 'N/A')}°C\n"
                report += f"📊 RAM: {stats.get('memory', {}).get('percent', 'N/A')}%\n"
                report += f"📍 Location: {stats.get('location', {}).get('city', 'Unknown')}"
                await self.send_notification(report)
            else:
                await self.send_notification("SystemAgent not available.")

        elif cmd == "/tasks":
            # List shadow tasks
            shadow = await self.service_manager.get_service("shadow")
            if shadow:
                tasks = shadow.running_processes
                if not tasks:
                    await self.send_notification("No active background tasks.")
                else:
                    msg = f"🛰 Active Shadow Tasks ({len(tasks)}):\n"
                    for idx, p in enumerate(tasks):
                        msg += f"{idx+1}. PID {p.pid} - Active\n"
                    await self.send_notification(msg)
            else:
                await self.send_notification("ShadowAgent not available.")
        
        elif cmd == "/stop":
            # Simple emergency stop
            await self.send_notification("Stopping all active background processes...")
            shadow = await self.service_manager.get_service("shadow")
            if shadow:
                await shadow.shutdown()
                await shadow.initialize() # Restart it empty
        
        else:
            await self.send_notification(f"Unknown command: {cmd}\nTry /status or /tasks")

    async def _process_generic_intent(self, text):
        """Routes text to REX for full agentic processing."""
        # This requires the rex_instance to be accessible. 
        # We can trigger it via the service manager if rex is registered, 
        # OR via a callback set during server initialization.
        print(f"[MobileBridgeAgent] Routing intent to REX: {text}")
        
        # For now, we'll try to find the 'rex' service if it exists
        # Or notify the user we are processing.
        await self.send_notification(f"Processing command: \"{text}\"...")
        
        # Implementation depends on how Rex is exposed (usually not a service in ServiceManager yet)
        # We might need to add a hook in server.py
        if hasattr(self, 'on_user_intent'):
            await self.on_user_intent(text)
        else:
            await self.send_notification("REX Intelligence link not yet initialized for two-way.")

    async def send_notification(self, message: str, silent: bool = False):
        """Sends a push notification to the user's phone."""
        if not self.session or not self.api_url:
            return False

        try:
            payload = {
                "chat_id": self.chat_id,
                "text": f"🤖 *R.E.X. MESSAGE*\n\n{message}",
                "parse_mode": "Markdown",
                "disable_notification": silent
            }
            async with self.session.post(f"{self.api_url}/sendMessage", json=payload) as resp:
                if resp.status == 200:
                    return True
                else:
                    err_data = await resp.text()
                    print(f"[MobileBridgeAgent] Telegram Error: {err_data}")
                    return False
        except Exception as e:
            print(f"[MobileBridgeAgent] Send error: {e}")
            return False

    async def run_task(self, data):
        """Polymorphic entry point for ToolDispatcher."""
        message = data.get("message")
        if not message:
            return {"error": "No message provided for notification."}
        
        success = await self.send_notification(message)
        return {"status": "Notified user" if success else "Notification failed"}

    async def shutdown(self):
        self.running = False
        if self._poll_task:
            self._poll_task.cancel()
        if self.session:
            await self.session.close()
            self.session = None
