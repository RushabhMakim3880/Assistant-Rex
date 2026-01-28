import asyncio
import sys
import os

# Add the current directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.workflow_agent import WorkflowAgent
from backend.desktop_agent import DesktopAgent

async def test_notepad_workflow():
    print("Testing Notepad Workflow Implementation...")
    
    desktop = DesktopAgent()
    workflow = WorkflowAgent(desktop)
    
    # Simple Notepad Workflow (Launch -> Type -> Save)
    prompt = "Open Notepad and type 'Hello from R.E.X. Workflow Engine' and save it to d:\\rex_test.txt"
    
    print(f"Executing: {prompt}")
    result = await workflow.execute_workflow(prompt)
    print(f"\nFinal Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_notepad_workflow())
