import os
import shutil
import pathlib
from datetime import datetime

class FileOrganizerAgent:
    def __init__(self, base_paths=None):
        # Default to Desktop and Downloads if not provided
        if base_paths is None:
            self.base_paths = [
                str(pathlib.Path.home() / "Desktop"),
                str(pathlib.Path.home() / "Downloads")
            ]
        else:
            self.base_paths = base_paths
            
        self.categories = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp"],
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
            "Code": [".py", ".js", ".html", ".css", ".cpp", ".c", ".h", ".java", ".json", ".md", ".sh", ".ps1"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Executables": [".exe", ".msi", ".bat"],
            "Media": [".mp4", ".mp3", ".wav", ".mov", ".avi"]
        }

    async def scan_clutter(self, path=None):
        """Scans a directory for files and groups them by category."""
        target_path = path if path else self.base_paths[0]
        if not os.path.exists(target_path):
            return {"error": f"Path {target_path} does not exist."}

        files_found = []
        clutter_summary = {}

        for item in os.listdir(target_path):
            full_path = os.path.join(target_path, item)
            if os.path.isfile(full_path):
                ext = pathlib.Path(item).suffix.lower()
                category = "Miscellaneous"
                
                for cat, extensions in self.categories.items():
                    if ext in extensions:
                        category = cat
                        break
                
                if category not in clutter_summary:
                    clutter_summary[category] = []
                
                clutter_summary[category].append(item)
                files_found.append({"name": item, "category": category})

        return {
            "path": target_path,
            "summary": clutter_summary,
            "total_files": len(files_found)
        }

    async def organize_folder(self, path=None, target_subdir="REX_Organized"):
        """Moves files into categorized subfolders within a target directory."""
        target_path = path if path else self.base_paths[0]
        if not os.path.exists(target_path):
            return {"error": f"Path {target_path} does not exist."}

        organized_root = os.path.join(target_path, target_subdir)
        if not os.path.exists(organized_root):
            os.makedirs(organized_root)

        moves = []
        errors = []

        for item in os.listdir(target_path):
            full_path = os.path.join(target_path, item)
            # Don't move the organized root itself or directories
            if os.path.isfile(full_path):
                ext = pathlib.Path(item).suffix.lower()
                category = "Miscellaneous"
                
                for cat, extensions in self.categories.items():
                    if ext in extensions:
                        category = cat
                        break
                
                cat_path = os.path.join(organized_root, category)
                if not os.path.exists(cat_path):
                    os.makedirs(cat_path)
                
                try:
                    dest_path = os.path.join(cat_path, item)
                    # Handle duplicate filenames
                    if os.path.exists(dest_path):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        dest_path = os.path.join(cat_path, f"{pathlib.Path(item).stem}_{timestamp}{ext}")
                    
                    shutil.move(full_path, dest_path)
                    moves.append({"file": item, "to": category})
                except Exception as e:
                    errors.append({"file": item, "error": str(e)})

        return {
            "organized_at": organized_root,
            "moved_count": len(moves),
            "moves": moves,
            "errors": errors
        }

# Tool Definitions for Gemini
file_organizer_tools = [
    {
        "name": "scan_desktop_clutter",
        "description": "Scans the Desktop or Downloads folder for local files and provides a summary of clutter grouped by category (Images, Docs, Code, etc).",
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "enum": ["Desktop", "Downloads"], "description": "The folder to scan."}
            }
        }
    },
    {
        "name": "organize_desktop_folder",
        "description": "Moves files on the Desktop or Downloads into an 'Organized' subfolder, categorized by type. REQUIRES user confirmation unless in autonomous mode.",
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "enum": ["Desktop", "Downloads"], "description": "The folder to organize."}
            },
            "required": ["folder"]
        }
    }
]
