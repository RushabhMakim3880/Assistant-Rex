import os
import json
import sqlite3
import numpy as np
from pathlib import Path
from google import genai
from google.genai import types

class SemanticSearchAgent:
    """
    Agent for semantic search within local project files.
    Uses Gemini 'text-embedding-004' for generating embeddings
    and SQLite for storage and retrieval.
    """
    def __init__(self, api_key: str, db_path: str = "semantic_search.db"):
        self.api_key = api_key
        self.db_path = db_path
        self.client = genai.Client(api_key=api_key)
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database for storing file embeddings."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS file_embeddings
                     (path TEXT PRIMARY KEY,
                      project TEXT,
                      content TEXT,
                      embedding BLOB,
                      last_modified REAL)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_project ON file_embeddings(project)''')
        
        # New: Interaction History for LTM
        c.execute('''CREATE TABLE IF NOT EXISTS interaction_history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp REAL,
                      query TEXT,
                      tool_used TEXT,
                      result TEXT,
                      embedding BLOB,
                      user_feedback TEXT)''')
        conn.commit()
        conn.close()

    async def get_embedding(self, text: str):
        """Generates an embedding for the given text using Gemini."""
        try:
            # text-embedding-004 is current standard
            result = self.client.models.embed_content(
                model="models/text-embedding-004",
                content=text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            return result.embeddings[0].values
        except Exception as e:
            print(f"[SemanticSearch] Embedding error: {e}")
            return None

    async def index_project(self, project_name: str, project_path: str):
        """Indexes all supported text files in the project."""
        print(f"[SemanticSearch] Indexing project: {project_name} at {project_path}")
        path = Path(project_path)
        if not path.exists():
            return

        supported_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.md', '.txt', '.css', '.html'}
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        for file_path in path.rglob('*'):
            if file_path.is_file() and file_path.suffix in supported_extensions:
                try:
                    # Skip large files for now
                    if file_path.stat().st_size > 50000:
                        continue
                        
                    mtime = file_path.stat().st_mtime
                    
                    # Check if already indexed and up to date
                    c.execute("SELECT last_modified FROM file_embeddings WHERE path = ?", (str(file_path),))
                    result = c.fetchone()
                    if result and result[0] >= mtime:
                        continue

                    print(f"[SemanticSearch] Processing: {file_path.name}")
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    embedding = await self.get_embedding(content[:8000]) # Limit content for embedding
                    if embedding:
                        # Convert list to float32 blob
                        embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
                        c.execute("""INSERT OR REPLACE INTO file_embeddings 
                                     (path, project, content, embedding, last_modified)
                                     VALUES (?, ?, ?, ?, ?)""",
                                  (str(file_path), project_name, content, embedding_blob, mtime))
                        conn.commit()
                except Exception as e:
                    print(f"[SemanticSearch] Error indexing {file_path}: {e}")

        conn.close()
        print(f"[SemanticSearch] Indexing complete for {project_name}.")

    async def search(self, project_name: str, query: str, top_k: int = 5):
        """Searches for project files conceptually similar to the query."""
        query_embedding = await self.get_embedding(query)
        if not query_embedding:
            return []

        query_vec = np.array(query_embedding, dtype=np.float32)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT path, content, embedding FROM file_embeddings WHERE project = ?", (project_name,))
        rows = c.fetchall()
        conn.close()

        results = []
        for path, content, embedding_blob in rows:
            doc_vec = np.frombuffer(embedding_blob, dtype=np.float32)
            
            # Simple Cosine Similarity
            dot_product = np.dot(query_vec, doc_vec)
            norm_q = np.linalg.norm(query_vec)
            norm_d = np.linalg.norm(doc_vec)
            
            if norm_q > 0 and norm_d > 0:
                score = dot_product / (norm_q * norm_d)
                results.append({
                    "path": path,
                    "name": Path(path).name,
                    "content_snippet": content[:200] + "...",
                    "score": float(score)
                })

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def log_interaction(self, query: str, tool_used: str, result: str):
        """Logs a user-AI interaction and its outcome for future conceptual retrieval."""
        print(f"[SemanticSearch] Logging interaction: {query[:50]}...")
        timestamp = datetime.now().timestamp()
        
        # Combine query and result for embedding context
        context_text = f"User Query: {query}\nTool: {tool_used}\nOutcome: {result}"
        embedding = await self.get_embedding(context_text[:8000])
        
        if embedding:
            embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""INSERT INTO interaction_history 
                         (timestamp, query, tool_used, result, embedding)
                         VALUES (?, ?, ?, ?, ?)""",
                      (timestamp, query, tool_used, result, embedding_blob))
            conn.commit()
            conn.close()

    async def search_interactions(self, query: str, top_k: int = 3):
        """Concepts search through past user interactions."""
        query_embedding = await self.get_embedding(query)
        if not query_embedding:
            return []

        query_vec = np.array(query_embedding, dtype=np.float32)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT query, tool_used, result, embedding FROM interaction_history")
        rows = c.fetchall()
        conn.close()

        results = []
        for q, tool, res, embedding_blob in rows:
            doc_vec = np.frombuffer(embedding_blob, dtype=np.float32)
            dot_product = np.dot(query_vec, doc_vec)
            norm_q = np.linalg.norm(query_vec)
            norm_d = np.linalg.norm(doc_vec)
            
            if norm_q > 0 and norm_d > 0:
                score = dot_product / (norm_q * norm_d)
                results.append({
                    "query": q,
                    "tool": tool,
                    "result": res,
                    "score": float(score)
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

# Tool Definition for Gemini
semantic_search_tools = [
    {
        "name": "search_files",
        "description": "Conceptually searches through the current project's files to find relevant code or information based on a query.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "The search query (e.g. 'How is authentication handled?')"}
            },
            "required": ["query"]
        }
    }
]
