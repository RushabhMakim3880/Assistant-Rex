import pytest
import asyncio
import os
from unittest.mock import MagicMock, AsyncMock
from backend.memory_orchestrator import MemoryOrchestrator

@pytest.mark.asyncio
async def test_memory_orchestrator_context():
    # Mock SemanticSearchAgent
    mock_ss = MagicMock()
    mock_ss.search_interactions = AsyncMock(return_value=[
        {"query": "Create a box", "result": "Success: Box created", "score": 0.9}
    ])
    
    orchestrator = MemoryOrchestrator(mock_ss)
    context = await orchestrator.get_relevant_context("Recent boxes")
    
    assert "[RELEVANT PAST CONTEXT]" in context
    assert "Create a box" in context
    assert "Success: Box created" in context

@pytest.mark.asyncio
async def test_memory_orchestrator_logging():
    mock_ss = MagicMock()
    mock_ss.log_interaction = AsyncMock()
    
    orchestrator = MemoryOrchestrator(mock_ss)
    await orchestrator.commit_to_long_term("Test query", "test_tool", "test result")
    
    mock_ss.log_interaction.assert_called_once_with("Test query", "test_tool", "test result")
    assert len(orchestrator.short_term_buffer) == 1
    assert orchestrator.short_term_buffer[0]["query"] == "Test query"
