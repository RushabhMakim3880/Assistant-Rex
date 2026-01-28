import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime

class CrossProjectAgent:
    """
    Learns from past projects to provide contextual suggestions.
    Analyzes project structures, dependencies, and patterns.
    """
    def __init__(self, db_path="cross_project_context.db"):
        self.db_path = os.path.join(os.path.dirname(__file__), db_path)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS projects
                     (name TEXT PRIMARY KEY, 
                      languages TEXT,
                      frameworks TEXT,
                      dependencies TEXT,
                      file_structure TEXT,
                      created_at REAL)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_languages ON projects(languages)''')
        conn.commit()
        conn.close()
    
    async def initialize(self):
        print("[CrossProjectAgent] Initialized and ready.")
    
    async def profile_project(self, project_path):
        """Analyzes a project and stores its profile."""
        try:
            path = Path(project_path)
            if not path.exists():
                return f"Project path {project_path} does not exist."
            
            profile = {
                "name": path.name,
                "languages": self._detect_languages(path),
                "frameworks": self._detect_frameworks(path),
                "dependencies": self._extract_dependencies(path),
                "file_structure": self._analyze_structure(path),
                "created_at": datetime.now().timestamp()
            }
            
            # Store in DB
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""INSERT OR REPLACE INTO projects 
                         (name, languages, frameworks, dependencies, file_structure, created_at)
                         VALUES (?, ?, ?, ?, ?, ?)""",
                      (profile["name"],
                       json.dumps(profile["languages"]),
                       json.dumps(profile["frameworks"]),
                       json.dumps(profile["dependencies"]),
                       json.dumps(profile["file_structure"]),
                       profile["created_at"]))
            conn.commit()
            conn.close()
            
            return f"Project '{profile['name']}' profiled successfully."
        except Exception as e:
            print(f"[CrossProjectAgent] Error profiling project: {e}")
            return f"Failed to profile project: {e}"
    
    def _detect_languages(self, path):
        """Detects programming languages based on file extensions."""
        extensions = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.php': 'PHP',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.c': 'C',
            '.html': 'HTML',
            '.css': 'CSS'
        }
        found = set()
        for file in path.rglob('*'):
            if file.is_file() and file.suffix in extensions:
                found.add(extensions[file.suffix])
        return list(found)
    
    def _detect_frameworks(self, path):
        """Detects frameworks based on config files and imports."""
        frameworks = []
        
        # Check for common framework indicators
        if (path / "package.json").exists():
            try:
                with open(path / "package.json") as f:
                    pkg = json.load(f)
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    if "react" in deps: frameworks.append("React")
                    if "next" in deps: frameworks.append("Next.js")
                    if "express" in deps: frameworks.append("Express")
                    if "vue" in deps: frameworks.append("Vue")
            except: pass
        
        if (path / "requirements.txt").exists():
            try:
                with open(path / "requirements.txt") as f:
                    reqs = f.read().lower()
                    if "fastapi" in reqs: frameworks.append("FastAPI")
                    if "django" in reqs: frameworks.append("Django")
                    if "flask" in reqs: frameworks.append("Flask")
            except: pass
        
        if (path / "pom.xml").exists(): frameworks.append("Maven/Spring")
        if (path / "composer.json").exists(): frameworks.append("Composer/Laravel")
        
        return frameworks
    
    def _extract_dependencies(self, path):
        """Extracts dependencies from package files."""
        deps = []
        
        if (path / "package.json").exists():
            try:
                with open(path / "package.json") as f:
                    pkg = json.load(f)
                    deps.extend(list(pkg.get("dependencies", {}).keys())[:10])
            except: pass
        
        if (path / "requirements.txt").exists():
            try:
                with open(path / "requirements.txt") as f:
                    deps.extend([line.split('==')[0].strip() for line in f.readlines()[:10]])
            except: pass
        
        return deps
    
    def _analyze_structure(self, path):
        """Analyzes top-level directory structure."""
        structure = []
        try:
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    structure.append(f"dir:{item.name}")
                elif item.is_file():
                    structure.append(f"file:{item.name}")
        except: pass
        return structure[:20]  # Limit to 20 items
    
    async def get_similar_projects(self, language=None, framework=None):
        """Finds projects with similar technology stacks."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        query = "SELECT name, languages, frameworks FROM projects WHERE 1=1"
        params = []
        
        if language:
            query += " AND languages LIKE ?"
            params.append(f"%{language}%")
        
        if framework:
            query += " AND frameworks LIKE ?"
            params.append(f"%{framework}%")
        
        query += " ORDER BY created_at DESC LIMIT 5"
        
        c.execute(query, params)
        results = c.fetchall()
        conn.close()
        
        if not results:
            return "No similar projects found in history."
        
        summary = []
        for name, langs, fwks in results:
            summary.append(f"- **{name}**: {', '.join(json.loads(langs))} | {', '.join(json.loads(fwks))}")
        
        return "Similar projects:\n" + "\n".join(summary)
    
    async def get_common_patterns(self):
        """Returns common patterns across all projects."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT languages, frameworks FROM projects")
        results = c.fetchall()
        conn.close()
        
        if not results:
            return "No project history available yet."
        
        all_langs = []
        all_fwks = []
        for langs, fwks in results:
            all_langs.extend(json.loads(langs))
            all_fwks.extend(json.loads(fwks))
        
        from collections import Counter
        lang_counts = Counter(all_langs).most_common(3)
        fwk_counts = Counter(all_fwks).most_common(3)
        
        summary = "**Common Patterns:**\n"
        summary += f"Top Languages: {', '.join([f'{l} ({c})' for l, c in lang_counts])}\n"
        summary += f"Top Frameworks: {', '.join([f'{f} ({c})' for f, c in fwk_counts])}"
        
        return summary
    
    async def shutdown(self):
        print("[CrossProjectAgent] Shutdown complete.")
