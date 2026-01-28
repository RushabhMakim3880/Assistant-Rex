import asyncio
import sqlite3
import time
import base64
import os
from datetime import datetime
from google import genai
from google.genai import types

class VisualMemoryAgent:
    """
    Agent responsible for maintaining a 'Visual Memory' of the user's screen.
    Periodically captures screenshots, performs OCR/Description via Gemini,
    and stores them in a searchable SQLite database.
    """
    def __init__(self, desktop_agent, db_path="visual_memory.db"):
        self.desktop = desktop_agent
        self.db_path = db_path
        self.running = False
        self.capture_task = None
        self.history_buffer = [] # Stores recent frame metadata
        self.backoff_until = 0 # Timestamp to wait until for 429 errors

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='visual_memory'")
        if not c.fetchone():
             c.execute('''CREATE TABLE visual_memory
                     (timestamp REAL, image_path TEXT, window_title TEXT, content TEXT)''')
             c.execute('''CREATE INDEX idx_timestamp ON visual_memory(timestamp)''')
        else:
            # Check for missing columns (Schema Migration)
            c.execute("PRAGMA table_info(visual_memory)")
            columns = [info[1] for info in c.fetchall()]
            
            if "image_path" not in columns:
                print("[VisualMemoryAgent] Migrating DB: Adding image_path column")
                c.execute("ALTER TABLE visual_memory ADD COLUMN image_path TEXT")
                
            if "window_title" not in columns:
                print("[VisualMemoryAgent] Migrating DB: Adding window_title column")
                c.execute("ALTER TABLE visual_memory ADD COLUMN window_title TEXT")

        conn.commit()
        conn.close()

    async def initialize(self, sio=None):
        self.running = True
        self.sio = sio # Socket.IO instance for alerts
        self.capture_task = asyncio.create_task(self._background_capture_loop())
        print(f"[VisualMemoryAgent] Initialized. Background loop running every {self.interval}s.")

    async def _background_capture_loop(self):
        # Wait a bit on startup
        await asyncio.sleep(10)
        while self.running:
            try:
                if time.time() < self.backoff_until:
                    await asyncio.sleep(10)
                    continue

                await self.record_current_screen()
                
                # Active Visual Reasoning: Check for errors every few frames
                if len(self.history_buffer) > 0:
                     await self._analyze_for_errors()
                
                await asyncio.sleep(30) # Increased to 30s to save free tier quota
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[VisualMemoryAgent] Loop error: {e}")
                await asyncio.sleep(10)

    async def _analyze_for_errors(self):
        """Scans recent indexed content for critical failures."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Check last 3 frames
            c.execute("SELECT content FROM visual_memory ORDER BY timestamp DESC LIMIT 3")
            rows = c.fetchall()
            conn.close()

            error_keywords = ["error", "failed", "exception", "timeout", "critical", "panic", "404", "500"]
            for row in rows:
                content = (row[0] or "").lower()
                for kw in error_keywords:
                    if kw in content:
                        print(f"[VisualMemoryAgent] Proactive Alert Triggered: Detected '{kw}' on screen.")
                        if self.sio:
                            await self.sio.emit('proactive_alert', {
                                "type": "visual_error",
                                "message": f"I noticed a '{kw}' state on your screen. Want me to investigate?",
                                "keyword": kw
                            })
                        return # Only alert once per cycle
        except Exception as e:
            print(f"[VisualMemoryAgent] Error analysis failed: {e}")

    async def record_current_screen(self):
        """Captures screen, saves to buffer, and performs lightweight indexing."""
        try:
            timestamp = time.time()
            # 1. Capture Screenshot
            screenshot = await self.desktop_agent.get_screenshot()
            if not screenshot: return

            # 2. Get Window Info (Lightweight Indexing)
            window_info = await self.desktop_agent.get_active_window_info()
            window_title = window_info.get("title", "Unknown") if window_info else "Unknown"

            # 3. Save Image to Disk
            filename = f"frame_{int(timestamp)}.jpg"
            filepath = os.path.join(self.buffer_dir, filename)
            
            # Decode and Save
            # We need to save as efficient JPG
            # The agent.get_screenshot return PNG b64. 
            # Ideally we optimized this in desktop agent but we can convert here.
            img_data = base64.b64decode(screenshot["data"])
            
            # Use threading for I/O
            await asyncio.to_thread(self._save_image, filepath, img_data)

            # 4. Perform Visual Indexing (Real implementation)
            content = "Indexing failed"
            try:
                # Limit frequency of full OCR to save tokens/rate limits
                # We can do full analysis every N frames or if window changes
                analysis_prompt = """
                Extract all visible text and describe the main activity on the screen.
                Focus on:
                - Application names
                - Web page titles/URLs
                - Keywords from documents
                - Buttons or active UI elements
                Return a concise summary for searching later.
                """
                
                # Convert bytes to PIL for Gemini consumption or use raw bytes if supported
                # client.models.generate_content supports bytes directly with mime_type
                from google.genai import types
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model="gemini-2.0-flash-exp",
                    contents=[
                        analysis_prompt,
                        types.Part.from_bytes(data=img_data, mime_type="image/jpeg")
                    ]
                )
                if response and response.text:
                    content = response.text.strip()
                    print(f"[VisualMemoryAgent] Indexed Frame: {window_title} - {content[:50]}...")
            except Exception as e:
                print(f"[VisualMemoryAgent] Indexing error: {e}")
                if "RESOURCE_EXHAUSTED" in str(e).upper() or "429" in str(e):
                    # Backoff for 60s
                    print("[VisualMemoryAgent] 429 Detected. Backing off for 60s...")
                    self.backoff_until = time.time() + 60

            c.execute("INSERT INTO visual_memory (timestamp, image_path, window_title, content) VALUES (?, ?, ?, ?)",
                      (timestamp, filepath, window_title, content))
            conn.commit()
            conn.close()
            
            # Maintain history_buffer
            self.history_buffer.append({"ts": timestamp, "title": window_title, "content": content})
            if len(self.history_buffer) > 10:
                self.history_buffer.pop(0)

            # 6. Cleanup Old Files
            await self._cleanup()
            
        except Exception as e:
            print(f"[VisualMemoryAgent] Capture error: {e}")

    def _save_image(self, filepath, data):
        with open(filepath, "wb") as f:
            f.write(data)

    async def _cleanup(self):
        """Removes entries older than retention period."""
        cutoff = time.time() - (self.retention_hours * 3600)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get files to delete
        c.execute("SELECT image_path FROM visual_memory WHERE timestamp < ?", (cutoff,))
        rows = c.fetchall()
        
        for row in rows:
            try:
                if os.path.exists(row[0]):
                    os.remove(row[0])
            except: pass
            
        c.execute("DELETE FROM visual_memory WHERE timestamp < ?", (cutoff,))
        conn.commit()
        conn.close()

    async def query_memory(self, query, time_range_hours=24):
        """
        Search for content in memory within a certain time window.
        """
        start_time = time.time() - (time_range_hours * 3600)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Simple LIKE search for now
        # Search window titles OR content (if indexed)
        c.execute("SELECT timestamp, image_path, window_title, content FROM visual_memory WHERE timestamp > ? AND (window_title LIKE ? OR content LIKE ?) ORDER BY timestamp DESC LIMIT 10",
                  (start_time, f"%{query}%", f"%{query}%"))
        results = c.fetchall()
        conn.close()
        
        if not results:
            return f"I couldn't find anything related to '{query}' in my visual memory (last {time_range_hours}h). Searched window titles."
        
        memos = []
        for ts, img_path, title, content in results:
            dt = datetime.fromtimestamp(ts).strftime('%I:%M:%S %p')
            # If content is empty, maybe we should offer to analyze it?
            # For now just list it.
            snippet = content[:200] if content else "(Visual Frame)"
            memos.append(f"[{dt}] Window: '{title}' - {snippet}\n   Path: {img_path}")
            
        return "\n".join(memos) + "\n\nTip: I can analyze specific frames if you ask."

    async def shutdown(self):
        self.running = False
        if self.capture_task:
            self.capture_task.cancel()
        print("[VisualMemoryAgent] Shutdown complete.")
