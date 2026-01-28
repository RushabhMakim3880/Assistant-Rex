import asyncio
import json
import os
from app_context_agent import AppContextAgent
from ui_executor_agent import UIExecutorAgent
import pathlib

class WorkflowAgent:
    """
    Orchestrates multi-step application workflows.
    Bridges the gap between 'Launch App' and 'Complete Work'.
    """
    def __init__(self, desktop_agent, gemini_client=None, pattern_agent=None):
        self.desktop = desktop_agent
        self.client = gemini_client
        self.pattern = pattern_agent
        self.context = AppContextAgent()
        self.executor = UIExecutorAgent(self.context)
        self.history = []

    async def execute_workflow(self, intent_prompt):
        """
        Main entry point for multi-step tasks.
        1. Plans steps using LLM or hardcoded logic.
        2. Executes steps with verification.
        """
        print(f"[WorkflowAgent] Planning workflow for: '{intent_prompt}'")
        
        # Planning Step
        steps = await self._plan_workflow(intent_prompt)
        if not steps:
            return "Failed to generate workflow plan."

        # Execution Loop
        results = []
        for i, step in enumerate(steps):
            target = step.get('target') or step.get('content') or step.get('path') or ""
            print(f"[WorkflowAgent] Step {i+1}/{len(steps)}: {step['action']} -> {target}")
            
            success = await self._run_step(step)
            results.append({"step": i+1, "action": step['action'], "success": success})
            
            if not success:
                print(f"[WorkflowAgent] Step {i+1} failed. Triggering recovery...")
                # Basic recovery: retry once or explain failure
                if not await self._run_step(step):
                    return f"Workflow halted at step {i+1} ({step['action']}). Please assist R.E.X."

        # Log success for pattern learning
        if self.pattern:
            asyncio.create_task(self.pattern.log_interaction(intent_prompt, "workflow", True))

        return f"Workflow completed successfully: {len(steps)} steps executed."

    async def _plan_workflow(self, prompt):
        """
        Uses Gemini to translate intent into a JSON step array.
        """
        # We no longer use hardcoded logic for Notepad or VS Code to ensure maximum flexibility.
        # But we can keep them as fast fallbacks if 'fast_mode' or similar is requested.
        pass

        if not self.client:
            return None

        # LLM based planning for complex requests
        planning_prompt = f"""
        Translate the user's intent into a series of executable steps for a Windows desktop.
        User Intent: "{prompt}"
        
        Available Actions:
        - launch (target: app name)
        - wait (target: app name substring)
        - type (content: text to write)
        - shortcut (keys: list of keys like ['ctrl', 'n'])
        - save (path: file path)
        
        Return a JSON array of steps. Example:
        [
            {{"action": "launch", "target": "notepad"}},
            {{"action": "wait", "target": "notepad"}},
            {{"action": "type", "content": "Hello World"}},
            {{"action": "save", "path": "D:\\test.txt"}}
        ]
        """
        
        try:
            from google.genai import types
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.0-flash-exp",
                contents=planning_prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"[WorkflowAgent] Planning failed: {e}")
            return None

    async def _run_step(self, step):
        """Executes a single workflow step with verification."""
        action = step['action']
        
        try:
            if action == "launch":
                # Check if already running/focused
                if self.context.is_window_focused(step['target']):
                    print(f"[WorkflowAgent] {step['target']} already focused. Skipping launch.")
                    return True
                return await self.desktop.launch_app(step['target'])
            
            elif action == "wait":
                return await self.context.wait_for_app_ready(step['target'])
            
            elif action == "type":
                content = step.get('content', '')
                return await self.executor.type_into_editor(content, app_context=step.get('target'))
            
            elif action == "shortcut":
                return await self.executor.trigger_shortcut(*step['keys'])
            
            elif action == "save":
                return await self.executor.save_file(step['path'])
                
            return False
        except Exception as e:
            print(f"[WorkflowAgent] Step execution error: {e}")
            return False

    def _extract_path(self, prompt):
        """Simple heuristic to find a path in the prompt."""
        import re
        # Prioritize Windows paths (D:\...) then Unix-style paths starting with /
        # Avoid matching random dots like in "R.E.X."
        match = re.search(r'([A-Za-z]:\\[^ ]+|(?<![a-zA-Z\d])[\/][^ ]+|(?<![a-zA-Z\d])[.][\\\/][^ ]+)', prompt)
        return match.group(1) if match else None

    def _analyze_folder(self, path):
        """Scans a folder and generates a requirement summary."""
        import os
        summary = f"Files found in {path}:\n"
        for root, dirs, files in os.walk(path):
            for file in files:
                summary += f"- {file}\n"
        return summary
