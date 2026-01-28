import asyncio
import os

class ModeManager:
    """
    Manages system-wide "Modes" or "Macros".
    Orchestrates multiple agents (Desktop, Kasa, etc.) to achieve a desired state.
    """
    def __init__(self, service_manager=None):
        self.service_manager = service_manager
        self.modes = {
            "work": {
                "apps_to_open": ["code", "browser"],
                "apps_to_close": ["Steam.exe", "Discord.exe"],
                "lights": {"target": "all", "action": "set", "color": "cyan", "brightness": 100},
                "speech": "Work mode initiated. Synchronizing environment for deep focus."
            },
            "gaming": {
                "apps_to_open": ["steam"],
                "apps_to_close": ["Code.exe", "PyCharm.exe"],
                "lights": {"target": "all", "action": "set", "color": "purple", "brightness": 60},
                "speech": "Gaming protocol active. Immersing system in high-performance mode."
            },
            "morning": {
                "apps_to_open": ["https://news.google.com", "browser"],
                "apps_to_close": [],
                "lights": {"target": "all", "action": "set", "color": "white", "brightness": 100},
                "speech": "Good morning. Initialization sequence complete. News and dashboard are ready."
            },
            "relax": {
                "apps_to_open": [],
                "apps_to_close": ["Code.exe", "Visual Studio Code"],
                "lights": {"target": "all", "action": "set", "color": "warm", "brightness": 40},
                "speech": "Relax mode engaged. Atmospheric parameters adjusted for recovery."
            },
            "default": {
                "apps_to_open": [],
                "apps_to_close": [],
                "lights": {"target": "all", "action": "set", "color": "cyan", "brightness": 80},
                "speech": "Restoring default system configuration."
            },
            "ethical_hacking": {
                "apps_to_open": ["msfconsole"],
                "apps_to_close": ["browser", "Code.exe"],
                "lights": {"target": "all", "action": "set", "color": "red", "brightness": 100},
                "speech": "Ethical Hacking Mode activated. Initializing offensive security environment. Remember to stay within legal boundaries, Sir."
            }
        }

    async def apply_mode(self, mode_name):
        mode_name = mode_name.lower().strip()
        if mode_name not in self.modes:
            return False, f"Mode '{mode_name}' not found.", None

        if mode_name == "ethical_hacking":
            import platform
            is_kali = False
            if platform.system() == "Linux":
                try:
                    if os.path.exists("/etc/os-release"):
                        with open("/etc/os-release", "r") as f:
                            if "kali" in f.read().lower():
                                is_kali = True
                except Exception:
                    pass
            
            if not is_kali:
                return False, "Ethical Hacking Mode is only available on Kali Linux. Please run R.E.X in a Kali environment to use this feature.", "I'm sorry Sir, but the Ethical Hacking module requires a Kali Linux environment. Please switch to Kali to proceed."

        config = self.modes[mode_name]
        results = []
        speech = config.get("speech")

        # 1. Close Apps
        desktop = await self.service_manager.get_service("desktop")
        if desktop:
            for app in config.get("apps_to_close", []):
                try:
                    await desktop.close_app(app)
                    results.append(f"Closed {app}")
                except Exception:
                    pass

        # 2. Open Apps / URLs
        if desktop:
            for app in config.get("apps_to_open", []):
                try:
                    # Special handling for common browser/code mapping if needed
                    if app.startswith("http"):
                         import webbrowser
                         webbrowser.open(app)
                         results.append(f"Opened URL: {app}")
                    elif app == "browser":
                        import webbrowser
                        webbrowser.open("https://google.com")
                        results.append(f"Opened Browser")
                    elif app == "code":
                        os.system("code")
                        results.append(f"Opened VS Code")
                    else:
                        await desktop.launch_app(app)
                        results.append(f"Opened {app}")
                except Exception as e:
                    results.append(f"Failed to open {app}: {e}")

        # 3. Lights
        kasa = await self.service_manager.get_service("kasa")
        if kasa and "lights" in config:
            light_cfg = config["lights"]
            # Trigger discovery if haven't recently or just use known
            if not kasa.devices:
                await kasa.discover_devices()
                
            devices = list(kasa.devices.values())
            for dev in devices:
                if dev.is_bulb or dev.is_dimmer or dev.is_plug:
                    try:
                        if light_cfg["action"] == "set":
                            if dev.is_bulb or dev.is_dimmer:
                                if "color" in light_cfg:
                                    await kasa.set_color(dev.ip, light_cfg["color"])
                                if "brightness" in light_cfg:
                                    await kasa.set_brightness(dev.ip, light_cfg["brightness"])
                            await kasa.turn_on(dev.ip)
                        elif light_cfg["action"] == "turn_off":
                            await kasa.turn_off(dev.ip)
                        results.append(f"Adjusted light: {dev.alias}")
                    except Exception as e:
                        print(f"Error adjusting light {dev.alias}: {e}")

        return True, "\n".join(results), speech

# Tool definition for Gemini
mode_tools = [
    {
        "name": "apply_system_mode",
        "description": "Applies a predefined system mode (macro) like 'work', 'gaming', 'morning', or 'relax'. This automatically opens/closes apps, launches URLs, and sets smart lighting.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mode_name": {
                    "type": "STRING", 
                    "description": "The name of the mode to apply: 'work', 'gaming', 'morning', 'relax', or 'ethical_hacking'."
                }
            },
            "required": ["mode_name"]
        }
    }
]
