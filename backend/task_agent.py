import json
import os
from datetime import datetime

class TaskAgent:
    def __init__(self, storage_path="tasks.json"):
        self.storage_path = os.path.join(os.path.dirname(__file__), storage_path)
        self.tasks = []
        self._load_tasks()

    def _load_tasks(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    self.tasks = json.load(f)
            except Exception as e:
                print(f"[TaskAgent] Error loading tasks: {e}")
                self.tasks = []

    def _save_tasks(self):
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.tasks, f, indent=4)
        except Exception as e:
            print(f"[TaskAgent] Error saving tasks: {e}")

    def add_task(self, title, description="", due_date=None, priority="medium"):
        task = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "title": title,
            "description": description,
            "due_date": due_date,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        self.tasks.append(task)
        self._save_tasks()
        return task

    def get_tasks(self, status=None):
        if status:
            return [t for t in self.tasks if t["status"] == status]
        return self.tasks

    def update_task_status(self, task_id, status):
        for t in self.tasks:
            if t["id"] == task_id:
                t["status"] = status
                self._save_tasks()
                return True
        return False

    def delete_task(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self._save_tasks()
        return True

    def clear_completed(self):
        self.tasks = [t for t in self.tasks if t["status"] != "completed"]
        self._save_tasks()
        return True

# Tool Definitions for Gemini
task_tools = [
    {
        "name": "add_task",
        "description": "Add a new task or item to the user's TODO list.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title of the task."},
                "description": {"type": "string", "description": "Optional details about the task."},
                "priority": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "list_tasks",
        "description": "List all pending or completed tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pending", "completed"], "description": "Filter by status."}
            }
        }
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_title": {"type": "string", "description": "The title or partial title of the task to complete."}
            },
            "required": ["task_title"]
        }
    }
]
