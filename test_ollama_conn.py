import asyncio
import aiohttp

async def test_ollama():
    base_url = "http://127.0.0.1:11434"
    print(f"Testing connection to Ollama at {base_url}...")
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    print(f"SUCCESS: Found {len(models)} models.")
                    for m in models:
                        print(f" - {m['name']}")
                else:
                    print(f"FAILURE: Ollama returned status {response.status}")
    except Exception as e:
        print(f"FAILURE: Could not connect to Ollama: {e}")

if __name__ == "__main__":
    asyncio.run(test_ollama())
