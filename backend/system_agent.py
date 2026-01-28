import psutil
import asyncio
import time
import platform
import os
import shutil
import aiohttp
import ctypes
from ctypes import wintypes

class SystemAgent:
    def __init__(self, callback, on_alert=None, lifestyle_agent=None):
        self.callback = callback
        self.on_alert = on_alert
        self.lifestyle_agent = lifestyle_agent
        self.mobile_bridge = None # To be set by server
        self.running = False
        self.task = None
        self.resolver_task = None
        self.ip_cache = {}
        self.ip_queue = asyncio.Queue()
        
        # Windows ctypes setup for window title
        self.user32 = ctypes.windll.user32
        
        # Network tracking
        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = time.time()
        # Maintenance thresholds
        self.thresholds = {
            'cpu': 90.0,    # %
            'ram': 85.0,    # %
            'disk': 90.0,   # %
            'cpu_trend': 5.0, # % increase per sample
            'ram_trend': 2.0  # % increase per sample
        }
        self.history = {
            'cpu': [],
            'ram': []
        }
        self.max_history = 10
        self.last_notification_time = 0
        self.notification_cooldown = 300 # 5 minutes
        self._fetch_hardware_info()

    async def start(self):
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        print(f"[SystemAgent] Started monitoring loop.")
        self.resolver_task = asyncio.create_task(self._resolve_ips())

    def get_stats(self):
        """Public accessor for mobile bridge to get current stats."""
        return self._get_stats()

    async def stop(self):
        self.running = False
        if self._task: # Changed from self.task to self._task
            self._task.cancel()
        if self.resolver_task:
            self.resolver_task.cancel()

    def _get_ip_location(self, ip):
        """Returns cached location or queues for resolution."""
        if ip in self.ip_cache:
            return self.ip_cache[ip]
        
        # If not cached and queue not too full, queue it
        if self.ip_queue.qsize() < 50:
             self.ip_cache[ip] = {} # Mark as pending to avoid re-queueing
             self.ip_queue.put_nowait(ip)
        
        return {}

    def _get_active_window(self):
        try:
            hwnd = self.user32.GetForegroundWindow()
            length = self.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buff, length + 1)
                return buff.value
        except:
            pass
        return ""

    async def _resolve_ips(self):
        """Background loop to resolve IPs."""
        async with aiohttp.ClientSession() as session:
            while self.running:
                try:
                    ip = await self.ip_queue.get()
                    if not ip: continue

                    # Use ip-api.com (free, rate limited to 45/min)
                    async with session.get(f"http://ip-api.com/json/{ip}") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get('status') == 'success':
                                self.ip_cache[ip] = {
                                    'lat': data.get('lat'),
                                    'lon': data.get('lon'),
                                    'city': data.get('city'),
                                    'country': data.get('countryCode')
                                }
                    
                    # Rate limit kindness
                    await asyncio.sleep(1.5) 
                except Exception as e:
                    print(f"GeoIP Error: {e}")
                    await asyncio.sleep(1)

    async def _monitor_loop(self):
        while self.running:
            try:
                stats = self._get_stats()
                # Check for maintenance
                await self._check_maintenance(stats)
                
                # Send general stats
                if self.callback:
                    self.callback(stats)
                
                await asyncio.sleep(2) # Poll every 2 seconds
            except Exception as e:
                print(f"[SystemAgent] Error in loop: {e}")
                await asyncio.sleep(5)

    async def _check_maintenance(self, stats):
        """Checks if resources are exceeding thresholds or trending upwards significantly."""
        now = time.time()
        
        # Update history
        self.history['cpu'].append(stats['cpu'])
        self.history['ram'].append(stats['ram']['percent'])
        if len(self.history['cpu']) > self.max_history:
            self.history['cpu'].pop(0)
        if len(self.history['ram']) > self.max_history:
            self.history['ram'].pop(0)

        if now - self.last_notification_time < self.notification_cooldown:
            return

        recommendations = []
        
        # 1. Hard Threshold Checks
        if stats['cpu'] > self.thresholds['cpu']:
            top_proc = stats['processes'][0]['name'] if stats['processes'] else "Unknown"
            recommendations.append(f"High CPU usage detected ({stats['cpu']}%). {top_proc} is using the most resources.")

        if stats['ram']['percent'] > self.thresholds['ram']:
            recommendations.append(f"System memory is low ({stats['ram']['percent']}% used). Consider closing non-essential apps.")

        # 2. Trend Analysis (Proactive)
        if len(self.history['cpu']) >= 5:
            cpu_trend = stats['cpu'] - self.history['cpu'][-5]
            if cpu_trend > self.thresholds['cpu_trend'] and stats['cpu'] > 50:
                 recommendations.append(f"CPU is trending upwards quickly (+{round(cpu_trend, 1)}% recently).")

        if len(self.history['ram']) >= 5:
            ram_trend = stats['ram']['percent'] - self.history['ram'][-5]
            if ram_trend > self.thresholds['ram_trend'] and stats['ram']['percent'] > 60:
                 recommendations.append(f"Memory usage is increasing steadily (+{round(ram_trend, 1)}% recently).")

        # 3. Disk check
        for disk in stats['disks']:
            if disk['percent'] > self.thresholds['disk']:
                recommendations.append(f"Disk {disk['mount']} is almost full ({disk['percent']}%).")

        if recommendations:
            self.last_notification_time = now
            alert = {
                'id': int(time.time()),
                'type': 'maintenance',
                'message': " ".join(recommendations),
                'time': time.strftime("%H:%M:%S"),
                'action': 'cleanup_suggestion'
            }
            if self.on_alert:
                await self.on_alert(alert)

    def _fetch_hardware_info(self):
        """Fetches static hardware info via PowerShell."""
        info = {
            'manufacturer': 'UNKNOWN',
            'model': 'UNKNOWN',
            'bios': 'UNKNOWN'
        }
        if platform.system() == "Windows":
            import subprocess
            try:
                # Manufacturer
                cmd_man = "powershell -Command \"Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object -ExpandProperty Manufacturer\""
                man = subprocess.check_output(cmd_man, shell=True).decode().strip()
                if man: info['manufacturer'] = man

                # Model
                cmd_mod = "powershell -Command \"Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object -ExpandProperty Model\""
                mod = subprocess.check_output(cmd_mod, shell=True).decode().strip()
                if mod: info['model'] = mod

                # BIOS
                cmd_bios = "powershell -Command \"Get-CimInstance -ClassName Win32_BIOS | Select-Object -ExpandProperty SMBIOSBIOSVersion\""
                bios = subprocess.check_output(cmd_bios, shell=True).decode().strip()
                if bios: info['bios'] = bios
            except Exception as e:
                print(f"[SystemAgent] Failed to fetch hardware info: {e}")
        
        self.hardware_info = info

    def _get_stats(self):
        # CPU
        cpu_percent = psutil.cpu_percent(interval=None)
        
        # Memory
        mem = psutil.virtual_memory()
        ram_percent = mem.percent
        ram_used_gb = round(mem.used / (1024**3), 1)
        ram_total_gb = round(mem.total / (1024**3), 1)

        # Disks
        disks = []
        for partition in psutil.disk_partitions():
            if 'cdrom' in partition.opts or partition.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    'mount': partition.mountpoint,
                    'percent': usage.percent,
                    'free': round(usage.free / (1024**3), 1),
                    'total': round(usage.total / (1024**3), 1)
                })
            except:
                continue

        # Processes
        processes = []
        for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                processes.append({
                    'name': pinfo['name'],
                    'cpu': pinfo['cpu_percent'],
                    'mem': f"{round(pinfo['memory_percent'], 1)}%"
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU and take top 5
        processes = sorted(processes, key=lambda p: p['cpu'], reverse=True)[:5]

        # Network
        net_io = psutil.net_io_counters()
        now = time.time()
        dt = now - self.last_net_time
        # Avoid division by zero
        if dt == 0: dt = 0.001
        
        download_speed = round((net_io.bytes_recv - self.last_net_io.bytes_recv) / dt / 1024, 1) # KB/s
        upload_speed = round((net_io.bytes_sent - self.last_net_io.bytes_sent) / dt / 1024, 1) # KB/s
        
        self.last_net_io = net_io
        self.last_net_time = now

        # Active Connections & GeoIP
        connections = []
        try:
            # Get TCP connections
            conns = psutil.net_connections(kind='inet')
            # Filter for ESTABLISHED and unique remote IPs
            seen_ips = set()
            for c in conns:
                if c.status == 'ESTABLISHED' and c.raddr:
                    ip = c.raddr.ip
                    if ip not in seen_ips and ip != '127.0.0.1':
                        seen_ips.add(ip)
                        # Check cache or queue for resolution
                        loc = self._get_ip_location(ip)
                        connections.append({
                            'ip': ip,
                            'lat': loc.get('lat'),
                            'lon': loc.get('lon'),
                            'city': loc.get('city'),
                            'country': loc.get('country')
                        })
                        if len(connections) > 10: break # Limit to top 10 unique for performance
        except Exception as e:
            # print(f"Net Conn Error: {e}")
            pass

        # GPU Stats
        gpus = []
        try:
            import GPUtil
            gpu_list = GPUtil.getGPUs()
            for gpu in gpu_list:
                gpus.append({
                    'id': gpu.id,
                    'name': gpu.name,
                    'load': round(gpu.load * 100, 1),
                    'memoryUsed': round(gpu.memoryUsed, 0),
                    'memoryTotal': round(gpu.memoryTotal, 0),
                    'temperature': gpu.temperature
                })
        except Exception as e:
            # print(f"GPU Error: {e}") 
            pass

        return {
            'active_window': self._get_active_window(),
            'cpu': cpu_percent,
            'ram': {
                'percent': ram_percent,
                'used': ram_used_gb,
                'total': ram_total_gb
            },
            'disk': disks[0] if disks else {'percent': 0, 'free': 0},
            'disks': disks,
            'gpu': gpus[0] if gpus else None, # Primary GPU for simple display
            'gpus': gpus,
            'processes': processes,
            'network': {
                'down': download_speed,
                'up': upload_speed,
                'up_rate': upload_speed * 1024,   # Bytes/s for frontend formatting
                'down_rate': download_speed * 1024, # Bytes/s for frontend formatting
                'connections': connections
            },
            'info': {
                'node': platform.node(),
                'os': platform.system(),
                'processor': platform.processor(),
                'manufacturer': getattr(self, 'hardware_info', {}).get('manufacturer', 'UNKNOWN'),
                'model': getattr(self, 'hardware_info', {}).get('model', 'UNKNOWN'),
                'bios': getattr(self, 'hardware_info', {}).get('bios', 'UNKNOWN')
            }
        }

    async def cleanup_system(self):
        """Cleans up temporary files. Returns summary of what was done."""
        temp_dir = os.environ.get('TEMP')
        if not temp_dir:
            return "No TEMP directory found."
        
        files_removed = 0
        bytes_freed = 0
        
        # Only clean some common temp subdirectories to be safe
        # In a real environment, we should be careful not to delete files in use.
        # We'll target the main temp folder and ignore errors (files in use).
        for root, dirs, files in os.walk(temp_dir):
            # Avoid deep recursion to prevent hanging
            if root.count(os.sep) - temp_dir.count(os.sep) > 2:
                continue
            for name in files:
                try:
                    path = os.path.join(root, name)
                    # Skip files larger than 100MB to avoid long IO
                    if os.path.getsize(path) > 100 * 1024 * 1024:
                        continue
                    size = os.path.getsize(path)
                    os.remove(path)
                    files_removed += 1
                    bytes_freed += size
                except:
                    continue
        
        return f"Cleaned up {files_removed} temporary files. Freed {round(bytes_freed / (1024**2), 1)} MB."

    async def check_updates(self):
        """Checks for pending Windows updates or major driver outdated states."""
        if platform.system() != "Windows":
            return "Update check only supported on Windows."
            
        print("[SystemAgent] Checking for system updates...")
        try:
            import subprocess
            # Lightweight check using PSWindowsUpdate or generic Session check
            cmd = "powershell -Command \"$UpdateSession = New-Object -ComObject 'Microsoft.Update.Session'; $UpdateSearcher = $UpdateSession.CreateUpdateSearcher(); $SearchResult = $UpdateSearcher.Search('IsInstalled=0 and Type=\\'Software\\' and IsHidden=0'); $SearchResult.Updates | Select-Object -Property Title\""
            result = await asyncio.to_thread(subprocess.check_output, cmd, shell=True)
            output = result.decode().strip()
            
            if not output:
                return "No pending Windows updates found."
            
            updates = output.split('\n')
            return f"Found {len(updates)} pending updates:\n" + "\n".join(updates[:5])
        except Exception as e:
            return f"Failed to check for updates: {e}"

    async def get_morning_briefing(self):
        """Generates a summary for the user at the start of the day."""
        stats = self._get_stats()
        date_str = time.strftime("%A, %B %d, %Y")
        greeting = f"Good morning! Today is {date_str}."
        sys_status = f"The system is running well. CPU is at {stats['cpu']}%, and you have {stats['ram']['percent']}% memory used."
        
        weather_summary = "Weather info currently unavailable."
        if self.lifestyle_agent:
            try:
                # Default to Mumbai if no location found, or try to get from IP
                # We can use the first IP location from stats if available
                location = "Mumbai"
                if stats['network']['connections']:
                    for conn in stats['network']['connections']:
                        if conn.get('city'):
                            location = conn['city']
                            break
                            
                weather = await self.lifestyle_agent.get_weather(location)
                if "summary" in weather:
                    weather_summary = weather["summary"]
            except Exception as e:
                print(f"[SystemAgent] Failed to fetch weather for briefing: {e}")

        return {
            'greeting': greeting,
            'system_status': sys_status,
            'weather_info': weather_summary
        }
    
    async def locate_file(self, filename, search_path=None):
        """
        Fast search for a file on the local system.
        If search_path is None, it scans common drives (C:, D:, etc.) with a shallow depth first.
        """
        results = []
        
        # Determine drives to search
        if search_path:
            drives = [search_path]
        else:
            drives = []
            for partition in psutil.disk_partitions():
                if 'fixed' in partition.opts or partition.fstype:
                    drives.append(partition.mountpoint)
        
        print(f"[SystemAgent] Locating '{filename}' in drives: {drives}")
        
        for drive in drives:
            try:
                # Use a fast walk or just search common folders first
                # We use a limited walk to maintain responsiveness.
                for root, dirs, files in os.walk(drive):
                    if filename.lower() in [f.lower() for f in files]:
                        full_path = os.path.join(root, filename)
                        results.append(full_path)
                    
                    # Safety/Performance: Don't dive too deep into hidden or system folders
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ['windows', 'program files', 'node_modules', 'appdata']]
                    
                    if len(results) >= 5: # Limit results
                        break
                if len(results) >= 5: break
            except:
                continue
        
        if results:
            return f"Found '{filename}' at:\n" + "\n".join(results)
        return f"Could not find '{filename}' on the system."

# Tool definitions for Gemini
system_maintenance_tools = [
    {
        "name": "cleanup_system",
        "description": "Perform system maintenance by cleaning temporary files to free up disk space.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_morning_briefing",
        "description": "Get a summary of the current day, including date and basic system status reports.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "locate_file",
        "description": "Searches for a file by name across all drives or a specific path. Use this to find PDFs, documents, or scripts the user mentions but doesn't provide a path for.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The exact name of the file to find (e.g. 'MSCCS_101.pdf')."},
                "search_path": {"type": "string", "description": "Optional directory to start search from (e.g. 'D:\\'). Defaults to all drives."}
            },
            "required": ["filename"]
        }
    }
]
