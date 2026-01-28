import os
import subprocess
import asyncio
from pathlib import Path

class ProjectSpawner:
    def __init__(self, project_manager):
        self.project_manager = project_manager

    async def spawn_project(self, name, template="basic"):
        """
        Orchestrates the creation of a new project.
        """
        success, msg = self.project_manager.create_project(name)
        if not success:
            return f"Failed to create project directory: {msg}"

        # Switch context to new project
        self.project_manager.switch_project(name)
        project_path = self.project_manager.get_current_project_path()

        results = []
        results.append(f"Project directory '{name}' initialized.")

        # 1. Init Git
        if await self._run_cmd(["git", "init"], project_path):
            results.append("Git repository initialized.")
        else:
            results.append("Warning: Git initialization failed.")

        # 2. Create venv (Python projects)
        if await self._run_cmd(["python", "-m", "venv", "venv"], project_path):
            results.append("Virtual environment ('venv') created.")
        else:
            results.append("Warning: venv creation failed.")

        # 3. Write Boilerplate based on template
        t = template.lower()
        if t == "fastapi":
            await self._write_fastapi_boilerplate(project_path)
            results.append("FastAPI boilerplate files created.")
        elif t == "scraper":
            await self._write_scraper_boilerplate(project_path)
            results.append("Web scraper boilerplate files created.")
        elif t in ["web", "html", "css"]:
            await self._write_web_boilerplate(project_path)
            results.append("Web (HTML/CSS) boilerplate files created.")
        elif t in ["node", "js", "javascript"]:
            await self._write_node_boilerplate(project_path)
            results.append("Node.js boilerplate files created.")
        elif t == "java":
            await self._write_java_boilerplate(project_path)
            results.append("Java boilerplate project created.")
        elif t == "php":
            await self._write_php_boilerplate(project_path)
            results.append("PHP boilerplate project created.")
        else:
            await self._write_basic_boilerplate(project_path)
            results.append(f"Basic boilerplate created for template '{template}'.")

        return "\n".join(results)

    async def _run_cmd(self, cmd, cwd):
        try:
            # Check if command exists before running (especially git)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return True
            else:
                err = stderr.decode().strip()
                print(f"[ProjectSpawner] Command failed: {cmd}, Error: {err}")
                return False
        except Exception as e:
            print(f"[ProjectSpawner] Error running command {cmd}: {e}")
            return False

    async def _write_basic_boilerplate(self, path):
        main_content = "def main():\n    print('Hello from R.E.X spawned project!')\n\nif __name__ == '__main__':\n    main()\n"
        with open(path / "main.py", "w") as f:
            f.write(main_content)
        with open(path / "requirements.txt", "w") as f:
            f.write("")
        with open(path / ".gitignore", "w") as f:
            f.write("venv/\n__pycache__/\n*.pyc\n")

    async def _write_fastapi_boilerplate(self, path):
        main_content = """from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello from R.E.X FastAPI boilerplate"}
"""
        with open(path / "main.py", "w") as f:
            f.write(main_content)
        with open(path / "requirements.txt", "w") as f:
            f.write("fastapi\nuvicorn\n")
        with open(path / ".gitignore", "w") as f:
            f.write("venv/\n__pycache__/\n*.pyc\n")

    async def _write_scraper_boilerplate(self, path):
        main_content = """import requests
from bs4 import BeautifulSoup

def scrape(url):
    print(f"Scraping {url}...")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    print(f"Title: {soup.title.string}")

if __name__ == '__main__':
    scrape('https://example.com')
"""
        with open(path / "main.py", "w") as f:
            f.write(main_content)
        with open(path / "requirements.txt", "w") as f:
            f.write("requests\nbeautifulsoup4\n")
        with open(path / ".gitignore", "w") as f:
            f.write("venv/\n__pycache__/\n*.pyc\n")

    async def _write_web_boilerplate(self, path):
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REX Web Project</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Welcome to Your R.E.X Project</h1>
        <p>This is a fresh HTML/CSS boilerplate.</p>
    </div>
    <script src="script.js"></script>
</body>
</html>"""
        css_content = """body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
.container { text-align: center; padding: 2rem; border: 1px solid #1e293b; border-radius: 0.75rem; background: #1e293b; }
h1 { color: #38bdf8; }"""
        js_content = "console.log('R.E.X Web Project initialized.');"
        
        with open(path / "index.html", "w") as f: f.write(html_content)
        with open(path / "style.css", "w") as f: f.write(css_content)
        with open(path / "script.js", "w") as f: f.write(js_content)
        with open(path / ".gitignore", "w") as f: f.write("node_modules/\n.DS_Store\n")

    async def _write_node_boilerplate(self, path):
        package_json = """{
  "name": "rex-node-project",
  "version": "1.0.0",
  "main": "index.js",
  "dependencies": {},
  "scripts": {
    "start": "node index.js"
  }
}"""
        index_js = "console.log('Hello from R.E.X Node.js environment!');"
        with open(path / "package.json", "w") as f: f.write(package_json)
        with open(path / "index.js", "w") as f: f.write(index_js)
        with open(path / ".gitignore", "w") as f: f.write("node_modules/\nnpm-debug.log\n")

    async def _write_java_boilerplate(self, path):
        java_content = """public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from R.E.X Java Boilerplate!");
    }
}"""
        with open(path / "Main.java", "w") as f: f.write(java_content)
        with open(path / ".gitignore", "w") as f: f.write("*.class\n*.jar\n")

    async def _write_php_boilerplate(self, path):
        php_content = """<?php
echo "<h1>Hello from R.E.X PHP Boilerplate</h1>";
phpinfo();
?>"""
        with open(path / "index.php", "w") as f: f.write(php_content)
        with open(path / ".gitignore", "w") as f: f.write("vendor/\n.env\n")
