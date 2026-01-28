import asyncio
from typing import List, Dict, Any

class MemoryOrchestrator:
    """
    Manages the flow of memory between the ToolDispatcher and the SemanticSearchAgent.
    Provides relevant past context to the LLM before tool execution.
    """
    def __init__(self, semantic_search_agent):
        self.memory = semantic_search_agent
        self.short_term_buffer = [] # Current session highlights

    async def get_relevant_context(self, current_query: str) -> str:
        """Retrieves and formats relevant past interactions for prompt injection."""
        print(f"[MemoryOrchestrator] Retrieving context for: {current_query[:50]}...")
        
        # 1. Search Long-Term Memory
        past_interactions = await self.memory.search_interactions(current_query, top_k=3)
        
        if not past_interactions:
            return ""

        context_header = "\n[RELEVANT PAST CONTEXT]\n"
        context_body = ""
        
        for idx, item in enumerate(past_interactions):
            context_body += f"{idx+1}. Query: {item['query']}\n   Result: {item['result']}\n"
            
        return context_header + context_body + "\n"

    async def commit_to_long_term(self, query: str, tool: str, result: str):
        """Asynchronously logs the interaction to the semantic database."""
        # Add to short term buffer first
        self.short_term_buffer.append({"query": query, "tool": tool, "result": str(result)[:200]})
        if len(self.short_term_buffer) > 5:
            self.short_term_buffer.pop(0)
            
        # Commit to SQL for persistent retrieval
        try:
            await self.memory.log_interaction(query, tool, str(result))
        except Exception as e:
            print(f"[MemoryOrchestrator] Failed to commit to LTM: {e}")

    def get_session_summary(self):
        """Returns a brief summary of recent actions in this session."""
        if not self.short_term_buffer:
            return "No recent actions."
        return "\n".join([f"- {it['tool']}: {it['query']}" for it in self.short_term_buffer])
