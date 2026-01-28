import sys
import asyncio
import os
import traceback

# Detect if we are frozen (PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    # Frozen: Workspace in Documents
    WORKSPACE_ROOT = os.path.join(os.path.expanduser('~'), 'Documents', 'REX_Workspace')
    if not os.path.exists(WORKSPACE_ROOT):
        try:
            os.makedirs(WORKSPACE_ROOT)
        except:
            pass
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Dev: Workspace in project root
    WORKSPACE_ROOT = os.path.dirname(BASE_DIR)


# Fix for asyncio subprocess support on Windows
# MUST BE SET BEFORE OTHER IMPORTS
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # Force UTF-8 encoding for stdout/stderr to handle emojis in Windows console
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Fix for Matplotlib in frozen app (PyInstaller)
# It tries to write config to read-only locations or fails to find HOME
if getattr(sys, 'frozen', False):
    import tempfile
    # Use a temp dir for matplotlib config to avoid permission errors
    os.environ['MPLCONFIGDIR'] = os.path.join(tempfile.gettempdir(), 'matplotlib_config')
    if not os.path.exists(os.environ['MPLCONFIGDIR']):
        try:
            os.makedirs(os.environ['MPLCONFIGDIR'])
        except:
            pass

import socketio
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import threading
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from fastapi import Request
from fastapi.responses import JSONResponse



# Ensure we can import rex and other modules
if getattr(sys, 'frozen', False):
    # If we are running in a bundled PyInstaller exe
    # The temp path where files are unpacked
    BASE_DIR = sys._MEIPASS
else:
    # Normal Python run
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(BASE_DIR)

import rex
from authenticator import FaceAuthenticator
from kasa_agent import KasaAgent

# Global state
audio_loop = None
loop_task = None
service_manager = None
authenticator = None
kasa_agent = None # Deprecated global, use service_manager

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# Define Lifespan Manager (Replaces deprecated @app.on_event("startup"))
@asynccontextmanager
async def lifespan(app: FastAPI):
    global service_manager, kasa_agent # Keep kasa_agent global for now for backward compat
    import sys
    print(f"[SERVER DEBUG] Lifespan Startup Triggered")
    
    # Initialize Service Manager
    from service_manager import ServiceManager
    service_manager = ServiceManager(backend_dir=BASE_DIR)
    
    # Import Base Agents
    from kasa_agent import KasaAgent
    from cad_agent import CadAgent
    from web_agent import WebAgent
    from printer_agent import PrinterAgent
    from project_manager import ProjectManager
    from desktop_agent import DesktopAgent
    from skill_manager import SkillManager
    from project_spawner import ProjectSpawner
    # from visual_memory_agent import VisualMemoryAgent
    from cross_project_agent import CrossProjectAgent
    from system_agent import SystemAgent
    from communications_agent import CommunicationsAgent
    from ollama_agent import OllamaAgent
    from calendar_agent import CalendarAgent
    from task_agent import TaskAgent
    from file_organizer_agent import FileOrganizerAgent
    from clipboard_agent import ClipboardAgent
    from lifestyle_agent import LifestyleAgent
    from terminal_agent import TerminalAgent
    from macro_agent import MacroAgent
    from generative_ui_agent import GenerativeUIAgent
    from pattern_agent import PatternAgent
    from workflow_agent import WorkflowAgent
    from stock_agent import StockAgent
    from ethical_hacking_agent import EthicalHackingAgent
    from speech_agent import SpeechAgent

    # New Hardening Services
    from sandbox_service import SandboxService
    from safety_agent import SafetyAgent
    
    sandbox = SandboxService(allowed_roots=[WORKSPACE_ROOT, os.environ.get('TEMP', './')])
    await service_manager.register_service("sandbox", sandbox)
    
    safety = SafetyAgent()
    await service_manager.register_service("safety", safety)

    # Register Services with Sandbox
    kasa = KasaAgent(known_devices=SETTINGS.get("kasa_devices"))
    kasa.service_manager = service_manager
    # Default Rule: If CPU > 90, turn on Fan (if exists)
    await kasa.add_rule("cpu > 90", "System Fan", "on")
    await service_manager.register_service("kasa", kasa)
    await service_manager.register_service("ollama", OllamaAgent())
    await service_manager.register_service("tasks", TaskAgent())
    await service_manager.register_service("organizer", FileOrganizerAgent())
    
    clipboard = ClipboardAgent()
    await service_manager.register_service("clipboard", clipboard)
    asyncio.create_task(clipboard.start_monitoring())
    
    await service_manager.register_service("calendar", CalendarAgent())
    
    lifestyle = LifestyleAgent()
    await service_manager.register_service("lifestyle", lifestyle)
    lifestyle.on_reminder = lambda msg: asyncio.create_task(sio.emit('maintenance_alert', {'type': 'reminder', 'message': f"REMINDER: {msg}", 'severity': 'info'}))

    await service_manager.register_service("cad", CadAgent(
        on_thought=lambda text: asyncio.create_task(sio.emit('cad_thought', {'text': text})),
        on_status=lambda s: asyncio.create_task(sio.emit('cad_status', s if isinstance(s, dict) else {'status': s}))
    ))
    await service_manager.register_service("web", WebAgent())
    printer_agent = PrinterAgent()
    printer_agent.gemini_client = rex.get_gemini_client()
    printer_agent.sio = sio
    await service_manager.register_service("printer", printer_agent) 
    await service_manager.register_service("project", ProjectManager(workspace_root=WORKSPACE_ROOT))
    await service_manager.register_service("desktop", DesktopAgent())
    
    pattern_agent = PatternAgent()
    await service_manager.register_service("pattern", pattern_agent)
    
    desktop = await service_manager.get_service("desktop")
    await service_manager.register_service("workflow", WorkflowAgent(desktop_agent=desktop, gemini_client=rex.get_gemini_client(), pattern_agent=pattern_agent))
    await service_manager.register_service("terminal", TerminalAgent(workspace_root=WORKSPACE_ROOT, sandbox=sandbox))
    await service_manager.register_service("skills", SkillManager())
    
    pm = await service_manager.get_service("project")
    await service_manager.register_service("project_spawner", ProjectSpawner(pm))
    
    # desktop = await service_manager.get_service("desktop")
    # visual_memory = VisualMemoryAgent(desktop)
    # await service_manager.register_service("visual_memory", visual_memory)
    # await visual_memory.initialize(sio=sio)
    macro_agent = MacroAgent(desktop_agent=desktop)
    await service_manager.register_service("macro", macro_agent)
    asyncio.create_task(macro_agent.start_hotkey_listener(sio_handle=sio))
    
    await service_manager.register_service("generative_ui", GenerativeUIAgent())
    await service_manager.register_service("cross_project", CrossProjectAgent())
    
    await service_manager.register_service("stock", StockAgent(genai_client=rex.get_gemini_client()))
    await service_manager.register_service("hacking", EthicalHackingAgent())
    await service_manager.register_service("speech", SpeechAgent())

    from mobile_bridge_agent import MobileBridgeAgent
    mobile_bridge = MobileBridgeAgent(service_manager=service_manager)
    
    async def handle_mobile_intent(text):
        if audio_loop:
            await audio_loop.process_text(text, source="telegram")
        else:
            print(f"[SERVER] Mobile intent received but R.E.X. Audio Loop is not active: {text}")
            
    mobile_bridge.on_user_intent = lambda text: asyncio.create_task(handle_mobile_intent(text))
    await service_manager.register_service("mobile_bridge", mobile_bridge)
    await mobile_bridge.initialize()

    from shadow_agent import ShadowAgent
    shadow = ShadowAgent()
    shadow.sio = sio
    shadow.mobile_bridge = mobile_bridge
    await service_manager.register_service("shadow", shadow)
    
    from recursive_agent import RecursiveAgent
    await service_manager.register_service("recursive", RecursiveAgent(service_manager, WORKSPACE_ROOT, sio=sio))

    # Phase VI: Distributed Hive Mind
    from sync_agent import SyncAgent
    SYNC_ROOT = os.path.join(WORKSPACE_ROOT, ".rex_sync") # User-specifiable in future
    sync_agent = SyncAgent(sync_root=SYNC_ROOT, local_data_dir=os.path.join(BASE_DIR, "backend"))
    sync_agent.on_state_updated = lambda: pattern_agent.reload_data()
    await service_manager.register_service("sync", sync_agent)
    await sync_agent.initialize()


    # Initialize System Agent
    system_agent = SystemAgent(
        callback=lambda stats: asyncio.create_task(sio.emit('system_stats', stats)),
        on_alert=lambda alert: asyncio.create_task(sio.emit('maintenance_alert', alert)),
        lifestyle_agent=lifestyle
    )
    await service_manager.register_service("system", system_agent)
    await system_agent.start()

    # Initialize Communications Agent
    comm_agent = CommunicationsAgent(on_notification=lambda n: asyncio.create_task(sio.emit('comm_notification', n)))
    await service_manager.register_service("communications", comm_agent)
    await comm_agent.initialize()

    # New Modular Services
    from tool_dispatcher import ToolDispatcher
    from voice_service import VoiceService
    from vision_service import VisionService
    from semantic_search_agent import SemanticSearchAgent
    
    # Register Semantic Search for LTM
    ss_agent = SemanticSearchAgent(api_key=os.getenv("GEMINI_API_KEY"))
    await service_manager.register_service("semantic_search", ss_agent)
    
    dispatcher = ToolDispatcher(service_manager)
    await service_manager.register_service("dispatcher", dispatcher)
    
    vision = VisionService()
    await service_manager.register_service("vision", vision)

    # Initialize All
    await service_manager.initialize_all()
    
    # Final Safety Boot Log
    await safety.log_event("STABLE_STARTUP", f"REX v2.0 Modular backend initialized. {len(service_manager.services)} services running.")

    # API Endpoints for Hardening
    @app.post("/panic")
    async def panic():
        """User-triggered emergency shutdown."""
        safety_mgr = await service_manager.get_service("safety")
        if safety_mgr:
            msg = await safety_mgr.trigger_kill_switch()
            return {"status": "STOPPED", "message": msg}
        return {"status": "ERROR", "message": "SafetyAgent not found"}
    
    # Set backward compat global
    kasa_agent = await service_manager.get_service("kasa")
    load_settings()

    yield # Running application

    # Cleanup on shutdown
    print(f"[SERVER DEBUG] Lifespan Shutdown Triggered")
    if audio_loop:
        try:
            print("[SERVER] Stopping Audio Loop...")
            audio_loop.stop()
        except:
            pass
    if authenticator:
        authenticator.stop()
    
    # Gracefully shut down all services managed by ServiceManager
    if service_manager:
        await service_manager.shutdown_all()
    
    # Stop System Agent
    try:
        sys_agent = await service_manager.get_service("system")
        if sys_agent:
            await sys_agent.stop()
    except:
        pass

# Initialize FastAPI with lifespan
app = FastAPI(lifespan=lifespan)

# Mount Generated Apps Directory
apps_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_apps")
if not os.path.exists(apps_dir):
    os.makedirs(apps_dir)
app.mount("/apps", StaticFiles(directory=apps_dir), name="apps")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
async def status():
    return {"status": "ok", "service": "REX Backend"}

app_socketio = socketio.ASGIApp(sio, app)

import signal

# --- SHUTDOWN HANDLER ---
def signal_handler(sig, frame):
    print(f"\n[SERVER] Caught signal {sig}. Exiting gracefully...")
    # Clean up audio loop
    if audio_loop:
        try:
            print("[SERVER] Stopping Audio Loop...")
            audio_loop.stop() 
        except:
            pass
    # Force kill
    print("[SERVER] Force exiting...")
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Determine Settings Path
if sys.platform == 'win32':
    APP_DATA = os.path.join(os.environ['APPDATA'], 'GeminiREX')
else:
    APP_DATA = os.path.expanduser('~/.geminirex')

if not os.path.exists(APP_DATA):
    try:
        os.makedirs(APP_DATA)
    except:
        pass

SETTINGS_FILE = os.path.join(APP_DATA, "settings.json")

DEFAULT_SETTINGS = {
    "face_auth_enabled": False, 
    "tool_permissions": {
        "generate_cad": True,
        "run_web_agent": True,
        "write_file": True,
        "read_directory": True,
        "read_file": True,
        "create_project": True,
        "switch_project": True,
        "list_projects": True,
        "desktop_qa": True,         # NEW
        "autonomous_control": False # NEW (Default OFF)
    },
    "printers": [], 
    "kasa_devices": [],
    "camera_flipped": False 
}

SETTINGS = DEFAULT_SETTINGS.copy()

def load_settings():
    global SETTINGS
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults to ensure new keys exist
                # Deep merge for tool_permissions would be better but shallow merge of top keys + tool_permissions check is okay for now
                for k, v in loaded.items():
                    if k == "tool_permissions" and isinstance(v, dict):
                         SETTINGS["tool_permissions"].update(v)
                    else:
                        SETTINGS[k] = v
            print(f"Loaded settings: {SETTINGS}")
        except Exception as e:
            print(f"Error loading settings: {e}")

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(SETTINGS, f, indent=4)
        print("Settings saved.")
    except Exception as e:
        print(f"Error saving settings: {e}")

# Load on startup
load_settings()

authenticator = None
kasa_agent = None # Initialized in startup

# Startup logic moved to lifespan


@app.get("/status")
async def status():
    return {"status": "running", "service": "R.E.X Backend"}

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit('status', {'msg': 'Connected to R.E.X Backend'}, room=sid)

    global authenticator
    
    # Callback for Auth Status
    async def on_auth_status(is_auth):
        print(f"[SERVER] Auth status change: {is_auth}")
        await sio.emit('auth_status', {'authenticated': is_auth})

    # Callback for Auth Camera Frames
    async def on_auth_frame(frame_b64):
        await sio.emit('auth_frame', {'image': frame_b64})

    # Initialize Authenticator if not already done
    if authenticator is None:
        authenticator = FaceAuthenticator(
            reference_image_path="reference.jpg",
            on_status_change=on_auth_status,
            on_frame=on_auth_frame
        )
    
    # Check if already authenticated or needs to start
    if authenticator.authenticated:
        await sio.emit('auth_status', {'authenticated': True})
    else:
        # Check Settings for Auth
        if SETTINGS.get("face_auth_enabled", False):
            await sio.emit('auth_status', {'authenticated': False})
            # Start the auth loop in background
            asyncio.create_task(authenticator.start_authentication_loop())
        else:
            # Bypass Auth
            print("Face Auth Disabled. Auto-authenticating.")
            # We don't change authenticator state to true to avoid confusion if re-enabled? 
            # Or we should just tell client it's auth'd.
            await sio.emit('auth_status', {'authenticated': True})

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def switch_video_mode(sid, data):
    # data: { mode: "camera" | "screen" }
    mode = data.get('mode', 'camera')
    print(f"[SERVER] Switching video mode to: {mode}")
    if audio_loop:
        audio_loop.video_mode = mode
        await sio.emit('status', {'msg': f"Vision Mode: {mode.upper()}"})

@sio.event
async def start_audio(sid, data=None):
    global audio_loop, loop_task
    
    # Optional: Block if not authenticated
    # Only block if auth is ENABLED and not authenticated
    if SETTINGS.get("face_auth_enabled", False):
        if authenticator and not authenticator.authenticated:
            print("Blocked start_audio: Not authenticated.")
            await sio.emit('error', {'msg': 'Authentication Required'})
            return

    print("Starting Audio Loop...")
    
    device_index = None
    device_name = None
    output_device_index = None
    output_device_name = None
    if data:
        if 'device_index' in data:
            device_index = data['device_index']
        if 'device_name' in data:
            device_name = data['device_name']
        if 'output_device_index' in data:
            output_device_index = data['output_device_index']
        if 'output_device_name' in data:
            output_device_name = data['output_device_name']
            
    print(f"Using input device: Name='{device_name}', Index={device_index}")
    print(f"Using output device: Name='{output_device_name}', Index={output_device_index}")
    
    if audio_loop:
        if loop_task and (loop_task.done() or loop_task.cancelled()):
             print("Audio loop task appeared finished/cancelled. Clearing and restarting...")
             audio_loop = None
             loop_task = None
        else:
             print("Audio loop already running. Re-connecting client to session.")
             await sio.emit('status', {'msg': 'R.E.X Already Running'})
             return


    # Callback to send audio data to frontend
    def on_audio_data(data_bytes):
        # We need to schedule this on the event loop
        # This is high frequency, so we might want to downsample or batch if it's too much
        asyncio.create_task(sio.emit('audio_data', {'data': list(data_bytes)}))

    # Callback to send CAL data to frontend
    def on_cad_data(data):
        info = f"{len(data.get('vertices', []))} vertices" if 'vertices' in data else f"{len(data.get('data', ''))} bytes (STL)"
        print(f"Sending CAD data to frontend: {info}")
        asyncio.create_task(sio.emit('cad_data', data))

    # Callback to send Browser data to frontend
    def on_web_data(data):
        print(f"Sending Browser data to frontend: {len(data.get('log', ''))} chars logs")
        asyncio.create_task(sio.emit('browser_frame', data))
        
    # Callback to send Transcription data to frontend
    def on_transcription(data):
        # data = {"sender": "User"|"REX", "text": "..."}
        asyncio.create_task(sio.emit('transcription', data))

    # Callback to send Confirmation Request to frontend
    def on_tool_confirmation(data):
        # data = {"id": "uuid", "tool": "tool_name", "args": {...}}
        print(f"Requesting confirmation for tool: {data.get('tool')}")
        asyncio.create_task(sio.emit('tool_confirmation_request', data))

    # Callback to send CAD status to frontend
    def on_cad_status(status):
        # status can be: 
        # - a string like "generating" (from rex.py handle_cad_request)
        # - a dict with {status, attempt, max_attempts, error} (from CadAgent)
        if isinstance(status, dict):
            print(f"Sending CAD Status: {status.get('status')} (attempt {status.get('attempt')}/{status.get('max_attempts')})")
            asyncio.create_task(sio.emit('cad_status', status))
        else:
            # Legacy: simple string
            print(f"Sending CAD Status: {status}")
            asyncio.create_task(sio.emit('cad_status', {'status': status}))

    # Callback to send CAD thoughts to frontend (streaming)
    def on_cad_thought(thought_text):
        asyncio.create_task(sio.emit('cad_thought', {'text': thought_text}))

    # Callback to send Project Update to frontend
    def on_project_update(project_name):
        print(f"Sending Project Update: {project_name}")
        asyncio.create_task(sio.emit('project_update', {'project': project_name}))

    # Callback to send Device Update to frontend
    def on_device_update(devices):
        # devices is a list of dicts
        print(f"Sending Kasa Device Update: {len(devices)} devices")
        asyncio.create_task(sio.emit('kasa_devices', devices))

    # Callback to send Task Update to frontend
    def on_task_update(tasks):
        print(f"Sending Task Update: {len(tasks)} tasks")
        asyncio.create_task(sio.emit('tasks_update', tasks))

    # Callback to send Error to frontend
    def on_error(msg):
        print(f"Sending Error to frontend: {msg}")
        asyncio.create_task(sio.emit('error', {'msg': msg}))

    # Get Agents from Service Manager
    print("[SERVER] Retrieving agents from ServiceManager...")
    kasa_agent = await service_manager.get_service("kasa")
    cad_agent = await service_manager.get_service("cad")
    web_agent = await service_manager.get_service("web")
    printer_agent = await service_manager.get_service("printer")
    calendar_agent = await service_manager.get_service("calendar")
    macro_agent = await service_manager.get_service("macro")
    project_manager = await service_manager.get_service("project")
    desktop_agent = await service_manager.get_service("desktop")
    skill_manager = await service_manager.get_service("skills")
    terminal_agent = await service_manager.get_service("terminal")
    project_spawner = await service_manager.get_service("project_spawner")
    visual_memory = await service_manager.get_service("visual_memory")
    cross_project = await service_manager.get_service("cross_project")
    system_agent = await service_manager.get_service("system")
    comm_agent = await service_manager.get_service("communications")
    task_agent = await service_manager.get_service("tasks")
    organizer_agent = await service_manager.get_service("organizer")
    clipboard_agent = await service_manager.get_service("clipboard")
    lifestyle_agent = await service_manager.get_service("lifestyle")
    ollama_agent = await service_manager.get_service("ollama")
    calendar_agent = await service_manager.get_service("calendar")
    
    # Delayed dependency injection for LifestyleAgent (needs WebAgent)
    lifestyle_agent.web_agent = web_agent

    # AudioLoop will be used from rex
    
    # Load Printers (Using the singleton printer_agent)
    # (Removed Logic)

    # Callbacks for Window Control
    def on_minimize():
        print("[SERVER] Minimizing Request Triggered")
        asyncio.create_task(sio.emit('minimize_window'))

    def on_restore():
        print("[SERVER] Restore Request Triggered")
        asyncio.create_task(sio.emit('restore_window'))

    try:
        print(f"[SERVER] Initializing AudioLoop with device_index={device_index}")
        # Create AudioLoop instance
        audio_loop = rex.AudioLoop(
            input_device_index=device_index,
            input_device_name=device_name,
            output_device_index=output_device_index,
            output_device_name=output_device_name,
            on_audio_data=on_audio_data, 
            on_transcription=on_transcription,
            on_tool_confirmation=on_tool_confirmation,
            on_error=on_error,
            on_minimize=on_minimize,
            on_restore=on_restore,
            # Pass Services
            kasa_agent=kasa_agent, 
            cad_agent=cad_agent, 
            web_agent=web_agent,
            printer_agent=printer_agent,
            project_manager=project_manager,
            desktop_agent=desktop_agent, 
            skill_manager=skill_manager, 
            terminal_agent=terminal_agent,
            project_spawner=project_spawner,
            visual_memory=visual_memory,
            cross_project=cross_project,
            system_agent=system_agent,
            comm_agent=comm_agent,
            task_agent=task_agent,
            organizer_agent=organizer_agent,
            clipboard_agent=clipboard_agent,
            lifestyle_agent=lifestyle_agent,
            ollama_agent=ollama_agent,
            calendar_agent=calendar_agent,
            macro_agent=macro_agent,
            # Pass new agents
            stock_agent=await service_manager.get_service("stock"),
            hacking_agent=await service_manager.get_service("hacking"),
            semantic_search=await service_manager.get_service("semantic_search"),
            speech_agent=await service_manager.get_service("speech"),
            # Settings
            tool_permissions=SETTINGS.get("tool_permissions", {}),
            settings=SETTINGS,
            # Agent Callbacks
            on_cad_data=on_cad_data,
            on_web_data=on_web_data,
            on_project_update=on_project_update,
            on_task_update=on_task_update,
            on_stock_data=lambda data: asyncio.create_task(sio.emit('stock_data', data))
        )

        print("AudioLoop initialized successfully.")

        # Apply current permissions
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
        
        # Check initial mute state
        if data and data.get('muted', False):
            print("Starting with Audio Paused")
            audio_loop.set_paused(True)

        print("Creating asyncio task for AudioLoop.run()")
        loop_task = asyncio.create_task(audio_loop.run())
        
        # Add a done callback to catch silent failures in the loop
        # Add a done callback to catch silent failures in the loop
        def handle_loop_exit(task):
            try:
                task.result()
            except asyncio.CancelledError:
                print("Audio Loop Cancelled")
            except Exception as e:
                print(f"[CRITICAL] Audio Loop Crashed: {e}")
                import traceback
                tb_str = traceback.format_exc()
                print(f"[MEDIC] 🚑 Crash detected. Traceback:\n{tb_str}")
                
                async def trigger_medic():
                    try:
                        from medic_agent import MedicAgent
                        medic = MedicAgent()
                        success = await medic.heal(tb_str)
                        if success:
                            medic.restart_system()
                        else:
                            print("[MEDIC] ⚠️ Healing failed. System state critical.")
                    except Exception as medic_err:
                        print(f"[MEDIC] 💀 Medic failed to operate: {medic_err}")

                # Launch Medic asynchronously
                asyncio.create_task(trigger_medic())
        
        loop_task.add_done_callback(handle_loop_exit)
        
        print("Emitting 'R.E.X Started'")
        await sio.emit('status', {'msg': 'R.E.X Started'})

        # Load saved printers
        # Load saved printers
        # (DISABLED BY USER REQUEST)
        '''
        saved_printers = SETTINGS.get("printers", [])
        if saved_printers and audio_loop.printer_agent:
            print(f"[SERVER] Loading {len(saved_printers)} saved printers...")
            for p in saved_printers:
                audio_loop.printer_agent.add_printer_manually(
                    name=p.get("name", p["host"]),
                    host=p["host"],
                    port=p.get("port", 80),
                    printer_type=p.get("type", "moonraker"),
                    camera_url=p.get("camera_url")
                )
        '''
        
        # Start Printer Monitor
        # Start Printer Monitor
        # asyncio.create_task(monitor_printers_loop())
        
    except Exception as e:
        print(f"CRITICAL ERROR STARTING REX: {e}")
        import traceback
        traceback.print_exc()
        await sio.emit('error', {'msg': f"Failed to start: {str(e)}"})
        audio_loop = None # Ensure we can try again

@sio.event
async def set_barge_in_prevention(sid, data=None):
    """Enable or disable barge-in prevention (mute mic while REX speaks)
    
    Args:
        data: dict with 'enabled' (bool) and optional 'threshold' (int, default 2000)
              Lower threshold = more sensitive to interruptions
              Higher threshold = requires louder interruptions
    """
    global audio_loop
    
    if not audio_loop:
        print("[SERVER] [ERROR] Audio loop not running")
        return
    
    try:
        enabled = data.get('enabled', True) if data else True
        threshold = data.get('threshold', 2000) if data else 2000
        
        audio_loop.set_barge_in_prevention(enabled, threshold)
        
        status_msg = f"Barge-in prevention {'enabled' if enabled else 'disabled'} (threshold: {threshold})"
        await sio.emit('status', {'msg': status_msg})
        print(f"[SERVER] {status_msg}")
        
    except Exception as e:
        print(f"[SERVER] [ERROR] Failed to set barge-in prevention: {e}")
        await sio.emit('error', {'msg': f"Failed to update audio settings: {str(e)}"})


async def monitor_printers_loop():
    """Background task to query printer status periodically."""
    print("[SERVER] Starting Printer Monitor Loop")
    while audio_loop and audio_loop.printer_agent:
        try:
            agent = audio_loop.printer_agent
            if not agent.printers:
                await asyncio.sleep(5)
                continue
                
            tasks = []
            for host, printer in agent.printers.items():
                if printer.printer_type.value != "unknown":
                    tasks.append(agent.get_print_status(host))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        pass # Ignore errors for now
                    elif res:
                        # res is PrintStatus object
                        await sio.emit('print_status_update', res.to_dict())
                        
        except asyncio.CancelledError:
            print("[SERVER] Printer Monitor Cancelled")
            break
        except Exception as e:
            print(f"[SERVER] Monitor Loop Error: {e}")
            
        await asyncio.sleep(2) # Update every 2 seconds for responsiveness

@sio.event
async def stop_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.stop() 
        print("Stopping Audio Loop")
        audio_loop = None
        await sio.emit('status', {'msg': 'R.E.X Stopped'})

@sio.event
async def pause_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(True)
        print("Pausing Audio")
        await sio.emit('status', {'msg': 'Audio Paused'})

@sio.event
async def resume_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(False)
        print("Resuming Audio")
        await sio.emit('status', {'msg': 'Audio Resumed'})

@sio.event
async def confirm_tool(sid, data):
    # data: { "id": "...", "confirmed": True/False }
    request_id = data.get('id')
    confirmed = data.get('confirmed', False)
    
    print(f"[SERVER DEBUG] Received confirmation response for {request_id}: {confirmed}")
    
    if audio_loop:
        audio_loop.resolve_tool_confirmation(request_id, confirmed)
    else:
        print("Audio loop not active, cannot resolve confirmation.")

@sio.event
async def shutdown(sid, data=None):
    """Gracefully shutdown the server when the application closes."""
    global audio_loop, loop_task, authenticator
    
    print("[SERVER] ========================================")
    print("[SERVER] SHUTDOWN SIGNAL RECEIVED FROM FRONTEND")
    print("[SERVER] ========================================")
    
    # Stop audio loop
    if audio_loop:
        print("[SERVER] Stopping Audio Loop...")
        audio_loop.stop()
        audio_loop = None
    
    # Cancel the loop task if running
    if loop_task and not loop_task.done():
        print("[SERVER] Cancelling loop task...")
        loop_task.cancel()
        loop_task = None
    
    # Stop authenticator if running
    if authenticator:
        print("[SERVER] Stopping Authenticator...")
        authenticator.stop()
    
    print("[SERVER] Graceful shutdown complete. Terminating process...")
    
    # Force exit immediately - os._exit bypasses cleanup but ensures termination
    os._exit(0)

@sio.event
async def context_action(sid, data):
    """Handle context shortcut actions from the frontend."""
    action = data.get('action')
    window = data.get('window', 'Unknown')
    print(f"[SERVER] Context Action Triggered: {action} (Window: {window})")

    if action == 'sys_status':
        # Return generic system status
        import platform
        import psutil
        
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        status_msg = f"R.E.X ONLINE | CPU: {cpu}% | RAM: {mem}% | OS: {platform.system()}"
        await sio.emit('status', {'msg': status_msg})
        
    elif action == 'commit_code':
         await sio.emit('status', {'msg': 'Initiating Code Commit... (Simulation)'})
         
    elif action == 'fix_lint':
         await sio.emit('status', {'msg': 'Running Auto-Linter... (Simulation)'})
         
    elif action == 'run_tests':
         await sio.emit('status', {'msg': 'Executing Test Suite... (Simulation)'})
         
    elif action == 'render_scene':
         await sio.emit('status', {'msg': 'Starting Render Job... (Simulation)'})
         
    elif action == 'bake_textures':
         await sio.emit('status', {'msg': 'Baking Textures... (Simulation)'})
         
    elif action == 'summarize_page':
         await sio.emit('status', {'msg': 'Analysis complete. (Simulation)'})
         
    elif action == 'save_bookmark':
         await sio.emit('status', {'msg': 'Bookmark Saved. (Simulation)'})
         
    else:
        print(f"[SERVER] Unknown context action: {action}")

@sio.event
async def user_input(sid, data):
    text = data.get('text')
    print(f"[SERVER DEBUG] User input received: '{text}'")
    
    if not audio_loop:
        print("[SERVER DEBUG] [Error] Audio loop is None. Cannot send text.")
        return

    if not audio_loop.session:
        print("[SERVER DEBUG] [Error] Session is None. Cannot send text.")
        return

    if text:
        print(f"[SERVER DEBUG] Routing message to AudioLoop: '{text}'")
        
        # Log User Input to Project History
        if audio_loop and audio_loop.project_manager:
            audio_loop.project_manager.log_chat("User", text)
            
        await audio_loop.send_text(text)

import json
from datetime import datetime
from pathlib import Path

# ... (imports)

@sio.event
async def video_frame(sid, data):
    # data should contain 'image' which is binary (blob) or base64 encoded
    image_data = data.get('image')
    if image_data and audio_loop:
        # We don't await this because we don't want to block the socket handler
        # But send_frame is async, so we create a task
        asyncio.create_task(audio_loop.send_frame(image_data))

@sio.event
async def file_drop(sid, data):
    try:
        if not audio_loop:
            return
        
        file_name = data.get('name')
        file_type = data.get('type')
        file_data = data.get('data') # Base64
        
        print(f"[SERVER DEBUG] File dropped: {file_name} ({file_type})")
        
        # Pass to REX for multimodal injection
        if hasattr(audio_loop, 'handle_file_drop'):
            await audio_loop.handle_file_drop(file_name, file_type, file_data)
        
        await sio.emit('status', {'msg': f"File '{file_name}' added to context."})
    except Exception as e:
        print(f"[SERVER DEBUG] [ERR] file_drop failed: {e}")

@sio.event
async def save_memory(sid, data):
    try:
        messages = data.get('messages', [])
        if not messages:
            print("No messages to save.")
            return

        # Ensure directory exists
        memory_dir = Path("long_term_memory")
        memory_dir.mkdir(exist_ok=True)

        # Generate filename
        # Use provided filename if available, else timestamp
        provided_name = data.get('filename')
        if provided_name:
            # Simple sanitization
            if not provided_name.endswith('.txt'):
                provided_name += '.txt'
            # Prevent directory traversal
            filename = memory_dir / Path(provided_name).name 
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = memory_dir / f"memory_{timestamp}.txt"

        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            for msg in messages:
                sender = msg.get('sender', 'Unknown')
                text = msg.get('text', '')
                f.write(f"[{sender}] {text}\n")
        print(f"Conversation saved to {filename}")
        await sio.emit('status', {'msg': 'Memory Saved Successfully'})

    except Exception as e:
        print(f"Error saving memory: {e}")
        await sio.emit('error', {'msg': f"Failed to save memory: {str(e)}"})

@sio.event
async def fetch_tasks(sid, data=None):
    if service_manager:
        agent = await service_manager.get_service("tasks")
        if agent:
            await sio.emit('tasks_update', agent.get_tasks(), room=sid)

@sio.event
async def complete_task_manual(sid, data):
    task_id = data.get('id')
    if service_manager:
        agent = await service_manager.get_service("tasks")
        if agent:
            agent.update_task_status(task_id, "completed")
            await sio.emit('tasks_update', agent.get_tasks())

@sio.event
async def upload_memory(sid, data):
    print(f"Received memory upload request")
    try:
        memory_text = data.get('memory', '')
        if not memory_text:
            print("No memory data provided.")
            return

        if not audio_loop:
             print("[SERVER DEBUG] [Error] Audio loop is None. Cannot load memory.")
             await sio.emit('error', {'msg': "System not ready (Audio Loop inactive)"})
             return
        
        if not audio_loop.session:
             print("[SERVER DEBUG] [Error] Session is None. Cannot load memory.")
             await sio.emit('error', {'msg': "System not ready (No active session)"})
             return

        # Send to model
        print("Sending memory context to model...")
        context_msg = f"System Notification: The user has uploaded a long-term memory file. Please load the following context into your understanding. The format is a text log of previous conversations:\n\n{memory_text}"
        
        await audio_loop.session.send(input=context_msg, end_of_turn=True)
        print("Memory context sent successfully.")
        await sio.emit('status', {'msg': 'Memory Loaded into Context'})

    except Exception as e:
        print(f"Error uploading memory: {e}")
        await sio.emit('error', {'msg': f"Failed to upload memory: {str(e)}"})

@sio.event
async def discover_kasa(sid):
    print(f"Received discover_kasa request")
    try:
        devices = await kasa_agent.discover_devices()
        await sio.emit('kasa_devices', devices)
        await sio.emit('status', {'msg': f"Found {len(devices)} Kasa devices"})
        
        # Save to settings
        # devices is a list of full device info dicts. minimizing for storage.
        saved_devices = []
        for d in devices:
            saved_devices.append({
                "ip": d["ip"],
                "alias": d["alias"],
                "model": d["model"]
            })
        
        # Merge with existing to preserve any manual overrides? 
        # For now, just overwrite with latest scan result + previously known if we want to be fancy,
        # but user asked for "Any new devices that are scanned are added there".
        # A simple full persistence of current state is safest.
        SETTINGS["kasa_devices"] = saved_devices
        save_settings()
        print(f"[SERVER] Saved {len(saved_devices)} Kasa devices to settings.")
        
    except Exception as e:
        print(f"Error discovering kasa: {e}")
        await sio.emit('error', {'msg': f"Kasa Discovery Failed: {str(e)}"})

@sio.event
async def iterate_cad(sid, data):
    # data: { prompt: "make it bigger" }
    prompt = data.get('prompt')
    print(f"Received iterate_cad request: '{prompt}'")
    
    if not audio_loop or not audio_loop.cad_agent:
        await sio.emit('error', {'msg': "CAD Agent not available"})
        return

    try:
        # Notify user work has started
        await sio.emit('status', {'msg': 'Iterating design...'})
        await sio.emit('cad_status', {'status': 'generating'})
        
        # Call the agent with project path
        cad_output_dir = str(audio_loop.project_manager.get_current_project_path() / "cad")
        result = await audio_loop.cad_agent.iterate_prototype(prompt, output_dir=cad_output_dir)
        
        if result:
            info = f"{len(result.get('data', ''))} bytes (STL)"
            print(f"Sending updated CAD data: {info}")
            await sio.emit('cad_data', result)
            # Save to Project
            if 'file_path' in result:
                saved_path = audio_loop.project_manager.save_cad_artifact(result['file_path'], prompt)
                if saved_path:
                    print(f"[SERVER] Saved iterated CAD to {saved_path}")

            await sio.emit('status', {'msg': 'Design updated'})
        else:
            await sio.emit('error', {'msg': 'Failed to update design'})
            
    except Exception as e:
        print(f"Error iterating CAD: {e}")
        await sio.emit('error', {'msg': f"Iteration Error: {str(e)}"})

@sio.event
async def comm_action(sid, data):
    # data: { action: "accept" | "decline" }
    action = data.get('action')
    print(f"Received comm_action: {action}")
    if audio_loop and audio_loop.comm_agent:
        await audio_loop.comm_agent.handle_call(action)

@sio.event
async def apply_system_mode(sid, data):
    mode = data.get('mode')
    print(f"Received apply_system_mode: {mode}")
    if audio_loop and audio_loop.mode_manager:
        success, msg, speech = await audio_loop.mode_manager.apply_mode(mode)
        if success:
            await sio.emit('system_mode_update', {'mode': mode})
            await sio.emit('status', {'msg': speech or f"Mode applied: {mode}"})
        else:
            await sio.emit('status', {'msg': speech or msg})
            await sio.emit('error', {'msg': msg})

@sio.event
async def toggle_wake_word(sid, data):
    enabled = data.get('enabled')
    print(f"Received toggle_wake_word: {enabled}")
    SETTINGS["wake_word_enabled"] = enabled
    save_settings()
    if audio_loop:
        audio_loop.wake_word_active = enabled
        audio_loop._wake_session_is_active = not enabled
        if enabled and not audio_loop.speech_agent.porcupine:
            audio_loop.speech_agent.initialize()
    await sio.emit('status', {'msg': f"Wake word {'enabled' if enabled else 'disabled'}"})

@sio.event
async def set_wake_word_sensitivity(sid, data):
    sensitivity = data.get('sensitivity')
    print(f"Received set_wake_word_sensitivity: {sensitivity}")
    SETTINGS["wake_word_sensitivity"] = sensitivity
    save_settings()
    if audio_loop and audio_loop.speech_agent:
        # Re-init speech agent with new sensitivity if needed
        # For now just update the setting
        pass
    await sio.emit('status', {'msg': f"Wake word sensitivity set to {sensitivity}"})

@sio.event
async def generate_cad(sid, data):
    # data: { prompt: "make a cube" }
    prompt = data.get('prompt')
    print(f"Received generate_cad request: '{prompt}'")
    
    if not audio_loop or not audio_loop.cad_agent:
        await sio.emit('error', {'msg': "CAD Agent not available"})
        return

    try:
        await sio.emit('status', {'msg': 'Generating new design...'})
        await sio.emit('cad_status', {'status': 'generating'})
        
        # Use generate_prototype based on prompt with project path
        cad_output_dir = str(audio_loop.project_manager.get_current_project_path() / "cad")
        result = await audio_loop.cad_agent.generate_prototype(prompt, output_dir=cad_output_dir)
        
        if result:
            info = f"{len(result.get('data', ''))} bytes (STL)"
            print(f"Sending newly generated CAD data: {info}")
            await sio.emit('cad_data', result)


            # Save to Project
            if 'file_path' in result:
                saved_path = audio_loop.project_manager.save_cad_artifact(result['file_path'], prompt)
                if saved_path:
                    print(f"[SERVER] Saved generated CAD to {saved_path}")

            await sio.emit('status', {'msg': 'Design generated'})
        else:
            await sio.emit('error', {'msg': 'Failed to generate design'})
            
    except Exception as e:
        print(f"Error generating CAD: {e}")
        await sio.emit('error', {'msg': f"Generation Error: {str(e)}"})

@sio.event
async def prompt_web_agent(sid, data):
    # data: { prompt: "find xyz" }
    prompt = data.get('prompt')
    print(f"Received web agent prompt: '{prompt}'")
    
    if not audio_loop or not audio_loop.web_agent:
        await sio.emit('error', {'msg': "Web Agent not available"})
        return

    try:
        await sio.emit('status', {'msg': 'Web Agent running...'})
        
        # We assume web_agent has a run method or similar.
        # This might block the loop if not strictly async or offloaded.
        # Ideally web_agent.run is async.
        # And it should emit 'browser_snap' and logs automatically via hooks if setup.
        
        # We might need to launch this as a task if it's long running?
        # asyncio.create_task(audio_loop.web_agent.run(prompt))
        # But we want to catch errors here.
        
        # Based on typical agent design, run() is the entry point.
        await audio_loop.web_agent.run(prompt)
        
        await sio.emit('status', {'msg': 'Web Agent finished'})
        
    except Exception as e:
        print(f"Error running Web Agent: {e}")
        await sio.emit('error', {'msg': f"Web Agent Error: {str(e)}"})

@sio.event
async def discover_printers(sid):
    print("Received discover_printers request")
    
    # If audio_loop isn't ready yet, return saved printers from settings
    if not audio_loop or not audio_loop.printer_agent:
        saved_printers = SETTINGS.get("printers", [])
        if saved_printers:
            # Convert saved printers to the expected format
            printer_list = []
            for p in saved_printers:
                printer_list.append({
                    "name": p.get("name", p["host"]),
                    "host": p["host"],
                    "port": p.get("port", 80),
                    "printer_type": p.get("type", "unknown"),
                    "camera_url": p.get("camera_url")
                })
            print(f"[SERVER] Returning {len(printer_list)} saved printers (audio_loop not ready)")
            await sio.emit('printer_list', printer_list)
            return
        else:
            await sio.emit('printer_list', [])
            await sio.emit('status', {'msg': "Connect to A.D.A to enable printer discovery"})
            return
        
    try:
        printers = await audio_loop.printer_agent.discover_printers()
        await sio.emit('printer_list', printers)
        await sio.emit('status', {'msg': f"Found {len(printers)} printers"})
    except Exception as e:
        print(f"Error discovering printers: {e}")
        await sio.emit('error', {'msg': f"Printer Discovery Failed: {str(e)}"})

@sio.event
async def add_printer(sid, data):
    # data: { host: "192.168.1.50", name: "My Printer", type: "moonraker" }
    raw_host = data.get('host')
    name = data.get('name') or raw_host
    ptype = data.get('type', "moonraker")
    
    # Parse port if present
    if ":" in raw_host:
        host, port_str = raw_host.split(":")
        port = int(port_str)
    else:
        host = raw_host
        port = 80
    
    print(f"Received add_printer request: {host}:{port} ({ptype})")
    
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
        
    try:
        # Add manually
        camera_url = data.get('camera_url')
        printer = audio_loop.printer_agent.add_printer_manually(name, host, port=port, printer_type=ptype, camera_url=camera_url)
        
        # Save to settings
        new_printer_config = {
            "name": name,
            "host": host,
            "port": port,
            "type": ptype,
            "camera_url": camera_url
        }
        
        # Check if already exists to avoid duplicates
        exists = False
        for p in SETTINGS.get("printers", []):
            if p["host"] == host and p["port"] == port:
                exists = True
                break
        
        if not exists:
            if "printers" not in SETTINGS:
                SETTINGS["printers"] = []
            SETTINGS["printers"].append(new_printer_config)
            save_settings()
            print(f"[SERVER] Saved printer {name} to settings.")
        
        # Probe to confirm/correct type
        print(f"Probing {host} to confirm type...")
        # Try port 7125 (Moonraker) and 4408 (Fluidd/K1) 
        ports_to_try = [80, 7125, 4408]
        
        actual_type = "unknown"
        for port in ports_to_try:
             found_type = await audio_loop.printer_agent._probe_printer_type(host, port)
             if found_type.value != "unknown":
                 actual_type = found_type
                 # Update port if different
                 if port != 80:
                     printer.port = port
                 break
        
        if actual_type != "unknown" and actual_type != printer.printer_type:
             printer.printer_type = actual_type
             print(f"Corrected type to {actual_type.value} on port {printer.port}")
             
        # Refresh list for everyone
        printers = [p.to_dict() for p in audio_loop.printer_agent.printers.values()]
        await sio.emit('printer_list', printers)
        await sio.emit('status', {'msg': f"Added printer: {name}"})
        
    except Exception as e:
        print(f"Error adding printer: {e}")
        await sio.emit('error', {'msg': f"Failed to add printer: {str(e)}"})

@sio.event
async def print_stl(sid, data):
    print(f"Received print_stl request: {data}")
    # data: { stl_path: "path/to.stl" | "current", printer: "name_or_ip", profile: "optional" }
    
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
        
    try:
        stl_path = data.get('stl_path', 'current')
        printer_name = data.get('printer')
        profile = data.get('profile')
        
        if not printer_name:
             await sio.emit('error', {'msg': "No printer specified"})
             return
             
        await sio.emit('status', {'msg': f"Preparing print for {printer_name}..."})
        
        # Get current project path for resolution
        current_project_path = None
        if audio_loop and audio_loop.project_manager:
            current_project_path = str(audio_loop.project_manager.get_current_project_path())
            print(f"[SERVER DEBUG] Using project path: {current_project_path}")

        # Resolve STL path before slicing so we can preview it
        resolved_stl = audio_loop.printer_agent._resolve_file_path(stl_path, current_project_path)
        
        if resolved_stl and os.path.exists(resolved_stl):
            # Open the STL in the CAD module for preview
            try:
                import base64
                with open(resolved_stl, 'rb') as f:
                    stl_data = f.read()
                stl_b64 = base64.b64encode(stl_data).decode('utf-8')
                stl_filename = os.path.basename(resolved_stl)
                
                print(f"[SERVER] Opening STL in CAD module: {stl_filename}")
                await sio.emit('cad_data', {
                    'format': 'stl',
                    'data': stl_b64,
                    'filename': stl_filename
                })
            except Exception as e:
                print(f"[SERVER] Warning: Could not preview STL: {e}")
        
        # Progress Callback
        async def on_slicing_progress(percent, message):
            await sio.emit('slicing_progress', {
                'printer': printer_name,
                'percent': percent,
                'message': message
            })
            if percent < 100:
                 await sio.emit('status', {'msg': f"Slicing: {percent}%"})

        result = await audio_loop.printer_agent.print_stl(
            stl_path, 
            printer_name, 
            profile,
            progress_callback=on_slicing_progress,
            root_path=current_project_path
        )
        
        await sio.emit('print_result', result)
        await sio.emit('status', {'msg': f"Print Job: {result.get('status', 'unknown')}"})
        
    except Exception as e:
        print(f"Error printing STL: {e}")
        await sio.emit('error', {'msg': f"Print Failed: {str(e)}"})

@sio.event
async def get_slicer_profiles(sid):
    """Get available OrcaSlicer profiles for manual selection."""
    print("Received get_slicer_profiles request")
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
    
    try:
        profiles = audio_loop.printer_agent.get_available_profiles()
        await sio.emit('slicer_profiles', profiles)
    except Exception as e:
        print(f"Error getting slicer profiles: {e}")
        await sio.emit('error', {'msg': f"Failed to get profiles: {str(e)}"})

@sio.event
async def control_kasa(sid, data):
    # data: { ip, action: "on"|"off"|"brightness"|"color", value: ... }
    ip = data.get('ip')
    action = data.get('action')
    print(f"Kasa Control: {ip} -> {action}")
    
    try:
        success = False
        if action == "on":
            success = await kasa_agent.turn_on(ip)
        elif action == "off":
            success = await kasa_agent.turn_off(ip)
        elif action == "brightness":
            val = data.get('value')
            success = await kasa_agent.set_brightness(ip, val)
        elif action == "color":
            # value is {h, s, v} - convert to tuple for set_color
            h = data.get('value', {}).get('h', 0)
            s = data.get('value', {}).get('s', 100)
            v = data.get('value', {}).get('v', 100)
            success = await kasa_agent.set_color(ip, (h, s, v))
        
        if success:
            await sio.emit('kasa_update', {
                'ip': ip,
                'is_on': True if action == "on" else (False if action == "off" else None),
                'brightness': data.get('value') if action == "brightness" else None,
            })
 
        else:
             await sio.emit('error', {'msg': f"Failed to control device {ip}"})

    except Exception as e:
         print(f"Error controlling kasa: {e}")
         await sio.emit('error', {'msg': f"Kasa Control Error: {str(e)}"})

@app.get("/market_pulse")
async def market_pulse_endpoint(request: Request):
    """Fetch live market data (Commodities, News)."""
    try:
        stock_agent = await service_manager.get_service("stock")
        if not stock_agent:
            raise Exception("Stock Service Not Ready")
        data = await stock_agent.get_market_pulse()
        return data
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@sio.event
async def get_settings(sid):
    await sio.emit('settings', SETTINGS)

@sio.event
async def update_settings(sid, data):
    # Generic update
    print(f"Updating settings: {data}")
    
    # Handle specific keys if needed
    if "tool_permissions" in data:
        SETTINGS["tool_permissions"].update(data["tool_permissions"])
        if audio_loop:
            audio_loop.update_permissions(SETTINGS["tool_permissions"])
            
    if "face_auth_enabled" in data:
        SETTINGS["face_auth_enabled"] = data["face_auth_enabled"]
        # If turned OFF, maybe emit auth status true?
        if not data["face_auth_enabled"]:
             await sio.emit('auth_status', {'authenticated': True})
             # Stop auth loop if running?
             if authenticator:
                 authenticator.stop() 

    if "camera_flipped" in data:
        SETTINGS["camera_flipped"] = data["camera_flipped"]
        print(f"[SERVER] Camera flip set to: {data['camera_flipped']}")

    save_settings()
    # Broadcast new full settings
    await sio.emit('settings', SETTINGS)


# Deprecated/Mapped for compatibility if frontend still uses specific events
@sio.event
async def get_tool_permissions(sid):
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

@sio.event
async def update_tool_permissions(sid, data):
    print(f"Updating permissions (legacy event): {data}")
    SETTINGS["tool_permissions"].update(data)
    save_settings()
    
    if audio_loop:
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
    # Broadcast update to all
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

@sio.event
async def get_settings(sid):
    print(f"Received get_settings request from {sid}")
    # Return relevant settings, avoiding sensitive info if any (though currently none really)
    # We specifically need tool_permissions
    await sio.emit('settings', SETTINGS)

@sio.event
async def update_permissions(sid, data):
    # data: { "desktop_qa": True, "autonomous_control": False, ... }
    print(f"Received permission update: {data}")
    
    # Update global settings
    if "tool_permissions" not in SETTINGS:
        SETTINGS["tool_permissions"] = {}
        
    SETTINGS["tool_permissions"].update(data)
    save_settings()
    
    # Update active loop if running
    if audio_loop:
        audio_loop.update_permissions(data)
        
    # Broadcast new settings to all clients (in case of multiple windows)
    await sio.emit('settings', SETTINGS)

from fastapi import UploadFile, File, BackgroundTasks

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Handle file uploads for Visual Cortex analysis.
    """
    try:
        print(f"[SERVER] Received upload: {file.filename} ({file.content_type})")
        
        # 1. Save to temp
        temp_dir = os.path.join(BASE_DIR, "temp_uploads")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        file_path = os.path.join(temp_dir, file.filename)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        # 2. Process File
        from file_processor import FileProcessor
        processor = FileProcessor()
        
        # Analyze
        analysis_result = await processor.process_file(file_path, file.content_type)
        
        # 3. Inject Context
        if audio_loop:
            audio_loop.add_context_item(analysis_result)
            print(f"[SERVER] Injected {len(analysis_result)} chars of context into AudioLoop.")
        else:
            print("[SERVER] AudioLoop not ready to receive context.")

        # 4. Cleanup (in background or immediately)
        try:
            os.remove(file_path)
        except:
            pass
            
        return {"status": "success", "message": f"File analyzed. Context added.", "summary": analysis_result[:100] + "..."}
        
    except Exception as e:
        print(f"[SERVER] Upload failed: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@sio.event
async def get_ollama_models(sid):
    print(f"[SOCKET] Sid {sid} requested Ollama models")
    if service_manager:
        try:
            ollama = await service_manager.get_service("ollama")
            if ollama:
                print(f"[SOCKET] Ollama service found, fetching models...")
                models = await ollama.get_models()
                print(f"[SOCKET] Successfully found {len(models)} models. Broadcasting...")
                await sio.emit('ollama_models', models)
            else:
                print("[SOCKET] [ERR] Ollama service NOT found in ServiceManager")
                await sio.emit('ollama_models', [], room=sid)
        except Exception as e:
            print(f"[SOCKET] [ERR] Exception in get_ollama_models: {e}")
            traceback.print_exc()
            await sio.emit('ollama_models', [], room=sid)
    else:
        print("[SOCKET] [ERR] ServiceManager NOT initialized")
        await sio.emit('ollama_models', [], room=sid)

@sio.event
async def switch_llm_provider(sid, data):
    provider = data.get('provider') # 'gemini' or 'ollama'
    if audio_loop:
        audio_loop.llm_provider = provider
        await sio.emit('llm_provider_update', {'provider': provider})
        await sio.emit('status', {'msg': f"Switched LLM Provider to {provider.upper()}"})

@sio.event
async def set_ollama_model(sid, data):
    model = data.get('model')
    if service_manager:
        ollama = await service_manager.get_service("ollama")
        if ollama:
            ollama.current_model = model
            await sio.emit('status', {'msg': f"Ollama model set to {model}"})

if __name__ == "__main__":
    # When frozen, we must pass the app object, not the string
    print(f"[SERVER] Starting R.E.X Backend on 127.0.0.1:8000...")
    uvicorn.run(
        app_socketio,
        host="127.0.0.1", 
        port=8000, 
        reload=False, 
        loop="asyncio"
    )
