import pytest
import asyncio
from backend.service_manager import ServiceManager
from backend.base_agent import BaseAgent

class MockAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.initialized = False
        self.shutdown_called = False

    async def initialize(self):
        await super().initialize()
        self.initialized = True

    async def shutdown(self):
        await super().shutdown()
        self.shutdown_called = True

@pytest.mark.asyncio
async def test_service_registration_and_init():
    sm = ServiceManager()
    agent = MockAgent()
    await sm.register_service("mock", agent)
    
    assert sm.status["mock"] == "registered"
    
    await sm.initialize_all()
    assert agent.initialized is True
    assert sm.status["mock"] == "running"

@pytest.mark.asyncio
async def test_service_shutdown():
    sm = ServiceManager()
    agent = MockAgent()
    await sm.register_service("mock", agent)
    await sm.initialize_all()
    
    await sm.shutdown_all()
    assert agent.shutdown_called is True
    assert sm.status["mock"] == "stopped"

@pytest.mark.asyncio
async def test_get_service():
    sm = ServiceManager()
    agent = MockAgent()
    await sm.register_service("mock", agent)
    
    retrieved = await sm.get_service("mock")
    assert retrieved == agent
