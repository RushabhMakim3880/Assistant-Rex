import aiohttp
import asyncio
import json
import logging
import subprocess
import os

class OllamaAgent:
    def __init__(self, base_url="http://127.0.0.1:11434"):
        self.base_url = base_url
        self.logger = logging.getLogger("OllamaAgent")
        self.logger.setLevel(logging.INFO)
        self.current_model = None
        self.timeout = aiohttp.ClientTimeout(total=5) # 5 second timeout for all calls

    async def is_running(self):
        """Checks if the Ollama server is responsive."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    return response.status == 200
        except Exception as e:
            self.logger.warning(f"Ollama server not reachable: {e}")
            return False

    async def get_models(self):
        """Lists all available local models."""
        print(f"[OLLAMA] Attempting to fetch models from {self.base_url}/api/tags...")
        self.logger.info(f"Fetching models from {self.base_url}/api/tags")
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    print(f"[OLLAMA] Server responded with status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        print(f"[OLLAMA] Successfully fetched {len(models)} models.")
                        self.logger.info(f"Successfully fetched {len(models)} models.")
                        return models
                    else:
                        print(f"[OLLAMA] [ERR] Ollama returned status {response.status}")
                        self.logger.error(f"Ollama returned status {response.status}")
            return []
        except Exception as e:
            print(f"[OLLAMA] [ERR] Connection failed: {e}")
            self.logger.error(f"Failed to fetch Ollama models: {e}")
            return []

    async def chat(self, prompt, model=None, system_prompt=None):
        """Generates a response from the local LLM."""
        target_model = model or self.current_model
        if not target_model:
            # Try to get the first available model if none specified
            models = await self.get_models()
            if models:
                target_model = models[0]['name']
            else:
                return {"error": "No Ollama models found. Please pull a model first (e.g., 'ollama pull llama3')."}

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False
        }
        
        if system_prompt:
            payload["system"] = system_prompt

        self.logger.info(f"Ollama generating response using model: {target_model}")
        try:
            # Chat can take longer than 5 seconds for complex prompts
            chat_timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=chat_timeout) as session:
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"Ollama error: {response.status}"}
        except Exception as e:
            self.logger.error(f"Ollama chat failed: {e}")
            return {"error": f"Ollama connection failed: {str(e)}"}

    async def stream_chat(self, prompt, model=None, system_prompt=None, callback=None):
        """Streams a response from the local LLM."""
        target_model = model or self.current_model
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": True
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            # Streaming can take longer
            stream_timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=stream_timeout) as session:
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    async for line in response.content:
                        if line:
                            chunk = json.loads(line)
                            if callback:
                                await callback(chunk)
                            if chunk.get("done"):
                                break
        except Exception as e:
            self.logger.error(f"Ollama stream failed: {e}")
            if callback:
                await callback({"error": str(e)})
