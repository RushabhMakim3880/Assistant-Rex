import asyncio
import base64
import io
import os
import sys
import traceback
from dotenv import load_dotenv
import cv2
import pyaudio
import PIL.Image
import mss
import argparse
import numpy as np
import time

from google import genai
from google.genai import types

if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

from tools import tools_list

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_MODE = "camera"

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not found in environment variables.")
        # Create a dummy client or handle gracefully? 
        # Ideally we should let the audio loop fail later or prompt user?
        # For now, let's allow import but fail on usage.
        client = None
    else:
        client = genai.Client(http_options={"api_version": "v1beta"}, api_key=api_key)
except Exception as e:
    print(f"[ERROR] Failed to initialize Gemini Client: {e}")
    client = None

def get_gemini_client():
    """Utility to expose the module-level Gemini client."""
    return client

# Function definitions
generate_cad = {
    "name": "generate_cad",
    "description": "Generates a 3D CAD model based on a prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The description of the object to generate."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

run_web_agent = {
    "name": "run_web_agent",
    "description": "Opens a web browser and performs a task according to the prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The detailed instructions for the web browser agent."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

create_project_tool = {
    "name": "create_project",
    "description": "Creates a new project folder to organize files.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the new project."}
        },
        "required": ["name"]
    }
}

switch_project_tool = {
    "name": "switch_project",
    "description": "Switches the current active project context.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the project to switch to."}
        },
        "required": ["name"]
    }
}

list_projects_tool = {
    "name": "list_projects",
    "description": "Lists all available projects.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

list_smart_devices_tool = {
    "name": "list_smart_devices",
    "description": "Lists all available smart home devices (lights, plugs, etc.) on the network.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

control_light_tool = {
    "name": "control_light",
    "description": "Controls a smart light device.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target": {
                "type": "STRING",
                "description": "The IP address of the device to control. Always prefer the IP address over the alias for reliability."
            },
            "action": {
                "type": "STRING",
                "description": "The action to perform: 'turn_on', 'turn_off', or 'set'."
            },
            "brightness": {
                "type": "INTEGER",
                "description": "Optional brightness level (0-100)."
            },
            "color": {
                "type": "STRING",
                "description": "Optional color name (e.g., 'red', 'cool white') or 'warm'."
            }
        },
        "required": ["target", "action"]
    }
}

discover_printers_tool = {
    "name": "discover_printers",
    "description": "Discovers 3D printers available on the local network.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

print_stl_tool = {
    "name": "print_stl",
    "description": "Prints an STL file to a 3D printer. Handles slicing the STL to G-code and uploading to the printer.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "stl_path": {"type": "STRING", "description": "Path to STL file, or 'current' for the most recent CAD model."},
            "printer": {"type": "STRING", "description": "Printer name or IP address."},
            "profile": {"type": "STRING", "description": "Optional slicer profile name."}
        },
        "required": ["stl_path", "printer"]
    }
}

get_print_status_tool = {
    "name": "get_print_status",
    "description": "Gets the current status of a 3D printer including progress, time remaining, and temperatures.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "printer": {"type": "STRING", "description": "Printer name or IP address."}
        },
        "required": ["printer"]
    }
}

iterate_cad_tool = {
    "name": "iterate_cad",
    "description": "Modifies or iterates on the current CAD design based on user feedback. Use this when the user asks to adjust, change, modify, or iterate on the existing 3D model (e.g., 'make it taller', 'add a handle', 'reduce the thickness').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The changes or modifications to apply to the current design."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}



analyze_stock_tool = {
    "name": "analyze_stock",
    "description": "Performs a deep-dive stock analysis with short-term (1, 3, 5, 7 day) price predictions and Buy/Sell/Wait guidance. Use this when the user asks for targets, directional forecasts, or advice like 'Should I buy or wait?'.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "symbol": {"type": "STRING", "description": "The stock ticker symbol (e.g., 'RELIANCE', 'INFY', 'TATASTEEL'). Defaults to NSE if no suffix provided."}
        },
        "required": ["symbol"]
    },
    "behavior": "NON_BLOCKING"
}

execute_workflow_tool = {
    "name": "execute_workflow",
    "description": "Executes a multi-step desktop workflow (e.g. 'Open Notepad and write Python code', 'Create a React project in VS Code'). Use this for ANY task that requires more than just launching an app.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The full description of the workflow to be executed."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

from desktop_agent import DesktopAgent, desktop_tools
from system_agent import SystemAgent, system_maintenance_tools
from speech_agent import SpeechAgent, speech_tools
from communications_agent import communication_tools
from ethical_hacking_agent import EthicalHackingAgent, hacking_tools
from semantic_search_agent import SemanticSearchAgent, semantic_search_tools

calendar_tools = [
     {
        "name": "list_calendar_events",
        "description": "Lists the upcoming events from the user's primary Google Calendar.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "create_calendar_event",
        "description": "Creates a new event in the user's Google Calendar.",
        "parameters": {
            "type": "OBJECT", 
            "properties": {
                "summary": {"type": "STRING", "description": "Title of the event"},
                "start_time": {"type": "STRING", "description": "Start time in ISO format (e.g. 2023-10-27T10:00:00)"},
                "end_time": {"type": "STRING", "description": "End time in ISO format (optional)"},
                "description": {"type": "STRING", "description": "Description of the event"}
            },
            "required": ["summary", "start_time"]
        }
    }
]

visual_memory_tools = [
    {
        "name": "query_visual_history",
        "description": "Searches the user's screen history (Visual Memory). Useful when the user asks 'what was I doing?' or 'find the file I was looking at'.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "The search term (e.g., 'Python docs', 'Spotify', 'Budget spreadsheet')."}
            },
            "required": ["query"]
        }
    }
]

visual_macro_tools = [
     {
        "name": "start_recording_macro",
        "description": "Starts recording a new workflow macro. Provide a unique name.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Name of the macro (e.g., 'pdf_conversion')."}
            },
            "required": ["name"]
        }
    },
    {
        "name": "stop_recording_macro",
        "description": "Stops the currently recording macro.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "replay_macro",
        "description": "Replays a recorded macro using visual recognition.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                 "name": {"type": "STRING", "description": "Name of the macro to replay."}
            },
            "required": ["name"]
        }
    }
]

gen_ui_tools = [
     {
        "name": "generate_dashboard",
        "description": "Generates a temporary, single-file HTML/JS dashboard/app to visualize data or solve a specific problem.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {"type": "STRING", "description": "Description of the app functionality (e.g., 'Compare GPU prices', 'Convert currency dashboard')."},
                "data_context": {"type": "STRING", "description": "The raw data to visualize (JSON or text)."}
            },
            "required": ["prompt"]
        }
    }
]

tools = [{'google_search': {}}, {"function_declarations": [generate_cad, run_web_agent, create_project_tool, switch_project_tool, list_projects_tool, list_smart_devices_tool, control_light_tool, discover_printers_tool, print_stl_tool, get_print_status_tool, iterate_cad_tool, analyze_stock_tool, execute_workflow_tool] + tools_list[0]['function_declarations'][1:] + speech_tools + system_maintenance_tools + communication_tools + hacking_tools + desktop_tools + semantic_search_tools + calendar_tools + visual_memory_tools + visual_macro_tools + gen_ui_tools}]

# --- CONFIG UPDATE: Enabled Transcription ---
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    # We switch these from [] to {} to enable them with default settings
    output_audio_transcription={}, 
    input_audio_transcription={},
    system_instruction="Your name is R.E.X., which stands for Real-time Executive Assistant. "
        "You have a witty and charming personality. "
        "Your creator is Rushabh Makim, and you address him as 'Sir'. "
        "When answering, respond using complete and concise sentences to keep a quick pacing and keep the conversation flowing. "
        "You have a fun personality. "
        "For complex multi-step tasks involving desktop applications, always use the 'execute_workflow' tool instead of basic 'launch_app'.",
    tools=tools,
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name="Kore"
            )
        )
    )
)

import concurrent.futures
import pyttsx3
from audio_engine import create_audio_engine

# pya representation removed (handled by AudioEngine process)

from cad_agent import CadAgent
from web_agent import WebAgent
from kasa_agent import KasaAgent
from printer_agent import PrinterAgent
from stock_agent import StockAgent

class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE, on_audio_data=None, on_video_frame=None, on_cad_data=None, on_web_data=None, on_transcription=None, on_tool_confirmation=None, on_cad_status=None, on_cad_thought=None, on_project_update=None, on_task_update=None, on_device_update=None, on_stock_data=None, on_error=None, on_minimize=None, on_restore=None, input_device_index=None, input_device_name=None, output_device_index=None, output_device_name=None, kasa_agent=None, cad_agent=None, web_agent=None, printer_agent=None, project_manager=None, desktop_agent=None, skill_manager=None, terminal_agent=None, project_spawner=None, visual_memory=None, cross_project=None, system_agent=None, comm_agent=None, task_agent=None, organizer_agent=None, clipboard_agent=None, lifestyle_agent=None, ollama_agent=None, calendar_agent=None, macro_agent=None, gen_ui_agent=None, stock_agent=None, hacking_agent=None, semantic_search=None, speech_agent=None, tool_permissions={}, settings={}):
        self.video_mode = video_mode
        self.on_audio_data = on_audio_data
        self.on_video_frame = on_video_frame
        self.on_cad_data = on_cad_data
        self.on_web_data = on_web_data
        self.on_transcription = on_transcription
        self.on_tool_confirmation = on_tool_confirmation 
        self.on_cad_status = on_cad_status
        self.on_cad_thought = on_cad_thought
        self.on_project_update = on_project_update
        self.on_task_update = on_task_update
        self.on_device_update = on_device_update
        self.on_stock_data = on_stock_data
        self.on_error = on_error
        self.on_minimize = on_minimize
        self.on_restore = on_restore
        self.input_device_index = input_device_index
        self.input_device_name = input_device_name
        self.output_device_index = output_device_index
        self.output_device_name = output_device_name

        self.audio_in_queue = None
        self.out_queue = None
        self.paused = False

        self.chat_buffer = {"sender": None, "text": ""} # For aggregating chunks
        
        # Track last transcription text to calculate deltas (Gemini sends cumulative text)
        self._last_input_transcription = ""
        self._last_output_transcription = ""

        self.audio_in_queue = None
        self.out_queue = None
        self.paused = False

        self.session = None
        
        # Create CadAgent with thought callback
        def handle_cad_thought(thought_text):
            if self.on_cad_thought:
                self.on_cad_thought(thought_text)
        
        def handle_cad_status(status_info):
            if self.on_cad_status:
                self.on_cad_status(status_info)
        
        self.cad_agent = cad_agent
        self.web_agent = web_agent
        self.kasa_agent = kasa_agent
        self.system_agent = system_agent
        self.comm_agent = comm_agent
        self.desktop_agent = desktop_agent
        self.skill_manager = skill_manager
        self.terminal_agent = terminal_agent
        self.project_spawner = project_spawner
        self.visual_memory = visual_memory
        self.cross_project = cross_project
        self.task_agent = task_agent
        self.organizer_agent = organizer_agent
        self.clipboard_agent = clipboard_agent
        self.lifestyle_agent = lifestyle_agent
        self.ollama_agent = ollama_agent
        self.calendar_agent = calendar_agent
        self.macro_agent = macro_agent
        self.gen_ui_agent = gen_ui_agent
        
        # Visual Cortex Memory
        self.pending_context = []
        
        self.settings = settings
        self.speech_agent = speech_agent or SpeechAgent()
        self.wake_word_active = self.settings.get("wake_word_enabled", False)
        self._wake_session_is_active = not self.wake_word_active
        self.printer_agent = printer_agent or PrinterAgent()
        self.stock_agent = stock_agent or StockAgent()
        self.hacking_agent = hacking_agent or EthicalHackingAgent()
        self.semantic_search = semantic_search or SemanticSearchAgent(api_key=None)
        
        from workflow_agent import WorkflowAgent
        self.workflow_agent = WorkflowAgent(self.desktop_agent, gemini_client=client)

        self.send_text_task = None
        self.stop_event = asyncio.Event()
        
        self.permissions = tool_permissions 
        self._pending_confirmations = {}

        # Video buffering state
        self._latest_image_payload = None
        # VAD State
        self._is_speaking = False
        self._silence_start_time = None
        
        # Initialize ProjectManager
        from project_manager import ProjectManager
        # Assuming we are running from backend/ or root? 
        # Using abspath of current file to find root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # If rex.py is in backend/, project root is one up
        project_root = os.path.dirname(current_dir)
        self.project_manager = ProjectManager(project_root)
        self.privacy_mode = False # If True, force local LLM
        self.ollama = ollama_agent # Set from constructor or server
        
        # Zero-Latency Audio Engine - Initialized in run()
        self.audio_process = None
        self.audio_queue = None
        
        # Ack Executor
        self.ack_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Barge-in Prevention State
        self._is_rex_speaking = False  # Track if REX is currently outputting audio
        self._rex_speech_timer = None  # Timer to detect when REX stops speaking
        self._mute_during_rex_speech = True  # Default: mute mic when REX speaks
        self._barge_in_threshold = 5000  # RMS threshold for allowing interruptions (higher = quieter interruptions blocked)
        self._normal_vad_threshold = 100  # LOWERED to 100 for high sensitivity (Default was 800) -- REX FIX
        self._mute_buffer_duration = 1.0  # Seconds to fully mute after REX starts speaking (prevent loopback)
        self._rex_speech_start_time = None  # Track when REX started speaking for mute buffer
        
        # Ack Executor
        self.ack_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        # Sync Initial Project State
        if self.on_project_update:
            # We need to defer this slightly or just call it. 
            # Since this is init, loop might not be running, but on_project_update in server.py uses asyncio.create_task which needs a loop.
            # We will handle this by calling it in run() or just print for now.
            pass

    def add_context_item(self, text_content):
        """Adds a high-priority context item (file analysis) to be consumed immediately."""
        self.pending_context.append(text_content)
        # Send to Gemini immediately regarding the file
        if self.session:
            asyncio.create_task(self.send_text(text_content))
        
        # Audio Ack
        asyncio.create_task(self.quick_response("I've analyzed the file."))

    def flush_chat(self):
        """Forces the current chat buffer to be written to log."""
        if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
            self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
            self.chat_buffer = {"sender": None, "text": ""}
        # Reset transcription tracking for new turn
        self._last_input_transcription = ""
        self._last_output_transcription = ""

    def update_permissions(self, new_perms):
        print(f"[REX DEBUG] [CONFIG] Updating tool permissions: {new_perms}")
        self.permissions.update(new_perms)

    def set_paused(self, paused):
        self.paused = paused

    def set_barge_in_prevention(self, enabled, barge_in_threshold=2000):
        """Enable or disable barge-in prevention (mute mic while REX speaks)
        
        Args:
            enabled: If True, mutes microphone when REX is speaking
            barge_in_threshold: RMS threshold for allowing interruptions (default: 2000)
                               Lower = more sensitive to interruptions
                               Higher = requires louder interruptions
        """
        self._mute_during_rex_speech = enabled
        self._barge_in_threshold = barge_in_threshold
        print(f"[REX DEBUG] [CONFIG] Barge-in prevention {'ENABLED' if enabled else 'DISABLED'} (Threshold: {barge_in_threshold})")

    def quick_response(self, text):
        """
        Uses a local TTS engine (pyttsx3) for immediate, zero-latency acknowledgments.
        Runs in a separate thread to avoid blocking the main loop.
        """
        print(f"[REX DEBUG] [ACK] Quick Response: '{text}'")
        self.ack_executor.submit(self._speak_local, text)

    def _speak_local(self, text):
        """Internal method to run pyttsx3 in a thread."""
        try:
            # Initialize locally in the thread (COM object requirement on Windows often prefers this)
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[REX DEBUG] [ACK] Local TTS Failed: {e}")

    def stop(self):
        """Stops the audio loop and helper processes."""
        self.stop_event.set()
        
        # Cleanup internal agents that might have sessions
        if hasattr(self, 'speech_agent') and self.speech_agent:
            try: self.speech_agent.cleanup()
            except: pass
            
        if hasattr(self, 'printer_agent') and hasattr(self.printer_agent, 'shutdown'):
            asyncio.create_task(self.printer_agent.shutdown())
            
        if hasattr(self, 'audio_process') and self.audio_process.is_alive():
            # Send Stop Signal
            # self.audio_queue.put(None) # Sentinel 
            # Force terminate for speed
            self.audio_process.terminate()
            self.audio_process.join()
        
        if hasattr(self, 'ack_executor'):
            self.ack_executor.shutdown(wait=False)

    def resolve_tool_confirmation(self, request_id, confirmed):
        print(f"[REX DEBUG] [RESOLVE] resolve_tool_confirmation called. ID: {request_id}, Confirmed: {confirmed}")
        if request_id in self._pending_confirmations:
            future = self._pending_confirmations[request_id]
            if not future.done():
                print(f"[REX DEBUG] [RESOLVE] Future found and pending. Setting result to: {confirmed}")
                future.set_result(confirmed)
            else:
                 print(f"[REX DEBUG] [WARN] Request {request_id} future already done. Result: {future.result()}")
        else:
            print(f"[REX DEBUG] [WARN] Confirmation Request {request_id} not found in pending dict. Keys: {list(self._pending_confirmations.keys())}")

    def clear_audio_queue(self):
        """Clears the queue of pending audio chunks to stop playback immediately."""
        try:
            # 1. Pulse RESET to the playback engine (for local buffer)
            from audio_engine import RESET_SIGNAL
            self.audio_in_queue.put_nowait(RESET_SIGNAL)
            
            # 2. Clear the communication queue
            count = 0
            while not self.audio_in_queue.empty():
                try:
                    self.audio_in_queue.get_nowait()
                    count += 1
                except: break
                
            if count > 0:
                print(f"[REX DEBUG] [AUDIO] Cleared {count} chunks from playback queue due to interruption.")
        except Exception as e:
            print(f"[REX DEBUG] [ERR] Failed to clear audio queue: {e}")

    async def send_frame(self, frame_data):
        # Update the latest frame payload
        if isinstance(frame_data, bytes):
            b64_data = base64.b64encode(frame_data).decode('utf-8')
        else:
            b64_data = frame_data 

        # Store as the designated "next frame to send"
        self._latest_image_payload = {"mime_type": "image/jpeg", "data": b64_data}
        # No event signal needed - listen_audio pulls it

    async def send_realtime(self):
        try:
            while True:
                msg = await self.out_queue.get()
                if self.session:
                    try:
                        await self.session.send(input=msg, end_of_turn=False)
                    except Exception as e:
                        print(f"[REX DEBUG] [ERR] send_realtime failed: {e}")
                        # If critical connection error, maybe break? 
                        # But for now logging is enough to prevent crash loop.
                        # Break to restart loop? The outer loop (run) handles reconnect.
                        break 
        except Exception as e:
            print(f"[REX DEBUG] [ERR] send_realtime loop error: {e}")

    async def send_text(self, text):
        """Sends a text message to the Gemini session."""
        print(f"[REX DEBUG] [CHAT] Sending text: '{text}'")
        try:
            if self.session:
                await self.session.send(input=text, end_of_turn=True)
            else:
                print("[REX DEBUG] [CHAT] Session not active. Queuing text.")
                # Optional: Queue or discard? For mobile, we might want to notify user.
        except Exception as e:
             print(f"[REX DEBUG] [ERR] Failed to send text: {e}")

    async def process_text(self, text, source="unknown"):
        """Alias for send_text to support mobile bridge and other inputs."""
        print(f"[REX DEBUG] [INPUT] Received text from {source}: {text}")
        await self.send_text(text)
             # We assume main loop will handle reconnect if needed.

    async def handle_file_drop(self, name, mime_type, b64_data):
        """Processes a file dropped onto the REX interface."""
        print(f"[REX DEBUG] [FILE] Processing dropped file: {name} ({mime_type})")
        
        try:
            if mime_type.startswith('image/'):
                # Inject as a vision frame immediately
                payload = {"mime_type": mime_type, "data": b64_data}
                if self.session:
                    await self.session.send(input=payload, end_of_turn=True)
                    print(f"[REX DEBUG] [FILE] Image injected into Gemini context.")
            else:
                # Treat as a document/text
                try:
                    raw_data = base64.b64decode(b64_data)
                    content = raw_data.decode('utf-8', errors='ignore')
                    
                    if self.session:
                        await self.session.send(input=f"System Notification: User dropped a file '{name}'. Content:\n\n{content}", end_of_turn=True)
                        print(f"[REX DEBUG] [FILE] Text content injected into Gemini context.")
                except Exception as e:
                    print(f"[REX DEBUG] [FILE] Failed to decode text file: {e}")
        except Exception as e:
            print(f"[REX DEBUG] [FILE] Error handling file drop: {e}")

    def _resolve_device(self, name_to_find, kind='input'):
        """Resolves a device name to a PyAudio index."""
        if not name_to_find:
            return None
            
        p = pyaudio.PyAudio()
        try:
            count = p.get_device_count()
            print(f"[REX] Attempting to find {kind} matching: '{name_to_find}'")
            
            for i in range(count):
                try:
                    info = p.get_device_info_by_index(i)
                    name = info.get('name', '')
                    channels = info.get('maxInputChannels' if kind == 'input' else 'maxOutputChannels', 0)
                    
                    if channels > 0:
                        # Simple case-insensitive check
                        if name_to_find.lower() in name.lower() or name.lower() in name_to_find.lower():
                             print(f"   [MATCH] Index {i}: {name}")
                             return i
                except Exception:
                    continue
            print(f"[REX] No match found for '{name_to_find}' ({kind}). Falling back.")
            return None
        finally:
            p.terminate()

    async def listen_audio(self):
        try:
            # Instantiate PyAudio locally for process safety (though input is usually main process)
            p = pyaudio.PyAudio()
            
            try:
                mic_info = p.get_default_input_device_info()
            except Exception as e:
                print(f"[REX] [WARN] No default input device found: {e}")
                mic_info = {"index": 0}

            # Resolve Input Device by Name
            resolved_index = self._resolve_device(self.input_device_name, kind='input')
            if resolved_index is not None:
                self.input_device_index = resolved_index
            
            # Final Device Choice
            device_index = self.input_device_index
            if device_index is None:
                print(f"[REX] Using default input device: {mic_info.get('name')} (Index {mic_info.get('index')})")
                device_index = mic_info.get('index')
            else:
                print(f"[REX] Using resolved input device index: {device_index}")

            try:
                self.audio_stream = await asyncio.to_thread(
                    p.open,
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=SEND_SAMPLE_RATE,
                    input=True,
                    input_device_index=device_index if device_index is not None else mic_info["index"],
                    frames_per_buffer=CHUNK_SIZE,
                )
            except OSError as e:
                print(f"[REX] [ERR] Failed to open audio input stream: {e}")
                print("[REX] [WARN] Audio features will be disabled. Please check microphone permissions.")
                p.terminate()
                return

            if __debug__:
                kwargs = {"exception_on_overflow": False}
            else:
                kwargs = {}
            
            # VAD Constants
            VAD_THRESHOLD = self._normal_vad_threshold  # 800 for normal speech
            SILENCE_DURATION = 0.5 # Seconds of silence to consider "done speaking"
            
            while True:
                if self.paused:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
                    
                    # Calculate RMS
                    count = len(data) // 2
                    shorts = struct.unpack(f"<{count}h", data) if count > 0 else []
                    if count > 0:
                        sum_squares = sum(s**2 for s in shorts)
                        rms = int(math.sqrt(sum_squares / count))
                    else:
                        rms = 0
                    
                    # Log RMS occasionally for debugging
                    if not hasattr(self, "_last_rms_log_time"): self._last_rms_log_time = 0
                    if time.time() - self._last_rms_log_time > 2:
                        print(f"[REX AUDIO DEBUG] RMS: {rms} (VAD Threshold: {VAD_THRESHOLD})")
                        self._last_rms_log_time = time.time()
                    
                    # Wake Word
                    if self.wake_word_active and not self._wake_session_is_active:
                        frame_len = self.speech_agent.porcupine.frame_length if self.speech_agent.porcupine else 512
                        for i in range(0, count, frame_len):
                            chunk = shorts[i : i + frame_len]
                            if len(chunk) == frame_len:
                                if self.speech_agent.process_frame(chunk) >= 0:
                                    self._wake_session_is_active = True
                                    if self.on_transcription:
                                         self.on_transcription({"sender": "System", "text": "[Wake Word Detected]"})
                                    break
                        if not self._wake_session_is_active: continue

                    if self._is_rex_speaking and self._mute_during_rex_speech:
                        if self._rex_speech_start_time and (time.time() - self._rex_speech_start_time) < self._mute_buffer_duration:
                            continue
                        if rms < self._barge_in_threshold:
                            continue
                    
                    if self.out_queue:
                        await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                    
                    if rms > VAD_THRESHOLD:
                        self._silence_start_time = None
                        if not self._is_speaking:
                            print(f"[REX DEBUG] VAD TRIGGERED (RMS: {rms})")
                            self._is_speaking = True
                            if self._latest_image_payload and self.out_queue:
                                await self.out_queue.put(self._latest_image_payload)
                    else:
                        if self._is_speaking:
                            if self._silence_start_time is None:
                                self._silence_start_time = time.time()
                            elif time.time() - self._silence_start_time > SILENCE_DURATION:
                                self._is_speaking = False
                                self._silence_start_time = None

                    if self.wake_word_active and self._wake_session_is_active:
                        if self._silence_start_time and (time.time() - self._silence_start_time) > 30:
                            self._wake_session_is_active = False

                except Exception as e:
                    print(f"Error reading audio: {e}")
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[CRITICAL] listen_audio crashed: {e}")
            traceback.print_exc()
        finally:
            if hasattr(self, 'audio_stream') and self.audio_stream:
                try: self.audio_stream.close() 
                except: pass
            if 'p' in locals():
                p.terminate()

    async def handle_cad_request(self, prompt):
        print(f"[REX DEBUG] [CAD] Background Task Started: handle_cad_request('{prompt}')")
        if self.on_cad_status:
            self.on_cad_status("generating")
            
        # Auto-create project if stuck in temp
        if self.project_manager.current_project == "temp":
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_project_name = f"Project_{timestamp}"
            print(f"[REX DEBUG] [CAD] Auto-creating project: {new_project_name}")
            
            success, msg = self.project_manager.create_project(new_project_name)
            if success:
                self.project_manager.switch_project(new_project_name)
                # Notify User (Optional, or rely on update)
                try:
                    await self.session.send(input=f"System Notification: Automatic Project Creation. Switched to new project '{new_project_name}'.", end_of_turn=False)
                    if self.on_project_update:
                         self.on_project_update(new_project_name)
                except Exception as e:
                    print(f"[REX DEBUG] [ERR] Failed to notify auto-project: {e}")

        # Get project cad folder path
        cad_output_dir = str(self.project_manager.get_current_project_path() / "cad")
        
        # Call the secondary agent with project path
        cad_data = await self.cad_agent.generate_prototype(prompt, output_dir=cad_output_dir)
        
        if cad_data:
            print(f"[REX DEBUG] [OK] CadAgent returned data successfully.")
            print(f"[REX DEBUG] [INFO] Data Check: {len(cad_data.get('vertices', []))} vertices, {len(cad_data.get('edges', []))} edges.")
            
            if self.on_cad_data:
                print(f"[REX DEBUG] [SEND] Dispatching data to frontend callback...")
                self.on_cad_data(cad_data)
                print(f"[REX DEBUG] [SENT] Dispatch complete.")
            
            # Save to Project
            if 'file_path' in cad_data:
                self.project_manager.save_cad_artifact(cad_data['file_path'], prompt)
            else:
                 # Fallback (legacy support)
                 self.project_manager.save_cad_artifact("output.stl", prompt)

            # Notify the model that the task is done - this triggers speech about completion
            completion_msg = "System Notification: CAD generation is complete! The 3D model is now displayed for the user. Let them know it's ready."
            try:
                await self.session.send(input=completion_msg, end_of_turn=True)
                print(f"[REX DEBUG] [NOTE] Sent completion notification to model.")
            except Exception as e:
                 print(f"[REX DEBUG] [ERR] Failed to send completion notification: {e}")

        else:
            print(f"[REX DEBUG] [ERR] CadAgent returned None.")
            # Optionally notify failure
            try:
                await self.session.send(input="System Notification: CAD generation failed.", end_of_turn=True)
            except Exception:
                pass



    async def handle_write_file(self, path, content):
        print(f"[REX DEBUG] [FS] Writing file: '{path}'")
        
        # Auto-create project if stuck in temp
        if self.project_manager.current_project == "temp":
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_project_name = f"Project_{timestamp}"
            print(f"[REX DEBUG] [FS] Auto-creating project: {new_project_name}")
            
            success, msg = self.project_manager.create_project(new_project_name)
            if success:
                self.project_manager.switch_project(new_project_name)
                # Notify User
                try:
                    await self.session.send(input=f"System Notification: Automatic Project Creation. Switched to new project '{new_project_name}'.", end_of_turn=False)
                    if self.on_project_update:
                         self.on_project_update(new_project_name)
                except Exception as e:
                    print(f"[REX DEBUG] [ERR] Failed to notify auto-project: {e}")
        
        # Force path to be relative to current project
        # If absolute path is provided, we try to strip it or just ignore it and use basename
        filename = os.path.basename(path)
        
        # If path contained subdirectories (e.g. "backend/server.py"), preserving that structure might be desired IF it's within the project.
        # But for safety, and per user request to "always create the file in the project", 
        # we will root it in the current project path.
        
        current_project_path = self.project_manager.get_current_project_path()
        final_path = current_project_path / filename # Simple flat structure for now, or allow relative?
        
        # If the user specifically wanted a subfolder, they might have provided "sub/file.txt".
        # Let's support relative paths if they don't start with /
        if not os.path.isabs(path):
             final_path = current_project_path / path
        
        print(f"[REX DEBUG] [FS] Resolved path: '{final_path}'")

        try:
            # Ensure parent exists
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            with open(final_path, 'w', encoding='utf-8') as f:
                f.write(content)
            result = f"File '{final_path.name}' written successfully to project '{self.project_manager.current_project}'."
        except Exception as e:
            result = f"Failed to write file '{path}': {str(e)}"

        print(f"[REX DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[REX DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_read_directory(self, path):
        print(f"[REX DEBUG] [FS] Reading directory: '{path}'")
        try:
            if not os.path.exists(path):
                result = f"Directory '{path}' does not exist."
            else:
                items = os.listdir(path)
                result = f"Contents of '{path}': {', '.join(items)}"
        except Exception as e:
            result = f"Failed to read directory '{path}': {str(e)}"

        print(f"[REX DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[REX DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_read_file(self, path):
        print(f"[REX DEBUG] [FS] Reading file: '{path}'")
        try:
            if not os.path.exists(path):
                result = f"File '{path}' does not exist."
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                result = f"Content of '{path}':\n{content}"
        except Exception as e:
            result = f"Failed to read file '{path}': {str(e)}"

        print(f"[REX DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[REX DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_web_agent_request(self, prompt):
        print(f"[REX DEBUG] [WEB] Web Agent Task: '{prompt}'")
        
        async def update_frontend(image_b64, log_text):
            if self.on_web_data:
                 self.on_web_data({"image": image_b64, "log": log_text})
                 
        # Run the web agent and wait for it to return
        result = await self.web_agent.run_task(prompt, update_callback=update_frontend)
        print(f"[REX DEBUG] [WEB] Web Agent Task Returned: {result}")
        
        # Send the final result back to the main model
        try:
             await self.session.send(input=f"System Notification: Web Agent has finished.\nResult: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[REX DEBUG] [ERR] Failed to send web agent result to model: {e}")

    async def handle_stock_request(self, symbol):
        print(f"[REX DEBUG] [STOCK] Processing analysis for: {symbol}")
        
        # analyze_stock is async, await it directly. Internal network calls are handled within.
        data = await self.stock_agent.analyze_stock(symbol)
        
        if "error" in data:
            print(f"[REX DEBUG] [STOCK] Error: {data['error']}")
            try:
                await self.session.send(input=f"System Notification: Stock Analysis Failed. {data['error']}", end_of_turn=True)
            except:
                pass
            return
            
        # Send to frontend
        if self.on_stock_data:
            print(f"[REX DEBUG] [STOCK] Sending data to frontend...")
            self.on_stock_data(data)
            
        # Notify Model
        try:
            summary = data.get('summary', 'Analysis Complete.')
            await self.session.send(input=f"System Notification: Stock Analysis Data for {symbol} has been sent to the user's screen. Summary: {summary}. Please present this to the user.", end_of_turn=True)
        except Exception as e:
            print(f"[REX DEBUG] [STOCK] Failed to notify model: {e}")

    async def handle_nmap_scan(self, target, options="-F"):
        print(f"[REX DEBUG] [HACK] Nmap Scan: {target} {options}")
        result = await self.hacking_agent.nmap_scan(target, options)
        try:
            await self.session.send(input=f"System Notification: Nmap scan results for {target}:\n{result}", end_of_turn=True)
        except Exception as e:
            print(f"[REX DEBUG] [ERR] Failed to send nmap result: {e}")

    async def handle_generate_hacking_payload(self, platform, lhost, lport, output_file):
        print(f"[REX DEBUG] [HACK] Generate Payload: {platform} {lhost}:{lport}")
        result = await self.hacking_agent.generate_payload(platform, lhost, lport, output_file)
        try:
            await self.session.send(input=f"System Notification: Payload generation result:\n{result}", end_of_turn=True)
        except Exception as e:
            print(f"[REX DEBUG] [ERR] Failed to send payload result: {e}")

    async def handle_test_website_vulnerability(self, url):
        print(f"[REX DEBUG] [HACK] SQLMap Test: {url}")
        result = await self.hacking_agent.sqlmap_test(url)
        try:
            await self.session.send(input=f"System Notification: Website vulnerability test result for {url}:\n{result}", end_of_turn=True)
        except Exception as e:
            print(f"[REX DEBUG] [ERR] Failed to send vulnerability test result: {e}")

    async def handle_locate_file(self, filename, search_path=None):
        print(f"[REX DEBUG] [SYS] Locating file: '{filename}' in '{search_path if search_path else 'All Drives'}'")
        result = await self.system_agent.locate_file(filename, search_path)
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[REX DEBUG] [ERR] Failed to send file location result: {e}")

    async def handle_execute_workflow(self, prompt):
        print(f"[REX DEBUG] [WORKFLOW] Executing: '{prompt}'")
        result = await self.workflow_agent.execute_workflow(prompt)
        try:
             await self.session.send(input=f"System Notification: Workflow Finished.\nResult: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[REX DEBUG] [ERR] Failed to send workflow result: {e}")

    async def generate_content_with_fallback(self, prompt, system_instruction=None, model="gemini-2.0-flash-exp"):
        """Generates content using Gemini, with a fallback to Ollama if quota exceeded or privacy mode active."""
        
        # Check Privacy Mode
        if self.privacy_mode:
            print("[REX] Privacy Mode Active: Routing to local Ollama.")
            if self.ollama:
                return await self.ollama.chat(prompt, system_prompt=system_instruction)
            return {"error": "Privacy Mode enabled but Ollama is not available."}

        try:
            # 1. Attempt Gemini
            from google.genai import types
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system_instruction) if system_instruction else None
            )
            return response.text
        except Exception as e:
            error_str = str(e).upper()
            if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str or "QUOTA" in error_str:
                print(f"[REX] Gemini Quota Exceeded. Falling back to local Ollama. Error: {e}")
                if self.ollama:
                    local_resp = await self.ollama.chat(prompt, system_prompt=system_instruction)
                    if "response" in local_resp:
                        return local_resp["response"]
                    return local_resp.get("error", "Ollama fallback failed.")
            
            print(f"[REX] LLM Generation failed: {e}")
            return f"Error: {e}"

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        try:
            while True:
                turn = self.session.receive()
                async for response in turn:
                    # 1. Handle Audio Data
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                        # NOTE: 'continue' removed here to allow processing transcription/tools in same packet

                    # 2. Handle Transcription (User & Model)
                    if response.server_content:
                        if response.server_content.input_transcription:
                            transcript = response.server_content.input_transcription.text
                            if transcript:
                                # Skip if this is an exact duplicate event
                                if transcript != self._last_input_transcription:
                                    # Calculate delta (Gemini may send cumulative or chunk-based text)
                                    delta = transcript
                                    if transcript.startswith(self._last_input_transcription):
                                        delta = transcript[len(self._last_input_transcription):]
                                    self._last_input_transcription = transcript
                                    
                                    # Only send if there's new text
                                    if delta:
                                        # User is speaking, so interrupt model playback!
                                        self.clear_audio_queue()

                                        # Send to frontend (Streaming)
                                        if self.on_transcription:
                                             self.on_transcription({"sender": "User", "text": delta})
                                        
                                        # Buffer for Logging
                                        if self.chat_buffer["sender"] != "User":
                                            # Flush previous if exists
                                            if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                                self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
                                            # Start new
                                            self.chat_buffer = {"sender": "User", "text": delta}
                                        else:
                                            # Append
                                            self.chat_buffer["text"] += delta
                        
                        if response.server_content.output_transcription:
                            transcript = response.server_content.output_transcription.text
                            if transcript:
                                # Skip if this is an exact duplicate event
                                if transcript != self._last_output_transcription:
                                    # Calculate delta (Gemini may send cumulative or chunk-based text)
                                    delta = transcript
                                    if transcript.startswith(self._last_output_transcription):
                                        delta = transcript[len(self._last_output_transcription):]
                                    self._last_output_transcription = transcript
                                    
                                    # Only send if there's new text
                                    if delta:
                                        # Send to frontend (Streaming)
                                        if self.on_transcription:
                                             self.on_transcription({"sender": "REX", "text": delta})
                                        
                                        # Buffer for Logging
                                        if self.chat_buffer["sender"] != "REX":
                                            # Flush previous
                                            if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                                self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
                                            # Start new
                                            self.chat_buffer = {"sender": "REX", "text": delta}
                                        else:
                                            # Append
                                            self.chat_buffer["text"] += delta
                        
                        # 2.5 Handle Model Turn Parts (Direct Text/Thoughts)
                        if response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if part.text:
                                    # Fallback transcription if output_transcription didn't catch it
                                    if part.text != self._last_output_transcription:
                                        print(f"[REX DEBUG] [MODEL TEXT] {part.text}")
                                        # Deduplicate with output_transcription if possible
                                        if not self._last_output_transcription.endswith(part.text):
                                            if self.on_transcription:
                                                 self.on_transcription({"sender": "REX", "text": part.text})
                                
                                # Explicitly handle 'thought' part to resolve SDK warnings
                                try:
                                    if hasattr(part, 'thought') and part.thought:
                                        thought_text = part.thought
                                        print(f"[REX DEBUG] [THOUGHT] {thought_text}")
                                        if self.on_cad_thought:
                                            self.on_cad_thought(thought_text)
                                except (AttributeError, Exception):
                                    pass

                    # 3. Handle Tool Calls
                    if response.tool_call:
                        print("The tool was called")
                        function_responses = []
                        for fc in response.tool_call.function_calls:
                            if fc.name in ["generate_cad", "run_web_agent", "write_file", "read_directory", "read_file", "create_project", "switch_project", "list_projects", "list_smart_devices", "control_light", "discover_printers", "print_stl", "get_print_status", "iterate_cad", "analyze_stock", "nmap_scan", "generate_hacking_payload", "test_website_vulnerability", "locate_file", "list_calendar_events", "create_calendar_event", "desktop_click", "desktop_type", "desktop_scroll", "desktop_press_key", "launch_app", "close_app", "query_visual_history", "start_recording_macro", "stop_recording_macro", "replay_macro", "generate_dashboard"]:
                                prompt = fc.args.get("prompt", "") # Prompt is not present for all tools
                                
                                # Check Permissions (Default to True if not set)
                                confirmation_required = self.permissions.get(fc.name, True)
                                
                                # Autonomous Control Permission Check (Master Bypass)
                                if self.permissions.get("autonomous_control", False):
                                    print(f"[REX DEBUG] [TOOL] Autonomous Mode: Auto-allowing '{fc.name}'")
                                    confirmation_required = False
                                
                                if not confirmation_required:
                                    print(f"[REX DEBUG] [TOOL] Permission check: '{fc.name}' -> AUTO-ALLOW")
                                    # Skip confirmation block and jump to execution
                                    pass
                                else:
                                    # Confirmation Logic
                                    if self.on_tool_confirmation:
                                        import uuid
                                        request_id = str(uuid.uuid4())
                                    print(f"[REX DEBUG] [STOP] Requesting confirmation for '{fc.name}' (ID: {request_id})")
                                    
                                    future = asyncio.Future()
                                    self._pending_confirmations[request_id] = future
                                    
                                    self.on_tool_confirmation({
                                        "id": request_id, 
                                        "tool": fc.name, 
                                        "args": fc.args
                                    })
                                    
                                    try:
                                        # Wait for user response
                                        confirmed = await future

                                    finally:
                                        self._pending_confirmations.pop(request_id, None)

                                    print(f"[REX DEBUG] [CONFIRM] Request {request_id} resolved. Confirmed: {confirmed}")

                                    if not confirmed:
                                        print(f"[REX DEBUG] [DENY] Tool call '{fc.name}' denied by user.")
                                        function_response = types.FunctionResponse(
                                            id=fc.id,
                                            name=fc.name,
                                            response={
                                                "result": "User denied the request to use this tool.",
                                            }
                                        )
                                        function_responses.append(function_response)
                                        continue

                                    if not confirmed:
                                        print(f"[REX DEBUG] [DENY] Tool call '{fc.name}' denied by user.")
                                        function_response = types.FunctionResponse(
                                            id=fc.id,
                                            name=fc.name,
                                            response={
                                                "result": "User denied the request to use this tool.",
                                            }
                                        )
                                        function_responses.append(function_response)
                                        continue

                                # If confirmed (or no callback configured, or auto-allowed), proceed
                                if fc.name == "generate_cad":
                                    print(f"\n[REX DEBUG] --------------------------------------------------")
                                    print(f"[REX DEBUG] [TOOL] Tool Call Detected: 'generate_cad'")
                                    print(f"[REX DEBUG] [IN] Arguments: prompt='{prompt}'")
                                    asyncio.create_task(self.handle_cad_request(prompt))
                                    # No function response needed - model already acknowledged when user asked
                                
                                elif fc.name == "analyze_stock":
                                    symbol = fc.args["symbol"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'analyze_stock' symbol='{symbol}'")
                                    asyncio.create_task(self.handle_stock_request(symbol))
                                
                                elif fc.name == "execute_workflow":
                                    prompt = fc.args["prompt"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'execute_workflow' prompt='{prompt}'")
                                    asyncio.create_task(self.handle_execute_workflow(prompt))

                                elif fc.name == "run_web_agent":
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'run_web_agent' with prompt='{prompt}'")
                                    asyncio.create_task(self.handle_web_agent_request(prompt))
                                    
                                    result_text = "Web Navigation started. Do not reply to this message."
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={
                                            "result": result_text,
                                        }
                                    )
                                    print(f"[REX DEBUG] [RESPONSE] Sending function response: {function_response}")
                                    function_responses.append(function_response)



                                elif fc.name == "write_file":
                                    path = fc.args["path"]
                                    content = fc.args["content"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'write_file' path='{path}'")
                                    asyncio.create_task(self.handle_write_file(path, content))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Writing file..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "read_directory":
                                    path = fc.args["path"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'read_directory' path='{path}'")
                                    asyncio.create_task(self.handle_read_directory(path))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Reading directory..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "read_file":
                                    path = fc.args["path"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'read_file' path='{path}'")
                                    asyncio.create_task(self.handle_read_file(path))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Reading file..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "create_project":
                                    name = fc.args["name"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'create_project' name='{name}'")
                                    success, msg = self.project_manager.create_project(name)
                                    if success:
                                        # Auto-switch and Index
                                        self.project_manager.switch_project(name)
                                        asyncio.create_task(self.semantic_search.index_project(name, self.project_manager.get_current_project_path()))
                                        msg += f" Switched to '{name}' and indexing started."
                                        if self.on_project_update:
                                            self.on_project_update(name)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": msg}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "switch_project":
                                    name = fc.args["name"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'switch_project' name='{name}'")
                                    success, msg = self.project_manager.switch_project(name)
                                    if success:
                                        if self.on_project_update:
                                            self.on_project_update(name)
                                        # Auto-index switched project
                                        asyncio.create_task(self.semantic_search.index_project(name, self.project_manager.get_current_project_path()))
                                        # Gather project context and send to AI (silently, no response expected)
                                        context = self.project_manager.get_project_context()
                                        print(f"[REX DEBUG] [PROJECT] Sending project context to AI ({len(context)} chars)")
                                        try:
                                            await self.session.send(input=f"System Notification: {msg}\n\n{context}", end_of_turn=False)
                                        except Exception as e:
                                            print(f"[REX DEBUG] [ERR] Failed to send project context: {e}")
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": msg}
                                    )
                                    function_responses.append(function_response)
                                
                                elif fc.name == "list_projects":
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'list_projects'")
                                    projects = self.project_manager.list_projects()
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": f"Available projects: {', '.join(projects)}"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "list_smart_devices":
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'list_smart_devices'")
                                    # Use cached devices directly for speed
                                    # devices_dict is {ip: SmartDevice}
                                    
                                    dev_summaries = []
                                    frontend_list = []
                                    
                                    for ip, d in self.kasa_agent.devices.items():
                                        dev_type = "unknown"
                                        if d.is_bulb: dev_type = "bulb"
                                        elif d.is_plug: dev_type = "plug"
                                        elif d.is_strip: dev_type = "strip"
                                        elif d.is_dimmer: dev_type = "dimmer"
                                        
                                        # Format for Model
                                        info = f"{d.alias} (IP: {ip}, Type: {dev_type})"
                                        if d.is_on:
                                            info += " [ON]"
                                        else:
                                            info += " [OFF]"
                                        dev_summaries.append(info)
                                        
                                        # Format for Frontend
                                        frontend_list.append({
                                            "ip": ip,
                                            "alias": d.alias,
                                            "model": d.model,
                                            "type": dev_type,
                                            "is_on": d.is_on,
                                            "brightness": d.brightness if d.is_bulb or d.is_dimmer else None,
                                            "hsv": d.hsv if d.is_bulb and d.is_color else None,
                                            "has_color": d.is_color if d.is_bulb else False,
                                            "has_brightness": d.is_dimmable if d.is_bulb or d.is_dimmer else False
                                        })
                                    
                                    result_str = "No devices found in cache."
                                    if dev_summaries:
                                        result_str = "Found Devices (Cached):\n" + "\n".join(dev_summaries)
                                    
                                    # Trigger frontend update
                                    if self.on_device_update:
                                        self.on_device_update(frontend_list)

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "control_light":
                                    target = fc.args["target"]
                                    action = fc.args["action"]
                                    brightness = fc.args.get("brightness")
                                    color = fc.args.get("color")
                                    
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'control_light' Target='{target}' Action='{action}'")
                                    
                                    result_msg = f"Action '{action}' on '{target}' failed."
                                    success = False
                                    
                                    if action == "turn_on":
                                        success = await self.kasa_agent.turn_on(target)
                                        if success:
                                            result_msg = f"Turned ON '{target}'."
                                    elif action == "turn_off":
                                        success = await self.kasa_agent.turn_off(target)
                                        if success:
                                            result_msg = f"Turned OFF '{target}'."
                                    elif action == "set":
                                        success = True
                                        result_msg = f"Updated '{target}':"
                                    
                                    # Apply extra attributes if 'set' or if we just turned it on and want to set them too
                                    if success or action == "set":
                                        if brightness is not None:
                                            sb = await self.kasa_agent.set_brightness(target, brightness)
                                            if sb:
                                                result_msg += f" Set brightness to {brightness}."
                                        if color is not None:
                                            sc = await self.kasa_agent.set_color(target, color)
                                            if sc:
                                                result_msg += f" Set color to {color}."

                                    # Notify Frontend of State Change
                                    if success:
                                        # We don't need full discovery, just refresh known state or push update
                                        # But for simplicity, let's get the standard list representation
                                        # KasaAgent updates its internal state on control, so we can rebuild the list
                                        
                                        # Quick rebuild of list from internal dict
                                        updated_list = []
                                        for ip, dev in self.kasa_agent.devices.items():
                                            # We need to ensure we have the correct dict structure expected by frontend
                                            # We duplicate logic from KasaAgent.discover_devices a bit, but that's okay for now or we can add a helper
                                            # Ideally KasaAgent has a 'get_devices_list()' method.
                                            # Use the cached objects in self.kasa_agent.devices
                                            
                                            dev_type = "unknown"
                                            if dev.is_bulb: dev_type = "bulb"
                                            elif dev.is_plug: dev_type = "plug"
                                            elif dev.is_strip: dev_type = "strip"
                                            elif dev.is_dimmer: dev_type = "dimmer"

                                            d_info = {
                                                "ip": ip,
                                                "alias": dev.alias,
                                                "model": dev.model,
                                                "type": dev_type,
                                                "is_on": dev.is_on,
                                                "brightness": dev.brightness if dev.is_bulb or dev.is_dimmer else None,
                                                "hsv": dev.hsv if dev.is_bulb and dev.is_color else None,
                                                "has_color": dev.is_color if dev.is_bulb else False,
                                                "has_brightness": dev.is_dimmable if dev.is_bulb or dev.is_dimmer else False
                                            }
                                            updated_list.append(d_info)
                                            
                                        if self.on_device_update:
                                            self.on_device_update(updated_list)
                                    else:
                                        # Report Error
                                        if self.on_error:
                                            self.on_error(result_msg)

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_msg}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "discover_printers":
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'discover_printers'")
                                    printers = await self.printer_agent.discover_printers()
                                    # Format for model
                                    if printers:
                                        printer_list = []
                                        for p in printers:
                                            printer_list.append(f"{p['name']} ({p['host']}:{p['port']}, type: {p['printer_type']})")
                                        result_str = "Found Printers:\n" + "\n".join(printer_list)
                                    else:
                                        result_str = "No printers found on network. Ensure printers are on and running OctoPrint/Moonraker."
                                    
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "print_stl":
                                    stl_path = fc.args["stl_path"]
                                    printer = fc.args["printer"]
                                    profile = fc.args.get("profile")
                                    
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'print_stl' STL='{stl_path}' Printer='{printer}'")
                                    
                                    # Resolve 'current' to project STL
                                    if stl_path.lower() == "current":
                                        stl_path = "output.stl" # Let printer agent resolve it in root_path

                                    # Get current project path
                                    project_path = str(self.project_manager.get_current_project_path())
                                    
                                    result = await self.printer_agent.print_stl(
                                        stl_path, 
                                        printer, 
                                        profile, 
                                        root_path=project_path
                                    )
                                    result_str = result.get("message", "Unknown result")
                                    
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "get_print_status":
                                    printer = fc.args["printer"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'get_print_status' Printer='{printer}'")
                                    
                                    status = await self.printer_agent.get_print_status(printer)
                                    if status:
                                        result_str = f"Printer: {status.printer}\n"
                                        result_str += f"State: {status.state}\n"
                                        result_str += f"Progress: {status.progress_percent:.1f}%\n"
                                        if status.time_remaining:
                                            result_str += f"Time Remaining: {status.time_remaining}\n"
                                        if status.time_elapsed:
                                            result_str += f"Time Elapsed: {status.time_elapsed}\n"
                                        if status.filename:
                                            result_str += f"File: {status.filename}\n"
                                        if status.temperatures:
                                            temps = status.temperatures
                                            if "hotend" in temps:
                                                result_str += f"Hotend: {temps['hotend']['current']:.0f}°C / {temps['hotend']['target']:.0f}°C\n"
                                            if "bed" in temps:
                                                result_str += f"Bed: {temps['bed']['current']:.0f}°C / {temps['bed']['target']:.0f}°C"
                                    else:
                                        result_str = f"Could not get status for printer '{printer}'. Ensure it is discovered first."
                                    
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "iterate_cad":
                                    prompt = fc.args["prompt"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'iterate_cad' Prompt='{prompt}'")
                                    
                                    # Emit status
                                    if self.on_cad_status:
                                        self.on_cad_status("generating")
                                    
                                    # Get project cad folder path
                                    cad_output_dir = str(self.project_manager.get_current_project_path() / "cad")
                                    
                                    # Call CadAgent to iterate on the design
                                    cad_data = await self.cad_agent.iterate_prototype(prompt, output_dir=cad_output_dir)
                                    
                                    if cad_data:
                                        print(f"[REX DEBUG] [OK] CadAgent iteration returned data successfully.")
                                        
                                        # Dispatch to frontend
                                        if self.on_cad_data:
                                            print(f"[REX DEBUG] [SEND] Dispatching iterated CAD data to frontend...")
                                            self.on_cad_data(cad_data)
                                            print(f"[REX DEBUG] [SENT] Dispatch complete.")
                                        
                                        # Save to Project
                                        self.project_manager.save_cad_artifact("output.stl", f"Iteration: {prompt}")
                                        
                                        result_str = f"Successfully iterated design: {prompt}. The updated 3D model is now displayed."
                                    else:
                                        print(f"[REX DEBUG] [ERR] CadAgent iteration returned None.")
                                        result_str = f"Failed to iterate design with prompt: {prompt}"
                                    
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "send_communication":
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'send_communication' - {fc.args}")
                                    if self.comm_agent:
                                        platform = fc.args.get("platform")
                                        contact = fc.args.get("contact")
                                        message = fc.args.get("message")
                                        if platform == "whatsapp":
                                            result = await self.comm_agent.send_whatsapp_message(contact, message)
                                        else:
                                            result = await self.comm_agent.send_sms(contact, message)
                                    else:
                                        result = "Communications Agent not available."
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "manage_call":
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'manage_call' - {fc.args}")
                                    if self.comm_agent:
                                        action = fc.args.get("action")
                                        result = await self.comm_agent.handle_call(action)
                                    else:
                                        result = "Communications Agent not available."
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "nmap_scan":
                                    target = fc.args["target"]
                                    options = fc.args.get("options", "-F")
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'nmap_scan' Target='{target}'")
                                    asyncio.create_task(self.handle_nmap_scan(target, options))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Initiating nmap scan..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "generate_hacking_payload":
                                    platform_arg = fc.args["platform"]
                                    lhost = fc.args["lhost"]
                                    lport = fc.args["lport"]
                                    output_file = fc.args.get("output_file", "payload.exe")
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'generate_hacking_payload' Platform='{platform_arg}'")
                                    asyncio.create_task(self.handle_generate_hacking_payload(platform_arg, lhost, lport, output_file))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Generating payload..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "get_desktop_screenshot":
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'get_desktop_screenshot'")
                                    result = await self.desktop_agent.get_screenshot()
                                    if result:
                                        # For Vision, we send the content as part of the next turn or as a response?
                                        # In Multimodal Live, we usually put it in the out_queue for the next turn.
                                        # But for a direct tool response, we can just say "Captured".
                                        # However, if the model wants to 'see' it, we should ensure the image is sent.
                                        if self.out_queue:
                                            await self.out_queue.put(result)
                                        result_str = "Screenshot captured and sent to context."
                                    else:
                                        result_str = "Failed to capture screenshot."
                                    
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "get_active_window":
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'get_active_window'")
                                    result = await self.desktop_agent.get_active_window_info()
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": str(result) if result else "None"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "desktop_click":
                                    x = fc.args.get("x")
                                    y = fc.args.get("y")
                                    button = fc.args.get("button", "left")
                                    clicks = fc.args.get("clicks", 1)
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'desktop_click' x={x}, y={y}, button={button}")
                                    success = await self.desktop_agent.click(x, y, button, clicks)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Success" if success else "Failed"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "desktop_type":
                                    text = fc.args["text"]
                                    interval = fc.args.get("interval", 0.01)
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'desktop_type' text='{text}'")
                                    success = await self.desktop_agent.type_text(text, interval)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Success" if success else "Failed"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "desktop_scroll":
                                    amount = fc.args["amount"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'desktop_scroll' amount={amount}")
                                    success = await self.desktop_agent.scroll(amount)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Success" if success else "Failed"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "desktop_press_key":
                                    key = fc.args["key"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'desktop_press_key' key='{key}'")
                                    success = await self.desktop_agent.press_key(key)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Success" if success else "Failed"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "locate_file":
                                    filename = fc.args["filename"]
                                    search_path = fc.args.get("search_path")
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'locate_file' Filename='{filename}'")
                                    asyncio.create_task(self.handle_locate_file(filename, search_path))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Searching for file..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "launch_app":
                                    app = fc.args["app_path_or_name"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'launch_app' app='{app}'")
                                    success = await self.desktop_agent.launch_app(app)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Success" if success else "Failed"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "desktop_click":
                                    x = fc.args.get("x")
                                    y = fc.args.get("y")
                                    button = fc.args.get("button", "left")
                                    clicks = int(fc.args.get("clicks", 1))
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'desktop_click' ({x}, {y})")
                                    if x is not None: x = int(x)
                                    if y is not None: y = int(y)
                                    success = await self.desktop_agent.click(x, y, button, clicks)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Clicked" if success else "Failed"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "desktop_type":
                                    text = fc.args["text"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'desktop_type' '{text}'")
                                    success = await self.desktop_agent.type_text(text)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Typed" if success else "Failed"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "desktop_press_key":
                                    key = fc.args["key"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'desktop_press_key' '{key}'")
                                    success = await self.desktop_agent.press_key(key)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Pressed" if success else "Failed"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "desktop_scroll":
                                    amount = int(fc.args["amount"])
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'desktop_scroll' amount={amount}")
                                    success = await self.desktop_agent.scroll(amount)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Scrolled" if success else "Failed"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "query_visual_history":
                                    query = fc.args["query"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'query_visual_history' '{query}'")
                                    result = await self.visual_memory.query_memory(query) if self.visual_memory else "Visual Memory not initialized."
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "start_recording_macro":
                                    name = fc.args["name"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'start_recording_macro' '{name}'")
                                    if self.macro_agent:
                                         result = await self.macro_agent.start_recording(name)
                                    else: 
                                         result = "Macro Agent not initialized."
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "stop_recording_macro":
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'stop_recording_macro'")
                                    if self.macro_agent:
                                         result = await self.macro_agent.stop_recording()
                                    else:
                                         result = "Macro Agent not initialized."
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "replay_macro":
                                    name = fc.args["name"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'replay_macro' '{name}'")
                                    if self.macro_agent:
                                         result = await self.macro_agent.replay_macro(name)
                                    else:
                                         result = "Macro Agent not initialized."
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "generate_dashboard":
                                    prompt = fc.args["prompt"]
                                    data = fc.args.get("data_context", "")
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'generate_dashboard' '{prompt}'")
                                    if self.gen_ui_agent:
                                         url = await self.gen_ui_agent.generate_dashboard(prompt, data)
                                         # Auto-open the dashboard
                                         if url.startswith("http"):
                                             await self.desktop_agent.launch_app(url)
                                             result = f"Dashboard generated and opened at {url}"
                                         else:
                                             result = url # Error message
                                    else:
                                         result = "Generative UI Agent not initialized."
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "close_app":
                                    proc = fc.args["process_name"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'close_app' proc='{proc}'")
                                    success = await self.desktop_agent.close_app(proc)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Success" if success else "Failed"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "test_website_vulnerability":
                                    url = fc.args["url"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'test_website_vulnerability' URL='{url}'")
                                    asyncio.create_task(self.handle_test_website_vulnerability(url))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Testing website vulnerability..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "list_calendar_events":
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'list_calendar_events'")
                                    events = self.calendar_agent.list_upcoming_events() if self.calendar_agent else "Calendar Agent not available."
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": events}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "create_calendar_event":
                                    summary = fc.args["summary"]
                                    start_time = fc.args["start_time"]
                                    end_time = fc.args.get("end_time")
                                    description = fc.args.get("description", "")
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'create_calendar_event' Summary='{summary}'")
                                    result = self.calendar_agent.create_event(summary, start_time, end_time, description) if self.calendar_agent else "Calendar Agent not available."
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "search_files":
                                    query = fc.args["query"]
                                    print(f"[REX DEBUG] [TOOL] Tool Call: 'search_files' query='{query}'")
                                    results = await self.semantic_search.search(self.project_manager.current_project, query)
                                    # Format results for Gemini
                                    if results:
                                        res_str = "Top semantic matches:\n"
                                        for r in results:
                                            res_str += f"- {r['name']} (Score: {r['score']:.2f})\n"
                                        # Optionally add snippets if Gemini needs them
                                    else:
                                        res_str = "No semantic matches found."
                                    
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": res_str}
                                    )
                                    function_responses.append(function_response)
                        if function_responses:
                            await self.session.send_tool_response(function_responses=function_responses)
                
                # Turn/Response Loop Finished
                self.flush_chat()

                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()
        except Exception as e:
            # Check for generic exception types that might be websockets
            if "ConnectionClosed" in str(type(e).__name__):
                print(f"[REX DEBUG] [NET] Audio connection closed by server (Normal Recalibration): {e}")
                # We raise to trigger reconnect, but we skip the traceback spam
                raise e
            else:
                print(f"Error in receive_audio: {e}")
                traceback.print_exc()
                # CRITICAL: Re-raise to crash the TaskGroup and trigger outer loop reconnect
                raise e

    async def play_audio(self):
        try:
             # We don't open a stream here anymore. The Audio Process has the stream.
            
            # Track when REX stops speaking (0.5 second timeout)
            self._rex_speech_timer = None
            
            # Track when REX started speaking (for mute buffer)
            self._rex_speech_start_time = None
            
            print("[REX DEBUG] [AUDIO] Audio Playback Loop Started (Redirecting to buffers)")
            
            while True:
                bytestream = await self.audio_in_queue.get()
                
                # Mark that REX is speaking
                if not self._is_rex_speaking:
                    self._is_rex_speaking = True
                    self._rex_speech_start_time = time.time()
                    print(f"[REX DEBUG] [AUDIO] REX started speaking at {self._rex_speech_start_time}")
                
                # Cancel any existing timer
                if self._rex_speech_timer:
                    self._rex_speech_timer.cancel()
                    self._rex_speech_timer = None
                
                if self.on_audio_data:
                    self.on_audio_data(bytestream)
                
                # Send to Process-Isolated Audio Engine
                # This Put can fail if the process died!
                try:
                    self.audio_queue.put(bytestream)
                except Exception as e:
                    print(f"[REX DEBUG] [ERR] Failed to put to audio_queue: {e}")
                    # If queue is broken, maybe restart engine?
                    # For now just log
                
                # Set a timer to mark REX as done speaking after 0.5 seconds of silence
                async def mark_rex_finished():
                    await asyncio.sleep(0.5)
                    if self._is_rex_speaking:  # Check if still true
                        self._is_rex_speaking = False
                        self._rex_speech_start_time = None
                        self._rex_speech_timer = None
                        print("[REX DEBUG] [AUDIO] REX finished speaking")
                
                self._rex_speech_timer = asyncio.create_task(mark_rex_finished())
        except Exception as e:
            print(f"[REX DEBUG] [CRITICAL] play_audio crashed: {e}")
            traceback.print_exc()
            raise e

    async def video_loop(self):
        try:
            cap = None
            while not self.stop_event.is_set():
                if self.paused:
                    await asyncio.sleep(0.1)
                    continue
            
            if self.video_mode == "camera":
                if cap is None:
                    print("[REX DEBUG] [VISION] Opening camera for first time...")
                    cap = await asyncio.to_thread(cv2.VideoCapture, 0)
            elif self.video_mode == "screen":
                if cap is not None:
                    print("[REX DEBUG] [VISION] Closing camera to switch to screen...")
                    cap.release()
                    cap = None
            
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame:
                if self.out_queue:
                    await self.out_queue.put(frame)
            
            # Wait for next frame (1 FPS is usually fine for Gemini Live)
            await asyncio.sleep(1.0)
            
        except Exception as e:
            print(f"[REX DEBUG] [CRITICAL] video_loop crashed: {e}")
            traceback.print_exc()
        
        if cap:
            cap.release()

    def _get_frame(self, cap):
        try:
            if self.video_mode == "screen":
                # Screen Capture Mode
                # Use DesktopAgent's SCT if available
                sct = self.desktop_agent.sct if hasattr(self, 'desktop_agent') else mss.mss()
                
                # Capture monitor with active window
                import pywinauto
                try:
                    active_window = pywinauto.Desktop(backend="uia").window(active_only=True)
                    if active_window.exists():
                        rect = active_window.rectangle()
                        # Find which monitor contains the rectangle center
                        cx, cy = rect.mid_point().x, rect.mid_point().y
                        selected_monitor = sct.monitors[1] # Default to primary
                        for m in sct.monitors[1:]:
                            if m['left'] <= cx <= m['left'] + m['width'] and \
                               m['top'] <= cy <= m['top'] + m['height']:
                                selected_monitor = m
                                break
                    else:
                        selected_monitor = sct.monitors[1]
                except:
                    selected_monitor = sct.monitors[1]

                sct_img = sct.grab(selected_monitor)
                
                # Convert to PIL for processing
                img = PIL.Image.fromarray(cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2RGB))
            else:
                # Camera Mode
                if cap is None: return None
                ret, frame = cap.read()
                if not ret:
                    return None
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = PIL.Image.fromarray(frame_rgb)
        except Exception as e:
            print(f"[REX DEBUG] [ERR] Frame capture failed: {e}")
            return None

        # Standard processing (resize, compress)
        img.thumbnail([1024, 1024])
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)
        image_bytes = image_io.read()
        return {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}


    async def run(self, start_message=None):
        retry_delay = 1
        is_reconnect = False
        
        while not self.stop_event.is_set():
            try:
                # Resolve Speaker Device by Name Before Connecting
                resolved_speaker_index = self._resolve_device(self.output_device_name, kind='output')
                if resolved_speaker_index is not None:
                    print(f"[REX] Resolved output_device_index to {resolved_speaker_index} (matched '{self.output_device_name}')")
                    self.output_device_index = resolved_speaker_index
                
                # Guaranteed Engine Start (or restart) with resolved index
                if self.audio_process:
                     try:
                         print("[REX] Stopping existing audio process for re-init...")
                         self.audio_process.terminate()
                     except: pass
                
                print(f"[REX] Starting Audio Engine for session with output_device_index={self.output_device_index}")
                self.audio_process, self.audio_queue = create_audio_engine(output_device_index=self.output_device_index)
                self.audio_process.start()

                print(f"[REX DEBUG] [CONNECT] Connecting to Gemini Live API...")
                
                # Init Queues BEFORE TaskGroup to prevent Race Condition
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=10)

                async with (
                    client.aio.live.connect(model=MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session = session

                    # Queues already inited above

                    tg.create_task(self.send_realtime())
                    tg.create_task(self.listen_audio())
                    # tg.create_task(self._process_video_queue()) # Removed in favor of VAD

                    if self.video_mode in ["camera", "screen"]:
                        tg.create_task(self.video_loop())

                    tg.create_task(self.receive_audio())
                    tg.create_task(self.play_audio())

                    # Handle Startup vs Reconnect Logic
                    if not is_reconnect:
                        if start_message:
                            print(f"[REX DEBUG] [INFO] Sending start message: {start_message}")
                            await self.session.send(input=start_message, end_of_turn=True)
                        else:
                            # Default Startup Greeting
                            print(f"[REX DEBUG] [INFO] Triggering automated startup greeting...")
                            greeting_prompt = "System Notification: Core systems initialized. Please provide a brief, witty welcome greeting to the user (Rushabh Makim) as R.E.X."
                            await self.session.send(input=greeting_prompt, end_of_turn=True)
                        
                        # Sync Project State & Index
                        if self.on_project_update and self.project_manager:
                            self.on_project_update(self.project_manager.current_project)
                        
                        # Initial project indexing
                        asyncio.create_task(self.semantic_search.index_project(self.project_manager.current_project, self.project_manager.get_current_project_path()))
                    
                    else:
                        print(f"[REX DEBUG] [RECONNECT] Connection restored.")
                        # Restore Context
                        print(f"[REX DEBUG] [RECONNECT] Fetching recent chat history to restore context...")
                        history = self.project_manager.get_recent_chat_history(limit=10)
                        
                        context_msg = "System Notification: Connection was lost and just re-established. Here is the recent chat history to help you resume seamlessly:\n\n"
                        for entry in history:
                            sender = entry.get('sender', 'Unknown')
                            text = entry.get('text', '')
                            context_msg += f"[{sender}]: {text}\n"
                        
                        context_msg += "\nPlease acknowledge the reconnection to the user (e.g. 'I lost connection for a moment, but I'm back...') and resume what you were doing."
                        
                        print(f"[REX DEBUG] [RECONNECT] Sending restoration context to model...")
                        await self.session.send(input=context_msg, end_of_turn=True)

                    # Reset retry delay on successful connection
                    retry_delay = 1
                    
                    # Wait until stop event, or until the session task group exits (which happens on error)
                    # Actually, the TaskGroup context manager will exit if any tasks fail/cancel.
                    # We need to keep this block alive.
                    # The original code just waited on stop_event, but that doesn't account for session death.
                    # We should rely on the TaskGroup raising an exception when subtasks fail (like receive_audio).
                    
                    # However, since receive_audio is a task in the group, if it crashes (connection closed), 
                    # the group will cancel others and exit. We catch that exit below.
                    
                    # We can await stop_event, but if the connection dies, receive_audio crashes -> group closes -> we exit `async with` -> restart loop.
                    # To ensure we don't block indefinitely if connection dies silently (unlikely with receive_audio), we just wait.
                    await self.stop_event.wait()

            except asyncio.CancelledError:
                print(f"[REX DEBUG] [STOP] Main loop cancelled.")
                break
                
            except Exception as e:
                # This catches the ExceptionGroup from TaskGroup or direct exceptions
                print(f"[REX DEBUG] [ERR] Connection Error: {e}")
                
                if self.stop_event.is_set():
                    break
                
                print(f"[REX DEBUG] [RETRY] Reconnecting in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 10) # Exponential backoff capped at 10s
                is_reconnect = True # Next loop will be a reconnect
                
            finally:
                # Cleanup before retry
                if hasattr(self, 'audio_stream') and self.audio_stream:
                    try:
                        self.audio_stream.close()
                    except: 
                        pass

def get_input_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            devices.append((i, p.get_device_info_by_host_api_device_index(0, i).get('name')))
    p.terminate()
    return devices

def get_output_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
            devices.append((i, p.get_device_info_by_host_api_device_index(0, i).get('name')))
    p.terminate()
    return devices

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        default=DEFAULT_MODE,
        help="pixels to stream from",
        choices=["camera", "screen", "none"],
    )
    args = parser.parse_args()
    main = AudioLoop(video_mode=args.mode)
    asyncio.run(main.run())