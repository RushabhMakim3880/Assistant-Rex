import os
import uuid
import json
import shutil
from datetime import datetime
from google import genai
from google.genai import types

class GenerativeUIAgent:
    """
    Agent responsible for synthesizing ephemeral HTML/JS applications.
    Generates single-file dashboards/tools on demand.
    """
    def __init__(self, apps_dir="generated_apps"):
        self.apps_dir = os.path.join(os.path.dirname(__file__), apps_dir)
        if not os.path.exists(self.apps_dir):
            os.makedirs(self.apps_dir)
            
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    async def generate_dashboard(self, prompt, data_context=""):
        """
        Generates a temporary interactive dashboard based on the prompt and data.
        Returns the local URL to access it.
        """
        app_id = str(uuid.uuid4())
        app_path = os.path.join(self.apps_dir, app_id)
        os.makedirs(app_path)
        
        print(f"[GenerativeUIAgent] Synthesizing app {app_id} for: '{prompt}'")
        
        system_instruction = (
            "You are an expert Frontend Developer specializing in single-file ephemeral dashboards. "
            "Your task is to generate a COMPLETE, self-contained HTML file that visualizes the provided data or solves the user's problem. "
            "Rules:\n"
            "1. Use TailwindCSS (via CDN) for styling. Make it look premium, modern, and dark-mode by default.\n"
            "2. Use Chart.js (via CDN) for any graphs.\n"
            "3. Use Vue.js 3 (via CDN) or Vanilla JS for interactivity and logic.\n"
            "4. The output must be ONLY the raw HTML code. Do not include markdown fences ```html.\n"
            "5. The app should be responsive and fill the screen.\n"
            "6. Include a 'Close App' button that closes the window (window.close())."
        )
        
        user_prompt = f"User Request: {prompt}\n\nData Context:\n{data_context}\n\nGenerate the dashboard HTML now."
        
        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                             types.Part.from_text(text=system_instruction), # System prompt as first user part technique or config
                             types.Part.from_text(text=user_prompt)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="text/plain",
                    temperature=0.7
                )
            )
            
            html_content = response.text
            # Strip markdown fences if Gemini adds them despite instructions
            if html_content.startswith("```html"):
                html_content = html_content[7:]
            if html_content.startswith("```"):
                html_content = html_content[3:]
            if html_content.endswith("```"):
                html_content = html_content[:-3]
                
            index_path = os.path.join(app_path, "index.html")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            url = f"http://127.0.0.1:8000/apps/{app_id}/index.html"
            print(f"[GenerativeUIAgent] App deployed at: {url}")
            return url
            
        except Exception as e:
            print(f"[GenerativeUIAgent] Generation failed: {e}")
            return f"Error generating app: {e}"

    async def list_active_apps(self):
        return os.listdir(self.apps_dir)

    async def purge_apps(self):
        shutil.rmtree(self.apps_dir)
        os.makedirs(self.apps_dir)
        return "All ephemeral apps destroyed."
