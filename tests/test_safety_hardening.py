import pytest
import asyncio
import os
from backend.sandbox_service import SandboxService
from backend.safety_agent import SafetyAgent

@pytest.mark.asyncio
async def test_sandbox_protection():
    # Configure sandbox with a specific project root
    project_root = os.path.abspath("./test_workspace")
    if not os.path.exists(project_root):
        os.makedirs(project_root)
        
    sandbox = SandboxService(allowed_roots=[project_root])
    
    # Safe path
    safe_path = os.path.join(project_root, "test.txt")
    assert sandbox.is_path_safe(safe_path) is True
    
    # Dangerous path
    dangerous_path = "C:/Windows/System32" if os.name == 'nt' else "/etc/shadow"
    assert sandbox.is_path_safe(dangerous_path) is False
    
    with pytest.raises(PermissionError):
        sandbox.validate_path(dangerous_path)

@pytest.mark.asyncio
async def test_kill_switch():
    safety = SafetyAgent()
    
    # Create a long running task
    async def long_task():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            print("Task cancelled successfully")
            raise

    task = asyncio.create_task(long_task())
    safety.track_task(task)
    
    # Trigger kill switch
    await safety.trigger_kill_switch()
    await asyncio.sleep(0.1) # Wait for cancellation to propagate
    
    assert task.cancelled() or task.done()

@pytest.mark.asyncio
async def test_audit_logging():
    log_file = "test_audit.log"
    if os.path.exists(log_file): os.remove(log_file)
    
    safety = SafetyAgent(log_path=log_file)
    await safety.log_event("TEST_EVENT", "This is a test", severity="DEBUG")
    
    # Check if log file exists (it's created on log_event)
    full_log_path = os.path.join(os.path.dirname(safety.log_path), log_file)
    assert os.path.exists(full_log_path)
    
    with open(full_log_path, "r") as f:
        content = f.read()
        assert "TEST_EVENT" in content
        assert "This is a test" in content
    
    if os.path.exists(full_log_path): os.remove(full_log_path)
