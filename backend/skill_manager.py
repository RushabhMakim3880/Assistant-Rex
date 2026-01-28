import os
import importlib.util
import sys
import glob

class SkillManager:
    """
    Manages dynamic loading of Python 'skills' (plugins).
    Each skill is a .py file in the 'skills' folder that defines:
    - a function declaration (tool definition)
    - an implementation function
    """
    def __init__(self, skills_dir="skills"):
        self.skills_dir = skills_dir
        self.loaded_skills = {} # {name: module}
        self.gemini_tools = [] # List of tool definitions for Gemini

    async def initialize(self):
        """Discovers and loads all skills."""
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir)
            
        await self.reload_skills()

    async def reload_skills(self):
        """Scans the skills directory and imports modules."""
        print(f"[SkillManager] Scanning '{self.skills_dir}'...")
        self.loaded_skills.clear()
        self.gemini_tools.clear()
        
        # Add skills dir to path so imports work if needed
        if self.skills_dir not in sys.path:
            sys.path.append(self.skills_dir)

        pattern = os.path.join(self.skills_dir, "*.py")
        files = glob.glob(pattern)
        
        for file_path in files:
            filename = os.path.basename(file_path)
            if filename.startswith("_"): continue # Skip __init__.py etc
            
            skill_name = filename[:-3] # remove .py
            
            try:
                # Dynamic Import
                spec = importlib.util.spec_from_file_location(skill_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Verify it has 'tool_definition' and 'handler' (or main function matching name)
                if hasattr(module, 'tool_definition'):
                    self.loaded_skills[skill_name] = module
                    self.gemini_tools.append(module.tool_definition)
                    print(f"[SkillManager] Loaded skill: {skill_name}")
                else:
                    print(f"[SkillManager] Skipping {skill_name}: No 'tool_definition' found.")
                    
            except Exception as e:
                print(f"[SkillManager] Error loading {skill_name}: {e}")

        print(f"[SkillManager] Total loaded skills: {len(self.loaded_skills)}")

    def get_tool_definitions(self):
        return self.gemini_tools

    async def create_skill(self, skill_name, description, code):
        """
        Creates a new skill file dynamically (Self-Evolution Protocol).
        Validates and writes the skill to the skills directory.
        """
        try:
            # Sanitize skill name
            skill_name = skill_name.lower().replace(" ", "_")
            skill_path = os.path.join(self.skills_dir, f"{skill_name}.py")
            
            if os.path.exists(skill_path):
                return f"Skill '{skill_name}' already exists. Please use a different name."
            
            # Basic validation: check for dangerous imports
            dangerous_patterns = ["os.system", "subprocess.call", "eval(", "exec(", "__import__", "open("]
            for pattern in dangerous_patterns:
                if pattern in code:
                    return f"Skill code contains potentially dangerous operation: {pattern}. Blocked for safety."
            
            # Write skill file
            with open(skill_path, "w") as f:
                f.write(f'"""\n{description}\n"""\n\n')
                f.write(code)
            
            # Reload skills to register the new one
            await self.reload_skills()
            
            if skill_name in self.loaded_skills:
                return f"Successfully created and loaded skill: {skill_name}"
            else:
                return f"Skill file created but failed to load. Check syntax."
                
        except Exception as e:
            return f"Failed to create skill: {e}"

    def get_skill_module(self, name):
        return self.loaded_skills.get(name)

# Tool Definition for Gemini to trigger reload
skill_tools = [
    {
        "name": "reload_skills",
        "description": "Reloads all Python skills/plugins from the skills folder. Use this after the user adds a new skill.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    }
]
