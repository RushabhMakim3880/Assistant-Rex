import os
from pathlib import Path

class SandboxService:
    """
    Security service that validates file operations against allowed directory boundaries.
    Prevents REX from accessing sensitive system folders or user data outside the project.
    """
    def __init__(self, allowed_roots=None):
        # Default allowed roots: Project Workspace and Temp CAD directory
        self.allowed_roots = allowed_roots or [
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), # Project Root
            os.environ.get('TEMP', '/tmp'),
        ]
        # Normalize paths
        self.allowed_roots = [os.path.abspath(r).lower() for r in self.allowed_roots]
        print(f"[Sandbox] Initialized with roots: {self.allowed_roots}")

    def is_path_safe(self, path: str) -> bool:
        """Checks if a given path falls within the allowed boundaries."""
        try:
            # Resolve all symlinks and '..' components
            abs_path = os.path.normpath(os.path.abspath(path)).lower()
            
            # Check if it starts with any allowed root
            for root in self.allowed_roots:
                # Ensure the root itself ends with a separator or we check it properly
                # to avoid 'C:\allowed' matching 'C:\allowed_not_really'
                root_path = os.path.normpath(root).lower()
                if abs_path.startswith(root_path):
                    # Double check that it's a subpath (not just startswith)
                    if abs_path == root_path or abs_path.startswith(root_path + os.sep):
                        return True
            return False
        except:
            return False

    def validate_path(self, path: str):
        """Raises a PermissionError if the path is outside the sandbox."""
        if not self.is_path_safe(path):
            print(f"[Sandbox] SECURITY ALERT: Blocked access to {path}")
            raise PermissionError(f"Access to path '{path}' is restricted by REX Sandbox.")
        return path

    def add_allowed_root(self, path: str):
        abs_path = os.path.abspath(path).lower()
        if abs_path not in self.allowed_roots:
            self.allowed_roots.append(abs_path)
            print(f"[Sandbox] Added safe root: {abs_path}")
