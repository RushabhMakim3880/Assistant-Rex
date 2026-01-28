import asyncio
import importlib
import traceback
import os
from typing import Dict, Any

class ServiceManager:
    """
    Central registry for all backend agents (services).
    Handles dynamic discovery, initialization, health checks, and shutdown.
    """
    def __init__(self, backend_dir=None):
        self.services = {}
        self.status = {}
        self.backend_dir = backend_dir or os.path.dirname(os.path.abspath(__file__))
        self.health_task = None
        self.running = False

    async def register_service(self, name, service_instance):
        """Registers a service instance manually."""
        print(f"[ServiceManager] Registering service: {name}")
        self.services[name] = service_instance
        self.status[name] = "registered"

    async def discover_services(self):
        """
        Scans the backend directory for *_agent.py and adds them to the registry.
        Dynamically imports each module and finds subclasses of BaseAgent.
        """
        print(f"[ServiceManager] Scanning for services in {self.backend_dir}...")
        
        for filename in os.listdir(self.backend_dir):
            if filename.endswith("_agent.py") and filename != "base_agent.py":
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(module_name)
                    # Find classes in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        # We look for classes that look like agents (CamelCase version of module name)
                        # Or just any class that might have an 'initialize' method
                        if isinstance(attr, type) and attr.__module__ == module.__name__:
                            # Heuristic: If it has 'Agent' in name and is a class
                            if "Agent" in attr_name:
                                print(f"[ServiceManager] Found potential agent class: {attr_name}")
                                # We don't auto-instantiate here as some need specific args
                                # But we mark it as discovered
                                self.status[attr_name.lower().replace("agent", "")] = "discovered"
                except Exception as e:
                    print(f"[ServiceManager] Error loading module {module_name}: {e}")

        # Start health check loop
        self.running = True
        self.health_task = asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self):
        """Periodically checks the health of all services and attempts recovery."""
        print("[ServiceManager] Health check loop started.")
        while self.running:
            await asyncio.sleep(60) # Check every minute
            for name, service in list(self.services.items()):
                try:
                    is_healthy = True
                    # Check if service has a health check method
                    if hasattr(service, 'check_health'):
                        is_healthy = await service.check_health()
                    
                    if not is_healthy:
                        print(f"[ServiceManager] Service '{name}' is UNHEALTHY. Attempting recovery...")
                        await self.recover_service(name)
                    else:
                        # If it was in error, mark it ready again if it's now healthy
                        if "error" in self.status.get(name, ""):
                            self.status[name] = "ready"
                except Exception as e:
                    print(f"[ServiceManager] health check failed for {name}: {e}")

    async def recover_service(self, name):
        """Attempts to restart a failed service."""
        try:
            self.status[name] = "recovering"
            service = self.services.get(name)
            if service and hasattr(service, 'initialize'):
                # Pass service_manager to initialize if it needs it (like KasaAgent)
                if hasattr(service, 'service_manager'):
                    service.service_manager = self
                await service.initialize()
                self.status[name] = "ready"
                print(f"[ServiceManager] Service '{name}' recovered.")
        except Exception as e:
            print(f"[ServiceManager] Recovery failed for {name}: {e}")
            self.status[name] = f"error: {e}"

    async def initialize_all(self):
        """Initializes all registered services with proper async handling."""
        print("[ServiceManager] Initializing registered services...")
        initialization_tasks = []
        
        for name, service in self.services.items():
            if hasattr(service, 'initialize') and asyncio.iscoroutinefunction(service.initialize):
                print(f"[ServiceManager] Starting init for '{name}'...")
                initialization_tasks.append(self._init_service(name, service))
            else:
                self.status[name] = "running"
                print(f"[ServiceManager] Service '{name}' ready (no async init).")
                
        if initialization_tasks:
            await asyncio.gather(*initialization_tasks)

    async def _init_service(self, name, service):
        try:
            await service.initialize()
            self.status[name] = "running"
            print(f"[ServiceManager] Service '{name}' initialized.")
        except Exception as e:
            self.status[name] = "failed"
            print(f"[ServiceManager] CRITICAL: Failed to initialize '{name}': {e}")
            traceback.print_exc()

    async def get_service(self, name):
        """Retrieves a service by name. Blocks until initialization if needed could be added."""
        return self.services.get(name)

    async def shutdown_all(self):
        """Gracefully shuts down all services by calling their shutdown methods."""
        print("[ServiceManager] Shutting down services...")
        shutdown_tasks = []
        
        for name, service in self.services.items():
            if hasattr(service, 'shutdown') and asyncio.iscoroutinefunction(service.shutdown):
                shutdown_tasks.append(self._shutdown_service(name, service))
            else:
                self.status[name] = "stopped"
                
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks)

    async def _shutdown_service(self, name, service):
        try:
            await service.shutdown()
            self.status[name] = "stopped"
            print(f"[ServiceManager] Service '{name}' stopped.")
        except Exception as e:
            print(f"[ServiceManager] Error stopping '{name}': {e}")
