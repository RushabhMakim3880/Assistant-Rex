import asyncio
import aiohttp
import time
import os

class LifestyleAgent:
    """
    Provides real-world utility features like Weather, News, and Currency.
    Designed to supplement the StockAgent and enhance R.E.X's daily utility.
    """
    def __init__(self, web_agent=None):
        self.web_agent = web_agent
        self.currency_cache = {}
        self.last_cache_update = 0

    async def get_weather(self, location="Mumbai"):
        """Fetches weather info from wttr.in."""
        try:
            url = f"https://wttr.in/{location}?format=j1"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        current = data['current_condition'][0]
                        temp = current['temp_C']
                        desc = current['weatherDesc'][0]['value']
                        humidity = current['humidity']
                        
                        # Get forecast for today
                        forecast = data['weather'][0]['hourly'][4] # Approx mid-day
                        high = data['weather'][0]['maxtempC']
                        low = data['weather'][0]['mintempC']
                        
                        return {
                            "location": location,
                            "temp": f"{temp}°C",
                            "condition": desc,
                            "humidity": f"{humidity}%",
                            "high": f"{high}°C",
                            "low": f"{low}°C",
                            "summary": f"In {location}, it's currently {temp}°C and {desc}. Humidity is at {humidity}%. High today: {high}°C, Low: {low}°C."
                        }
                    else:
                        return {"error": f"Weather service returned status {response.status}"}
        except Exception as e:
            return {"error": str(e)}

    async def get_top_news(self, topic="general"):
        """Fetches top news highlights using the WebAgent."""
        if not self.web_agent:
            return {"error": "WebAgent not available for news fetching."}
        
        query = f"latest {topic} news headlines"
        print(f"[LifestyleAgent] Fetching news for: {topic}")
        
        try:
            # We use the web_agent's search capability
            results = await self.web_agent.search(query)
            # The web_agent returns a list of results with title, snippet, link
            
            if not results:
                return {"error": "No news results found."}
            
            news_items = []
            for res in results[:5]: # Take top 5
                news_items.append({
                    "title": res.get("title", ""),
                    "snippet": res.get("snippet", ""),
                    "link": res.get("link", "")
                })
            
            summary = f"Sir, here are the top headlines for {topic}:\n\n"
            for i, item in enumerate(news_items):
                summary += f"{i+1}. {item['title']} - {item['snippet'][:100]}...\n"
                
            return {
                "topic": topic,
                "items": news_items,
                "summary": summary
            }
        except Exception as e:
            return {"error": str(e)}

    async def convert_currency(self, amount, from_curr="USD", to_curr="INR"):
        """Real-time exchange rates."""
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()
        
        # Check cache (1 hour expiry)
        now = time.time()
        if from_curr in self.currency_cache and (now - self.last_cache_update) < 3600:
            rates = self.currency_cache[from_curr]
        else:
            try:
                url = f"https://api.exchangerate-api.com/v4/latest/{from_curr}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            rates = data['rates']
                            self.currency_cache[from_curr] = rates
                            self.last_cache_update = now
                        else:
                            return {"error": f"Currency service status {response.status}"}
            except Exception as e:
                return {"error": str(e)}
        
        if to_curr in rates:
            rate = rates[to_curr]
            result = float(amount) * rate
            return {
                "from": from_curr,
                "to": to_curr,
                "amount": amount,
                "result": round(result, 2),
                "rate": rate,
                "summary": f"{amount} {from_curr} is approximately {round(result, 2)} {to_curr} (Rate: {rate})."
            }
        else:
            return {"error": f"Target currency {to_curr} not found."}

    async def track_package(self, tracking_id):
        """Attempts to track a package via web search."""
        if not self.web_agent:
            return {"error": "WebAgent not available for tracking."}
        
        # Simple heuristic to identify carrier if possible, or just search
        # Carriers often have distinct patterns
        query = f"package tracking {tracking_id}"
        
        try:
            results = await self.web_agent.search(query)
            if not results:
                return {"error": "No tracking info found on the web."}
            
            # Extract top snippet which often contains the status directly on Google
            snippet = results[0].get("snippet", "No detailed status available.")
            
            return {
                "tracking_id": tracking_id,
                "status_snippet": snippet,
                "source": results[0].get("link", ""),
                "summary": f"Tracking information for {tracking_id}: {snippet}"
            }
        except Exception as e:
            return {"error": str(e)}

    async def set_reminder(self, message, delay_minutes, on_trigger=None):
        """Sets a timed reminder."""
        print(f"[LifestyleAgent] Setting reminder: '{message}' in {delay_minutes} mins")
        
        async def _waiter():
            await asyncio.sleep(delay_minutes * 60)
            print(f"[LifestyleAgent] TRIGGERING REMINDER: {message}")
            if on_trigger:
                if asyncio.iscoroutinefunction(on_trigger):
                    await on_trigger(message)
                else:
                    on_trigger(message)
        
        asyncio.create_task(_waiter())
        return f"Sir, I've set a reminder for '{message}' in {delay_minutes} minutes."

# Tool Definitions for Gemini
lifestyle_tools = [
    {
        "name": "get_weather_info",
        "description": "Get current weather and forecast for any city.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "The city name (e.g., Mumbai, London)."}
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_daily_news",
        "description": "Get the top headlines and summaries for a specific topic or general news.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "The news topic (e.g., SpaceX, Technology, Sports, World)."}
            }
        }
    },
    {
        "name": "convert_currency",
        "description": "Convert an amount from one currency to another using real-time exchange rates.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "The value to convert."},
                "from_curr": {"type": "string", "description": "The source currency code (e.g., USD, EUR, GBP)."},
                "to_curr": {"type": "string", "description": "The target currency code (e.g., INR, JPY)."}
            },
            "required": ["amount", "from_curr", "to_curr"]
        }
    },
    {
        "name": "track_logistics",
        "description": "Track a package or shipment status using its tracking number.",
        "parameters": {
            "type": "object",
            "properties": {
                "tracking_id": {"type": "string", "description": "The tracking number of the shipment."}
            },
            "required": ["tracking_id"]
        }
    },
    {
        "name": "set_personal_reminder",
        "description": "Set a reminder for a specific message after a delay in minutes.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The reminder message."},
                "delay_minutes": {"type": "number", "description": "How many minutes from now to trigger the reminder."}
            },
            "required": ["message", "delay_minutes"]
        }
    }
]
