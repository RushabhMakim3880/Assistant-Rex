import asyncio

class BaseAgent:
    """
    Base class for all REX agents/services.
    Defines the contract for initialization and lifecycle management.
    """
    def __init__(self):
        self.status = "static"

    async def initialize(self):
        """Async initialization logic (e.g., connecting to databases, initializing LLM clients)."""
        self.status = "running"
        pass

    async def shutdown(self):
        """Async cleanup logic (e.g., closing connections, saving state)."""
        self.status = "stopped"
        pass

    def get_status(self):
        return self.status
