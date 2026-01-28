import asyncio
from typing import Dict, Any
from memory_orchestrator import MemoryOrchestrator

class ToolDispatcher:
    """
    Central dispatcher for tool execution.
    Handles service lookups, asynchronous execution, and persistent memory logging.
    Now includes a 'Reflexion' cycle for autonomous self-correction.
    """
    def __init__(self, service_manager):
        self.service_manager = service_manager
        self.pending_confirmations = {}
        self.memory = None # Set after service registration

    async def initialize(self):
        # Retrieve semantic search agent for memory
        ss_agent = await self.service_manager.get_service("skills")
        # Actually SemanticSearchAgent is usually separate or integrated
        # For this refactor, we'll try to find it dynamically
        ss_agent = await self.service_manager.get_service("semantic_search")
        if ss_agent:
            self.memory = MemoryOrchestrator(ss_agent)
            print("[ToolDispatcher] Memory Orchestrator initialized.")

    async def dispatch(self, tool_name: str, args: Dict[str, Any], attempt: int = 1):
        """Dispatches a tool call with an autonomous retry loop (Reflexion)."""
        print(f"[ToolDispatcher] Dispatching: {tool_name} (Attempt {attempt})")
        
        result = None
        error = None
        
        try:
            # Mapping logic
            if tool_name == "generate_cad":
                agent = await self.service_manager.get_service("cad")
                result = await agent.generate_prototype(args.get("prompt"))
            
            elif tool_name == "run_web_agent":
                agent = await self.service_manager.get_service("web")
                result = await agent.run_task(args.get("prompt"))
                
            elif tool_name == "cleanup_system":
                agent = await self.service_manager.get_service("system")
                result = await agent.cleanup_system()
            
            elif tool_name == "execute_workflow":
                agent = await self.service_manager.get_service("workflow")
                result = await agent.execute_workflow(args.get("prompt"))
            
            elif tool_name == "shadow_run_task":
                agent = await self.service_manager.get_service("shadow")
                result = await agent.run_task(args)
                
            elif tool_name == "analyze_self_performance":
                agent = await self.service_manager.get_service("recursive")
                result = await agent.run_task(args)

            elif tool_name == "hive_sync":
                agent = await self.service_manager.get_service("sync")
                result = await agent.run_task(args)
                
            elif tool_name == "mobile_notify":
                agent = await self.service_manager.get_service("mobile_bridge")
                result = await agent.run_task(args)
            else:
                error = f"Tool {tool_name} not found."
                print(f"[ToolDispatcher] WARN: {error}")

        except Exception as e:
            error = str(e)
            print(f"[ToolDispatcher] Execution Error: {e}")

        # Reflexion / Self-Correction Cycle
        if (error or (result is None)) and attempt < 3:
            print(f"[ToolDispatcher] Reflexion Triggered: Analyzing failure of {tool_name}...")
            
            # Autonomous Debugging: If it's a CAD or Script error, ask Terminal to help
            if any(kw in str(error).lower() for kw in ["syntax", "error", "failed", "not found"]):
                print(f"[ToolDispatcher] Attempting autonomous repair via Terminal...")
                terminal = await self.service_manager.get_service("terminal")
                if terminal:
                    # In a real scenario, we'd pass the error to an LLM to generate a fix
                    # For now, we simulate the 'Self-Correction' attempt
                    repair_hint = f"Fixing {tool_name} failure: {error}"
                    await terminal.run_command(f"echo 'Self-Correction Log: {repair_hint}'")
            
            await asyncio.sleep(1)
            return await self.dispatch(tool_name, args, attempt + 1)

        # Log to Long-Term Memory
        if self.memory:
            query = args.get("prompt", tool_name)
            outcome = result if not error else f"Error: {error}"
            asyncio.create_task(self.memory.commit_to_long_term(query, tool_name, str(outcome)))

        return result if not error else {"error": error}

    async def relay_task(self, source_agent_name, target_agent_name, data):
        """Allows direct agent-to-agent data transfer."""
        print(f"[ToolDispatcher] Relaying data from {source_agent_name} to {target_agent_name}")
        target = await self.service_manager.get_service(target_agent_name)
        if target:
            # Polymorphic entry point: most agents have 'run_task' or 'execute'
            if hasattr(target, 'run_task'):
                return await target.run_task(data)
            elif hasattr(target, 'execute_workflow'):
                return await target.execute_workflow(data)
        return {"error": f"Target agent {target_agent_name} not found or incompatible."}

    def resolve_confirmation(self, request_id, confirmed):
        if request_id in self.pending_confirmations:
            future = self.pending_confirmations[request_id]
            if not future.done():
                future.set_result(confirmed)
