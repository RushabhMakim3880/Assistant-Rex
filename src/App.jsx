import React, { useEffect, useState, useRef } from 'react';
import io from 'socket.io-client';

import Visualizer from './components/Visualizer';
import TopAudioBar from './components/TopAudioBar';
import CadWindow from './components/CadWindow';
import TaskHUD from './components/TaskHUD';
import BrowserWindow from './components/BrowserWindow';
import ChatModule from './components/ChatModule';
import ToolsModule from './components/ToolsModule';
import { Mic, MicOff, Settings, X, Minus, Power, Video, VideoOff, Layout, Hand, Printer, Clock, Eye, EyeOff, MousePointer, ShieldAlert, Laptop } from 'lucide-react';
import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision';
// MemoryPrompt removed - memory is now actively saved to project
import ConfirmationPopup from './components/ConfirmationPopup';
import AuthLock from './components/AuthLock';
import SystemMonitor from './components/SystemMonitor'; // [NEW]
import NetworkMonitor from './components/NetworkMonitor'; // [NEW]
import NetworkGlobe from './components/NetworkGlobe';
import NetworkStatus from './components/NetworkStatus';
import NetworkTraffic from './components/NetworkTraffic';
import ThoughtStream from './components/ThoughtStream'; // [NEW]
import ContextShortcuts from './components/ContextShortcuts'; // [NEW]
import NeuralCore from './components/NeuralCore'; // [NEW]
import TerminalView from './components/TerminalView';
import KasaWindow from './components/KasaWindow';
import PrinterWindow from './components/PrinterWindow';
import StockWindow from './components/StockWindow';
import LifestyleWindow from './components/LifestyleWindow';
import SettingsWindow from './components/SettingsWindow';
import LlmWindow from './components/LlmWindow';
import SplashScreen from './components/SplashScreen';
import CommunicationGhost from './components/CommunicationGhost';
import { AnimatePresence } from 'framer-motion';



const socket = io('http://127.0.0.1:8000', {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000
});
const { ipcRenderer } = window.require('electron');

import DragDropZone from './components/DragDropZone';

// FileDropOverlay removed - replaced by components/DragDropZone.jsx

function App() {
    const [status, setStatus] = useState('Disconnected');
    const [socketConnected, setSocketConnected] = useState(socket.connected); // Track socket connection reactively
    // Auth State
    const [isAuthenticated, setIsAuthenticated] = useState(() => {
        // Optimistically assume authenticated if face auth is NOT enabled
        return localStorage.getItem('face_auth_enabled') !== 'true';
    });

    // Initialize from LocalStorage to prevent flash of UI
    const [isLockScreenVisible, setIsLockScreenVisible] = useState(() => {
        const saved = localStorage.getItem('face_auth_enabled');
        // If saved is 'true', we MUST start locked.
        // If 'false' or null (default off), we start unlocked.
        return saved === 'true';
    });

    // Local state for tracking settings, also init from local storage
    const [faceAuthEnabled, setFaceAuthEnabled] = useState(() => {
        return localStorage.getItem('face_auth_enabled') === 'true';
    });

    // Splash Screen State
    const [showSplash, setShowSplash] = useState(true);

    // Splash Logic: Show for min 3s, then wait for socket
    useEffect(() => {
        const timer = setTimeout(() => {
            // Once timer is done, if we are connected (or if we don't care about strict connection gating for aesthetic reasons)
            // Let's just do a purely aesthetic splash for now.
            setShowSplash(false);
        }, 5000); // 5s splash
        return () => clearTimeout(timer);
    }, []);


    const [isConnected, setIsConnected] = useState(true); // Power state DEFAULT ON
    const [isMuted, setIsMuted] = useState(false); // Mic state DEFAULT UNMUTED
    const [isVideoOn, setIsVideoOn] = useState(false); // Video state
    const [showGlobe, setShowGlobe] = useState(true);
    const [isDraggingFile, setIsDraggingFile] = useState(false);
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [cadData, setCadData] = useState(null);
    const [cadThoughts, setCadThoughts] = useState(''); // Streaming AI thoughts
    const [cadRetryInfo, setCadRetryInfo] = useState({ attempt: 1, maxAttempts: 3, error: null }); // Retry status
    const [browserData, setBrowserData] = useState({ image: null, logs: [] });
    // showMemoryPrompt removed - memory is now actively saved to project
    const [confirmationRequest, setConfirmationRequest] = useState(null); // { id, tool, args }
    const [kasaDevices, setKasaDevices] = useState([]);
    const [showKasaWindow, setShowKasaWindow] = useState(false);
    const [showPrinterWindow, setShowPrinterWindow] = useState(false);
    const [showCadWindow, setShowCadWindow] = useState(false);
    const [showBrowserWindow, setShowBrowserWindow] = useState(false);
    const [stockData, setStockData] = useState(null);
    const [showStockWindow, setShowStockWindow] = useState(false);
    const [showLifestyleWindow, setShowLifestyleWindow] = useState(false);
    const [tasks, setTasks] = useState([]);
    const [showTaskHUD, setShowTaskHUD] = useState(true);
    const [llmProvider, setLlmProvider] = useState('gemini');
    const [showLLMWindow, setShowLLMWindow] = useState(false);

    // Printing workflow status (for top toolbar display)
    const [slicingStatus, setSlicingStatus] = useState({ active: false, percent: 0, message: '' });
    const [activePrintStatus, setActivePrintStatus] = useState(null); // {printer, progress_percent, time_elapsed, state}
    const [printerCount, setPrinterCount] = useState(0); // Count of connected printers
    const [currentTime, setCurrentTime] = useState(new Date()); // Live clock
    const [showCameraWindow, setShowCameraWindow] = useState(false); // [NEW] Popup visibility


    // RESTORED STATE
    const [aiAudioData, setAiAudioData] = useState(new Array(64).fill(0));
    const [micAudioData, setMicAudioData] = useState(new Array(32).fill(0));
    const [fps, setFps] = useState(0);

    // Device states - microphones, speakers, webcams
    const [micDevices, setMicDevices] = useState([]);
    const [speakerDevices, setSpeakerDevices] = useState([]);
    const [webcamDevices, setWebcamDevices] = useState([]);

    // Selected device IDs - restored from localStorage
    const [selectedMicId, setSelectedMicId] = useState(() => localStorage.getItem('selectedMicId') || '');
    const [selectedSpeakerId, setSelectedSpeakerId] = useState(() => localStorage.getItem('selectedSpeakerId') || '');
    const [selectedWebcamId, setSelectedWebcamId] = useState(() => localStorage.getItem('selectedWebcamId') || '');
    const [showSettings, setShowSettings] = useState(false);
    const [currentProject, setCurrentProject] = useState('default');

    // Modular Mode State
    const [isModularMode, setIsModularMode] = useState(false);
    const [elementPositions, setElementPositions] = useState({
        video: { x: 40, y: 80 }, // Initial positions (approximate)
        visualizer: { x: window.innerWidth / 2, y: window.innerHeight / 2 - 150 },
        chat: { x: window.innerWidth / 2, y: window.innerHeight / 2 + 100 },
        cad: { x: window.innerWidth / 2 + 300, y: window.innerHeight / 2 },
        browser: { x: window.innerWidth / 2 - 300, y: window.innerHeight / 2 },
        kasa: { x: window.innerWidth / 2 + 350, y: window.innerHeight / 2 - 100 },
        printer: { x: window.innerWidth / 2 - 350, y: window.innerHeight / 2 - 100 },
        camera: { x: 200, y: 150 }, // [NEW] Default position
        stock: { x: window.innerWidth / 2, y: window.innerHeight / 2 },
        tools: { x: window.innerWidth / 2, y: window.innerHeight - 100 }, // Fixed bottom OFFSET
        tasks: { x: window.innerWidth - 200, y: 300 },
        llm: { x: window.innerWidth / 2, y: window.innerHeight / 2 }
    });

    const [elementSizes, setElementSizes] = useState({
        visualizer: { w: 550, h: 350 },
        chat: { w: 550, h: 220 },
        tools: { w: 500, h: 80 }, // Approx
        cad: { w: 400, h: 400 },
        browser: { w: 550, h: 380 },
        video: { w: 320, h: 180 },
        camera: { w: 340, h: 220 }, // [NEW] Popup size
        kasa: { w: 300, h: 380 }, // Approx
        printer: { w: 380, h: 380 }, // Approx
        stock: { w: 1100, h: 700 }, // Ultra-wide for premium analysis
        tasks: { w: 320, h: 450 },
        llm: { w: 320, h: 400 }
    });
    const [activeDragElement, setActiveDragElement] = useState(null);

    // Z-Index Stacking Order (last element = highest z-index)
    const [zIndexOrder, setZIndexOrder] = useState([
        'visualizer', 'chat', 'tools', 'video', 'cad', 'browser', 'kasa', 'printer', 'camera', 'stock', 'tasks', 'llm'
    ]);

    // Vision Mode (Camera vs Screen)
    const [videoMode, setVideoMode] = useState('camera'); // 'camera' or 'screen'

    // --- PHASE 6: Automation & Audio States ---
    const [wakeWordEnabled, setWakeWordEnabled] = useState(() => localStorage.getItem('wake_word_enabled') === 'true');
    const [wakeWordSensitivity, setWakeWordSensitivity] = useState(() => parseFloat(localStorage.getItem('wake_word_sensitivity')) || 0.5);
    const [maintenanceAlerts, setMaintenanceAlerts] = useState([]);
    const [currentMode, setCurrentMode] = useState('Default');
    const [trafficHistory, setTrafficHistory] = useState([]); // Network Traffic History
    const [activeConnections, setActiveConnections] = useState([]); // [NEW] Active GeoIP Connections
    const [activeWindow, setActiveWindow] = useState(''); // [NEW] Active Window Title
    const [focusMode, setFocusMode] = useState(false); // [NEW] Focus Mode
    const [commNotification, setCommNotification] = useState(null);
    const [shadowTasks, setShadowTasks] = useState([]); // [NEW] Track background shadow tasks

    // Panel Visibility State (Persisted)
    const [showLeftPanel, setShowLeftPanel] = useState(() => localStorage.getItem('showLeftPanel') !== 'false');
    const [showRightPanel, setShowRightPanel] = useState(() => localStorage.getItem('showRightPanel') !== 'false');

    useEffect(() => {
        localStorage.setItem('showLeftPanel', showLeftPanel);
    }, [showLeftPanel]);

    useEffect(() => {
        localStorage.setItem('showRightPanel', showRightPanel);
    }, [showRightPanel]);

    // Hand Control State
    const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 });
    const [isPinching, setIsPinching] = useState(false);
    const [isHandTrackingEnabled, setIsHandTrackingEnabled] = useState(false); // DEFAULT OFF
    const [cursorSensitivity, setCursorSensitivity] = useState(2.0);
    const [isCameraFlipped, setIsCameraFlipped] = useState(false); // Gesture control camera flip

    // Refs for Loop Access (Avoiding Closure Staleness)
    const isHandTrackingEnabledRef = useRef(false); // DEFAULT OFF
    const cursorSensitivityRef = useRef(2.0);
    const isCameraFlippedRef = useRef(false);
    const handLandmarkerRef = useRef(null);
    const cursorTrailRef = useRef([]); // Stores last N positions for trail
    const [ripples, setRipples] = useState([]); // Visual ripples on click

    // Web Audio Context for Mic Visualization
    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const sourceRef = useRef(null);
    const animationFrameRef = useRef(null);

    // Video Refs
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const transmissionCanvasRef = useRef(null); // Dedicated canvas for resizing payload
    const videoIntervalRef = useRef(null);
    const lastFrameTimeRef = useRef(0);
    const frameCountRef = useRef(0);
    const lastVideoTimeRef = useRef(-1);

    // Ref to track video state for the loop (avoids closure staleness)
    const isVideoOnRef = useRef(false);
    const isModularModeRef = useRef(false);
    const elementPositionsRef = useRef(elementPositions);
    const activeDragElementRef = useRef(null);
    const lastActiveDragElementRef = useRef(null);
    const lastCursorPosRef = useRef({ x: 0, y: 0 });
    const lastWristPosRef = useRef({ x: 0, y: 0 }); // For stable fist gesture tracking

    // Smoothing and Snapping Refs
    const smoothedCursorPosRef = useRef({ x: 0, y: 0 });
    const snapStateRef = useRef({ isSnapped: false, element: null, snapPos: { x: 0, y: 0 } });

    // Mouse Drag Refs
    const dragOffsetRef = useRef({ x: 0, y: 0 });
    const isDraggingRef = useRef(false);

    // Update refs when state changes
    useEffect(() => {
        isModularModeRef.current = isModularMode;
        elementPositionsRef.current = elementPositions;
        isHandTrackingEnabledRef.current = isHandTrackingEnabled;
        cursorSensitivityRef.current = cursorSensitivity;
        isCameraFlippedRef.current = isCameraFlipped;
        console.log("[Ref Sync] Camera flipped ref updated to:", isCameraFlipped);
    }, [isModularMode, elementPositions, isHandTrackingEnabled, cursorSensitivity, isCameraFlipped]);

    // Live Clock Update
    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentTime(new Date());
        }, 1000);
        return () => clearInterval(timer);
    }, []);

    // --- PHASE 1: Vision & Control Toggles ---
    const [visionEnabled, setVisionEnabled] = useState(true);
    const [controlEnabled, setControlEnabled] = useState(false);

    // Initial Settings Fetch
    useEffect(() => {
        socket.emit('get_settings');

        const handleSettings = (settings) => {
            console.log("Received Settings:", settings);
            if (settings.tool_permissions) {
                setVisionEnabled(settings.tool_permissions.desktop_qa !== false); // Default True
                setControlEnabled(settings.tool_permissions.autonomous_control === true); // Default False checking explicitly
            }
        };

        socket.on('settings', handleSettings);

        // Window Control Events for Screenshotting
        socket.on('minimize_window', () => {
            console.log("Minimizing window for screenshot...");
            if (window.electron && window.electron.minimize) {
                window.electron.minimize();
            }
        });

        socket.on('restore_window', () => {
            console.log("Restoring window...");
            if (window.electron && window.electron.restore) {
                window.electron.restore();
            }
        });

        return () => {
            socket.off('settings', handleSettings);
            socket.off('minimize_window');
            socket.off('restore_window');
        };
    }, []);

    // Network Stats Listener
    useEffect(() => {
        const handleStats = (data) => {
            if (data.active_window !== undefined) setActiveWindow(data.active_window);
            if (data.network) {
                if (data.network.connections) {
                    setActiveConnections(data.network.connections);
                }
                setTrafficHistory(prev => {
                    const next = [...prev, { upload: data.network.up_rate, download: data.network.down_rate }];
                    // Keep last 30 points
                    if (next.length > 30) return next.slice(next.length - 30);
                    return next;
                });
            }
        };

        socket.on('system_stats', handleStats);
        return () => socket.off('system_stats', handleStats);
    }, []);

    const toggleVision = () => {
        const newState = !visionEnabled;
        setVisionEnabled(newState);

        // Hierarchy: If Vision OFF, Control must be OFF
        let textUpdate = {};
        if (!newState && controlEnabled) {
            setControlEnabled(false);
            textUpdate = { desktop_qa: false, autonomous_control: false };
        } else {
            textUpdate = { desktop_qa: newState };
        }

        socket.emit('update_permissions', textUpdate);
    };

    const toggleControl = () => {
        // Hierarchy: Can only enable Control if Vision is ON
        if (!visionEnabled && !controlEnabled) {
            // Maybe shake animation or alert?
            console.warn("Cannot enable control without vision.");
            return;
        }

        const newState = !controlEnabled;
        setControlEnabled(newState);
        socket.emit('update_permissions', { autonomous_control: newState });
    };

    // Centering Logic (Startup & Resize)
    useEffect(() => {
        const centerElements = () => {
            const width = window.innerWidth;
            const height = window.innerHeight;

            // Calculate available vertical space
            // Tools is fixed at bottom ~100px space
            const toolsY = height - 100;
            // ToolsModule uses translate(-50%, -50%). So its Center Y.
            // Let's reserve bottom 140px for tools to be safe and float it nicely.
            const toolsCenterY = height - 100;

            const gap = 20;

            // Chat: Anchor is Top-Center (translate(-50%, 0)).
            // We want Chat Bottom to be above Tools Top.
            // Tools Top = toolsCenterY - (ToolsHeight/2) approx 40 = height - 140;
            const chatBottomLimit = height - 140;

            // Dynamic Height Calculation to fit screen
            // Standard Heights
            let vizH = 400;
            let chatH = 250;
            const topBarHeight = 60;

            // Total needed: TopBar + Viz + Gap + Chat + Gap + Tools (140 reserved)
            const totalNeeded = topBarHeight + vizH + gap + chatH + gap + 140;

            if (height < totalNeeded) {
                // Scale down
                const available = height - topBarHeight - 140 - (gap * 2);
                // Allocate 60% to Viz, 40% to Chat
                vizH = available * 0.6;
                chatH = available * 0.4;
            }

            // Positions
            // Visualizer (Center Anchored)
            // Top of Viz = TopBarHeight. Center = TopBarHeight + VizH/2
            const vizY = topBarHeight + (vizH / 2); // Removed buffer

            // Chat (Top Anchored)
            // Top of Chat = TopBarHeight + VizH + Gap
            const chatY = topBarHeight + vizH + gap;

            setElementSizes(prev => ({
                ...prev,
                visualizer: { w: Math.min(600, width * 0.8), h: vizH },
                chat: { w: Math.min(600, width * 0.9), h: chatH }
            }));

            setElementPositions(prev => ({
                ...prev,
                visualizer: {
                    x: width / 2,
                    y: vizY
                },
                chat: {
                    x: width / 2,
                    y: chatY
                },
                tools: {
                    x: width / 2,
                    y: toolsCenterY
                }
            }));
        };

        // Center on mount
        centerElements();

        // Center on resize
        window.addEventListener('resize', centerElements);
        return () => window.removeEventListener('resize', centerElements);
    }, []);

    // Utility: Clamp position to viewport so component stays fully visible
    const clampToViewport = (pos, size) => {
        const margin = 10;
        const topBarHeight = 60;
        const width = window.innerWidth;
        const height = window.innerHeight;

        return {
            x: Math.max(size.w / 2 + margin, Math.min(width - size.w / 2 - margin, pos.x)),
            y: Math.max(size.h / 2 + margin + topBarHeight, Math.min(height - size.h / 2 - margin, pos.y))
        };
    };

    // Utility: Get z-index for an element based on stacking order
    const getZIndex = (id) => {
        const baseZ = 30; // Above background elements
        const index = zIndexOrder.indexOf(id);
        return baseZ + (index >= 0 ? index : 0);
    };

    // Utility: Bring element to front (highest z-index)
    const bringToFront = (id) => {
        setZIndexOrder(prev => {
            const filtered = prev.filter(el => el !== id);
            return [...filtered, id]; // Move to end = highest z-index
        });
    };

    // Ref to track if model has been auto-connected (prevents duplicate connections)
    const hasAutoConnectedRef = useRef(false);

    // Auto-Connect Model on Start (Only after Auth and devices loaded)
    useEffect(() => {
        // Only auto-connect once: when socket connected, authenticated, and devices loaded
        if (isConnected && isAuthenticated && socketConnected && micDevices.length > 0 && !hasAutoConnectedRef.current) {
            hasAutoConnectedRef.current = true;

            // Trigger Kasa and Printer Discovery
            socket.emit('discover_kasa');
            socket.emit('discover_printers');

            // Connect to model with small delay for socket stability
            const timer = setTimeout(() => {
                const index = micDevices.findIndex(d => d.deviceId === selectedMicId);
                const queryDevice = micDevices.find(d => d.deviceId === selectedMicId);
                const deviceName = queryDevice ? queryDevice.label : null;
                const speakerIndex = speakerDevices.findIndex(d => d.deviceId === selectedSpeakerId);
                const speakerDevice = speakerDevices.find(d => d.deviceId === selectedSpeakerId);
                const speakerName = speakerDevice ? speakerDevice.label : null;
                console.log("Auto-connecting to model with device:", deviceName, "Index:", index, "Output:", speakerName, "Index:", speakerIndex);

                setStatus('Connecting...');
                socket.emit('start_audio', {
                    device_index: index >= 0 ? index : null,
                    device_name: deviceName,
                    output_device_index: speakerIndex >= 0 ? speakerIndex : null,
                    output_device_name: speakerName,
                    muted: isMuted
                });
            }, 500);
        }
    }, [isConnected, isAuthenticated, socketConnected, micDevices, selectedMicId]);

    // Voice Reactivity: Map Audio Amplitude to CSS Variable for Global Glow
    useEffect(() => {
        if (!aiAudioData || aiAudioData.length === 0) return;

        // Calculate average amplitude
        const sum = aiAudioData.reduce((a, b) => a + b, 0);
        const avg = sum / aiAudioData.length;

        // Normalize (Assuming uint8 0-255, but data might be smaller floats depending on backend)
        // If from analyzer, usually 0-255.
        // Sensitivity tweak: divide by 100 to get 0-2.5 range, clamped to 1.
        const intensity = Math.min(1, avg / 80);

        document.documentElement.style.setProperty('--voice-intensity', intensity.toFixed(3));
    }, [aiAudioData]);

    useEffect(() => {
        // Socket IO Setup
        socket.on('connect', () => {
            setStatus('Connected');
            setSocketConnected(true);
            socket.emit('get_settings');
        });
        socket.on('disconnect', () => {
            setStatus('Disconnected');
            setSocketConnected(false);
        });
        socket.on('status', (data) => {
            addMessage('System', data.msg);
            // Update status bar based on backend messages
            if (data.msg === 'R.E.X Started') {
                setStatus('Model Connected');
            } else if (data.msg === 'R.E.X Stopped') {
                setStatus('Connected');
            }
        });
        socket.on('system_mode_update', (data) => {
            console.log("[Mode] Applying mode update:", data.mode);
            setCurrentMode(data.mode.charAt(0).toUpperCase() + data.mode.slice(1));
        });
        socket.on('llm_provider_update', (data) => {
            console.log("[LLM] Provider switched to:", data.provider);
            setLlmProvider(data.provider);
        });
        socket.on('audio_data', (data) => {
            setAiAudioData(data.data);
        });
        socket.on('tasks_update', (data) => {
            console.log("[Tasks] Received update:", data);
            setTasks(data);
        });
        socket.on('shadow_tasks_update', (data) => {
            console.log("[Shadow] Received update:", data);
            setShadowTasks(data);
        });
        socket.emit('fetch_tasks');
        socket.on('auth_status', (data) => {
            console.log("Auth Status:", data);
            setIsAuthenticated(data.authenticated);
            if (data.authenticated) {
                // If authenticated, hide lock screen with animation (handled by component if visible)
                // But simpler: just hide it
                // Actually, wait for animation if it WAS visible.
                // For now, let's just assume if authenticated -> hide
                // But we want the component to invoke onAnimationComplete.
                // If we are starting up (and face auth disabled), we want it FALSE immediately.
                if (!isLockScreenVisible) {
                    // Do nothing, already hidden
                }
            } else {
                // If NOT authenticated, show lock screen
                setIsLockScreenVisible(true);
            }
        });

        socket.on('settings', (settings) => {
            console.log("[Settings] Received:", settings);
            if (settings && typeof settings.face_auth_enabled !== 'undefined') {
                setFaceAuthEnabled(settings.face_auth_enabled);
                localStorage.setItem('face_auth_enabled', settings.face_auth_enabled);
            }
            if (typeof settings.camera_flipped !== 'undefined') {
                console.log("[Settings] Camera flip set to:", settings.camera_flipped);
                setIsCameraFlipped(settings.camera_flipped);
            }
        });
        socket.on('error', (data) => {
            console.error("Socket Error:", data);
            addMessage('System', `Error: ${data.msg}`);
        });
        socket.on('cad_data', (data) => {
            console.log("Received CAD Data:", data);
            setCadData(data);
            setCadThoughts(''); // Clear thoughts when generation complete
            setShowCadWindow(true); // Open window when data arrives
            // Auto-show the window if it's hidden, clamped to viewport
            if (!elementPositions.cad) {
                const size = { w: 400, h: 400 };
                const clamped = clampToViewport({ x: window.innerWidth / 2 + 150, y: window.innerHeight / 2 }, size);
                setElementPositions(prev => ({
                    ...prev,
                    cad: clamped
                }));
            }
        });
        socket.on('cad_status', (data) => {
            console.log("Received CAD Status:", data);
            // Extract retry info from extended payload
            if (data.attempt) {
                setCadRetryInfo({
                    attempt: data.attempt,
                    maxAttempts: data.max_attempts || 3,
                    error: data.error
                });
            }
            if (data.status === 'generating' || data.status === 'retrying') {
                setCadData({ format: 'loading' });
                setShowCadWindow(true);
                if (data.status === 'generating' && data.attempt === 1) {
                    setCadThoughts(''); // Clear previous thoughts for new generation
                }
                // Auto-show the window, clamped to viewport
                if (!elementPositions.cad) {
                    const size = { w: 400, h: 400 };
                    const clamped = clampToViewport({ x: window.innerWidth / 2 + 150, y: window.innerHeight / 2 }, size);
                    setElementPositions(prev => ({
                        ...prev,
                        cad: clamped
                    }));
                }
            } else if (data.status === 'failed') {
                // Keep loading state but show error
                setCadData({ format: 'loading' });
            }
        });
        socket.on('cad_thought', (data) => {
            // Append streaming thought text
            setCadThoughts(prev => prev + data.text);
        });
        socket.on('browser_frame', (data) => {
            setBrowserData(prev => ({
                image: data.image,
                logs: [...prev.logs, data.log].filter(l => l).slice(-50) // Keep last 50 logs
            }));
            setShowBrowserWindow(true);
            // Auto-show browser window if hidden, clamped to viewport
            if (!elementPositions.browser) {
                const size = { w: 550, h: 380 };
                const clamped = clampToViewport({ x: window.innerWidth / 2 - 200, y: window.innerHeight / 2 }, size);
                setElementPositions(prev => ({
                    ...prev,
                    browser: clamped
                }));
            }
        });

        // Handle streaming transcription
        socket.on('transcription', (data) => {
            setMessages(prev => {
                const lastMsg = prev[prev.length - 1];

                // If the last message is from the same sender, append the chunk
                if (lastMsg && lastMsg.sender === data.sender) {
                    // Create a NEW object instead of mutating (prevents React StrictMode duplication)
                    return [
                        ...prev.slice(0, -1),
                        {
                            ...lastMsg,
                            text: lastMsg.text + data.text
                        }
                    ];
                } else {
                    // New message block
                    return [...prev, {
                        sender: data.sender,
                        text: data.text,
                        time: new Date().toLocaleTimeString()
                    }];
                }
            });
        });

        // Handle tool confirmation requests
        socket.on('tool_confirmation_request', (data) => {
            console.log("Received Confirmation Request:", data);
            setConfirmationRequest(data);
        });

        // Handle Print Window Request (from CadWindow)
        socket.on('request_print_window', () => {
            setShowPrinterWindow(true);
            const size = { w: 380, h: 380 };
            const clamped = clampToViewport({ x: window.innerWidth / 2, y: window.innerHeight / 2 }, size);
            setElementPositions(prev => ({
                ...prev,
                printer: clamped
            }));
        });

        // Stock Analysis Data
        socket.on('stock_data', (data) => {
            console.log("Stock Data Received:", data);
            if (data.loading) {
                // Open window in loading state
                setShowStockWindow(true);
                // We need to pass loading state to component.
                // Modify state to include loading.
                setStockData({ loading: true, symbol: data.symbol, name: data.symbol });
            } else {
                setStockData(data); // Replaces loading state with real data
                setShowStockWindow(true);
            }

            const size = { w: 700, h: 500 };
            // Center it (only if not already open to avoid jumping? Or always center?)
            // We use clampToViewport logic which defaults to center if pos is not set
            // Center it (only if not already open/positioned to avoid jumping)
            // We use functional update to check 'prev' state correctly
            setElementPositions(prev => {
                if (!prev.stock) {
                    const clamped = clampToViewport({ x: window.innerWidth / 2, y: window.innerHeight / 2 }, size);
                    return {
                        ...prev,
                        stock: clamped
                    };
                }
                return prev; // No change if already positioned
            });
        });

        // Kasa Devices
        // Kasa Devices (DISABLED BY USER REQUEST)
        /*
        socket.on('kasa_devices', (devices) => {
            console.log("Kasa Devices:", devices);
            setKasaDevices(devices);
        });

        socket.on('tasks_update', (data) => {
            console.log('[APP] Tasks Updated:', data);
            setTasks(data);
        });

        socket.emit('fetch_tasks');
        */

        /*
        socket.on('kasa_update', (data) => {
            setKasaDevices(prev => prev.map(d => {
                if (d.ip === data.ip) {
                    // Update only fields that are not null/undefined
                    return {
                        ...d,
                        is_on: data.is_on !== null ? data.is_on : d.is_on,
                        brightness: data.brightness !== null ? data.brightness : d.brightness
                    };
                }
                return d;
            }));
        });
        */

        socket.on('project_update', (data) => {
            console.log("Project Update:", data.project);
            setCurrentProject(data.project);
            addMessage('System', `Switched to project: ${data.project}`);
        });

        socket.on('maintenance_alert', (data) => {
            console.log("Maintenance Alert:", data);
            setMaintenanceAlerts(prev => [
                { id: Date.now(), ...data, time: new Date().toLocaleTimeString() },
                ...prev
            ].slice(0, 5));
            addMessage('System', `[MAINTENANCE] ${data.message}`);
        });

        socket.on('system_mode_update', (data) => {
            console.log("Mode Update:", data.mode);
            setCurrentMode(data.mode);
        });

        socket.on('comm_notification', (data) => {
            console.log("[App] Communication Notification:", data);
            setCommNotification(data);
            // Auto-dismiss messages after 10s
            if (data.type === 'message') {
                setTimeout(() => setCommNotification(null), 10000);
            }
        });

        // Track printer count for toolbar display
        // Track printer count for toolbar display (DISABLED)
        /*
        socket.on('printer_list', (list) => {
            console.log('[PRINTERS] Count:', list.length);
            setPrinterCount(list.length);
        });
        */

        // Slicing progress for top toolbar
        socket.on('slicing_progress', (data) => {
            console.log('[SLICING] Progress:', data);
            setSlicingStatus({
                active: data.percent < 100,
                percent: data.percent,
                message: data.message
            });
        });

        // Print status for top toolbar - track active prints
        // Print status for top toolbar - track active prints (DISABLED)
        /*
        socket.on('print_status_update', (data) => {
            console.log('[PRINT STATUS]', data);
            // Only show in toolbar if actively printing
            if (data.state && data.state.toLowerCase().includes('print')) {
                setActivePrintStatus({
                    active: true,
                    name: data.filename || 'Printing...',
                    progress: data.progress || 0,
                    eta: data.eta || 0
                });
            } else {
                setActivePrintStatus(prev => ({ ...prev, active: false }));
            }
        });
        */
        // The original code block for 'print_status_update' was:
        // socket.on('print_status_update', (data) => {
        //     console.log('[PRINT STATUS]', data);
        //     // Only show in toolbar if actively printing
        //     if (data.state && data.state.toLowerCase().includes('print')) {
        //         setActivePrintStatus({
        //             printer: data.printer,
        //             progress_percent: data.progress_percent,
        //             time_elapsed: data.time_elapsed,
        //             state: data.state
        //         });
        //     } else if (data.state && (data.state.toLowerCase() === 'idle' || data.state.toLowerCase() === 'standby' || data.state.toLowerCase() === 'complete')) {
        //         // Clear if print finished or idle
        //         setActivePrintStatus(null);
        //     }
        // });



        // Get All Media Devices (Microphones, Speakers, Webcams)
        navigator.mediaDevices.enumerateDevices().then(devs => {
            const audioInputs = devs.filter(d => d.kind === 'audioinput');
            const audioOutputs = devs.filter(d => d.kind === 'audiooutput');
            const videoInputs = devs.filter(d => d.kind === 'videoinput');

            setMicDevices(audioInputs);
            setSpeakerDevices(audioOutputs);
            setWebcamDevices(videoInputs);

            // Restore saved microphone or use first available
            const savedMicId = localStorage.getItem('selectedMicId');
            if (savedMicId && audioInputs.some(d => d.deviceId === savedMicId)) {
                setSelectedMicId(savedMicId);
            } else if (audioInputs.length > 0) {
                setSelectedMicId(audioInputs[0].deviceId);
            }

            // Restore saved speaker or use first available
            const savedSpeakerId = localStorage.getItem('selectedSpeakerId');
            if (savedSpeakerId && audioOutputs.some(d => d.deviceId === savedSpeakerId)) {
                setSelectedSpeakerId(savedSpeakerId);
            } else if (audioOutputs.length > 0) {
                setSelectedSpeakerId(audioOutputs[0].deviceId);
            }

            // Restore saved webcam or use first available
            const savedWebcamId = localStorage.getItem('selectedWebcamId');
            if (savedWebcamId && videoInputs.some(d => d.deviceId === savedWebcamId)) {
                setSelectedWebcamId(savedWebcamId);
            } else if (videoInputs.length > 0) {
                setSelectedWebcamId(videoInputs[0].deviceId);
            }
        });

        // Initialize Hand Landmarker
        const initHandLandmarker = async () => {
            try {
                console.log("Initializing HandLandmarker...");

                // 1. Verify Model File
                console.log("Fetching model file...");
                const response = await fetch('/hand_landmarker.task');
                if (!response.ok) {
                    throw new Error(`Failed to fetch model: ${response.status} ${response.statusText}`);
                }
                console.log("Model file found:", response.headers.get('content-type'), response.headers.get('content-length'));

                // 2. Initialize Vision
                console.log("Initializing FilesetResolver...");
                const vision = await FilesetResolver.forVisionTasks(
                    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
                );
                console.log("FilesetResolver initialized.");

                // 3. Create Landmarker
                console.log("Creating HandLandmarker (GPU)...");
                handLandmarkerRef.current = await HandLandmarker.createFromOptions(vision, {
                    baseOptions: {
                        modelAssetPath: `/hand_landmarker.task`,
                        delegate: "GPU" // Enable GPU acceleration
                    },
                    runningMode: "VIDEO",
                    numHands: 1
                });
                console.log("HandLandmarker initialized successfully!");
                addMessage('System', 'Hand Tracking Ready');

            } catch (error) {
                console.error("Failed to initialize HandLandmarker:", error);
                addMessage('System', `Hand Tracking Error: ${error.message}`);
            }
        };
        initHandLandmarker();

        return () => {
            socket.off('connect');
            socket.off('disconnect');
            socket.off('status');
            socket.off('audio_data');
            socket.off('cad_data');
            socket.off('cad_thought');
            socket.off('cad_status');
            socket.off('browser_frame');
            socket.off('transcription');
            socket.off('tool_confirmation_request');
            socket.off('kasa_devices');
            socket.off('printer_list');
            socket.off('slicing_progress');
            socket.off('print_status_update');
            socket.off('error');

            stopMicVisualizer();
            stopVideo();
        };
    }, []);

    // Initial check in case we are already connected (fix race condition)
    useEffect(() => {
        if (socket.connected) {
            setStatus('Connected');
            socket.emit('get_settings');
        }
    }, []);

    // Persist device selections to localStorage when they change
    useEffect(() => {
        if (selectedMicId) {
            localStorage.setItem('selectedMicId', selectedMicId);
            console.log('[Settings] Saved microphone:', selectedMicId);
        }
    }, [selectedMicId]);

    useEffect(() => {
        if (selectedSpeakerId) {
            localStorage.setItem('selectedSpeakerId', selectedSpeakerId);
            console.log('[Settings] Saved speaker:', selectedSpeakerId);
        }
    }, [selectedSpeakerId]);

    useEffect(() => {
        if (selectedWebcamId) {
            localStorage.setItem('selectedWebcamId', selectedWebcamId);
            console.log('[Settings] Saved webcam:', selectedWebcamId);
        }
    }, [selectedWebcamId]);

    // Start/Stop Mic Visualizer
    useEffect(() => {
        if (selectedMicId) {
            startMicVisualizer(selectedMicId);
        }
    }, [selectedMicId]);

    const startMicVisualizer = async (deviceId) => {
        stopMicVisualizer();
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { deviceId: { exact: deviceId } }
            });

            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
            analyserRef.current = audioContextRef.current.createAnalyser();
            analyserRef.current.fftSize = 64;

            sourceRef.current = audioContextRef.current.createMediaStreamSource(stream);
            sourceRef.current.connect(analyserRef.current);

            const updateMicData = () => {
                if (!analyserRef.current) return;
                const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
                analyserRef.current.getByteFrequencyData(dataArray);
                setMicAudioData(Array.from(dataArray));
                animationFrameRef.current = requestAnimationFrame(updateMicData);
            };

            updateMicData();
        } catch (err) {
            console.error("Error accessing microphone:", err);
        }
    };

    const stopMicVisualizer = () => {
        if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
        if (sourceRef.current) {
            sourceRef.current.disconnect();
            sourceRef.current = null;
        }
        if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close().catch(err => console.error("Error closing AudioContext:", err));
            audioContextRef.current = null;
        }
    };

    const startVideo = async () => {
        try {
            // Request 1080p resolution with selected webcam
            const constraints = {
                video: {
                    width: { ideal: 1920 },
                    height: { ideal: 1080 },
                    aspectRatio: 16 / 9
                }
            };

            // Use selected webcam if available
            if (selectedWebcamId) {
                constraints.video.deviceId = { exact: selectedWebcamId };
            }

            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                videoRef.current.play();
            }

            // Initialize the transmission canvas
            if (!transmissionCanvasRef.current) {
                transmissionCanvasRef.current = document.createElement('canvas');
                transmissionCanvasRef.current.width = 640;
                transmissionCanvasRef.current.height = 360;
                console.log("Initialized transmission canvas (640x360)");
            }

            setIsVideoOn(true);
            isVideoOnRef.current = true; // Update ref for loop
            setShowCameraWindow(true); // [NEW] Show popup on start

            console.log("Starting video loop with webcam:", selectedWebcamId || "default");
            requestAnimationFrame(predictWebcam);

        } catch (err) {
            console.error("Error accessing camera:", err);
            addMessage('System', 'Error accessing camera');
        }
    };

    const handleFileDrop = async (e) => {
        e.preventDefault();
        setIsDraggingFile(false);

        const files = Array.from(e.dataTransfer.files);
        for (const file of files) {
            const reader = new FileReader();
            reader.onload = () => {
                const base64Data = reader.result.split(',')[1];
                socket.emit('file_drop', {
                    name: file.name,
                    type: file.type,
                    data: base64Data
                });
            };
            reader.readAsDataURL(file);
        }
    };

    const handleGlobalDragOver = (e) => {
        e.preventDefault();
        if (e.dataTransfer.types.includes('Files')) {
            setIsDraggingFile(true);
        }
    };

    const handleGlobalDragLeave = (e) => {
        if (e.currentTarget === e.target || !e.relatedTarget) {
            setIsDraggingFile(false);
        }
    };

    const predictWebcam = () => {
        // Use ref for checking state to avoid closure staleness
        if (!isVideoOnRef.current) return;

        if (!videoRef.current) {
            requestAnimationFrame(predictWebcam);
            return;
        }

        // Check if video has valid dimensions to prevent MediaPipe crash
        if (videoRef.current.readyState < 2 || videoRef.current.videoWidth === 0 || videoRef.current.videoHeight === 0) {
            requestAnimationFrame(predictWebcam);
            return;
        }

        // 1. Draw Video to Local Display Canvas (Native Resolution) - OPTIONAL PREVIEW
        if (canvasRef.current) {
            const ctx = canvasRef.current.getContext('2d');
            // Ensure canvas matches video dimensions
            if (canvasRef.current.width !== videoRef.current.videoWidth || canvasRef.current.height !== videoRef.current.videoHeight) {
                canvasRef.current.width = videoRef.current.videoWidth;
                canvasRef.current.height = videoRef.current.videoHeight;
            }
            ctx.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height);
        }

        // 2. Send Frame to Backend (Throttled & Resized)
        if (isConnected) {
            // Simple throttle: every 5th frame roughly
            if (frameCountRef.current % 5 === 0) {
                const transCanvas = transmissionCanvasRef.current;
                if (transCanvas) {
                    const transCtx = transCanvas.getContext('2d');
                    transCtx.drawImage(videoRef.current, 0, 0, transCanvas.width, transCanvas.height);
                    transCanvas.toBlob((blob) => {
                        if (blob && isVideoOnRef.current) {
                            socket.emit('video_frame', { image: blob });
                        }
                    }, 'image/jpeg', 0.6);
                }
            }
        }

        // 3. Hand Tracking
        let startTimeMs = performance.now();
        if (isHandTrackingEnabledRef.current && handLandmarkerRef.current && videoRef.current.currentTime !== lastVideoTimeRef.current) {
            lastVideoTimeRef.current = videoRef.current.currentTime;
            const results = handLandmarkerRef.current.detectForVideo(videoRef.current, startTimeMs);

            if (results.landmarks && results.landmarks.length > 0) {
                const landmarks = results.landmarks[0];
                const indexTip = landmarks[8];
                const thumbTip = landmarks[4];
                const SENSITIVITY = cursorSensitivityRef.current;
                const rawX = isCameraFlippedRef.current ? (1 - indexTip.x) : indexTip.x;

                let normX = (rawX - 0.5) * SENSITIVITY + 0.5;
                normX = Math.max(0, Math.min(1, normX));
                let normY = (indexTip.y - 0.5) * SENSITIVITY + 0.5;
                normY = Math.max(0, Math.min(1, normY));

                const targetX = normX * window.innerWidth;
                const targetY = normY * window.innerHeight;

                const lerpFactor = 0.2;
                smoothedCursorPosRef.current.x = smoothedCursorPosRef.current.x + (targetX - smoothedCursorPosRef.current.x) * lerpFactor;
                smoothedCursorPosRef.current.y = smoothedCursorPosRef.current.y + (targetY - smoothedCursorPosRef.current.y) * lerpFactor;

                let finalX = smoothedCursorPosRef.current.x;
                let finalY = smoothedCursorPosRef.current.y;

                // --- Snap-to-Button Logic ---
                const SNAP_THRESHOLD = 50;
                const UNSNAP_THRESHOLD = 100;

                if (snapStateRef.current.isSnapped) {
                    const dist = Math.sqrt(
                        Math.pow(finalX - snapStateRef.current.snapPos.x, 2) +
                        Math.pow(finalY - snapStateRef.current.snapPos.y, 2)
                    );
                    if (dist > UNSNAP_THRESHOLD) {
                        if (snapStateRef.current.element) {
                            snapStateRef.current.element.classList.remove('snap-highlight');
                            snapStateRef.current.element.style.boxShadow = '';
                            snapStateRef.current.element.style.backgroundColor = '';
                            snapStateRef.current.element.style.borderColor = '';
                        }
                        snapStateRef.current = { isSnapped: false, element: null, snapPos: { x: 0, y: 0 } };
                    } else {
                        finalX = snapStateRef.current.snapPos.x;
                        finalY = snapStateRef.current.snapPos.y;
                    }
                } else {
                    const targets = Array.from(document.querySelectorAll('button, input, select, .draggable'));
                    let closest = null;
                    let minDist = Infinity;
                    for (const el of targets) {
                        const rect = el.getBoundingClientRect();
                        const centerX = rect.left + rect.width / 2;
                        const centerY = rect.top + rect.height / 2;
                        const dist = Math.sqrt(Math.pow(finalX - centerX, 2) + Math.pow(finalY - centerY, 2));
                        if (dist < minDist) {
                            minDist = dist;
                            closest = { el, centerX, centerY };
                        }
                    }
                    if (closest && minDist < SNAP_THRESHOLD) {
                        snapStateRef.current = {
                            isSnapped: true,
                            element: closest.el,
                            snapPos: { x: closest.centerX, y: closest.centerY }
                        };
                        finalX = closest.centerX;
                        finalY = closest.centerY;
                        closest.el.classList.add('snap-highlight');
                        closest.el.style.boxShadow = '0 0 20px rgba(34, 211, 238, 0.6)';
                        closest.el.style.backgroundColor = 'rgba(6, 182, 212, 0.2)';
                        closest.el.style.borderColor = 'rgba(34, 211, 238, 1)';
                    }
                }

                setCursorPos({ x: finalX, y: finalY });

                // --- Pinch Detection (Click) ---
                const distance = Math.sqrt(
                    Math.pow(indexTip.x - thumbTip.x, 2) + Math.pow(indexTip.y - thumbTip.y, 2)
                );
                const isPinchNow = distance < 0.05;
                if (isPinchNow && !isPinching) {
                    const el = document.elementFromPoint(finalX, finalY);
                    if (el) {
                        const clickable = el.closest('button, input, a, [role="button"]');
                        if (clickable && typeof clickable.click === 'function') {
                            clickable.click();
                        } else if (typeof el.click === 'function') {
                            el.click();
                        }
                    }
                }
                setIsPinching(isPinchNow);

                // --- Fist Detection (Drag) ---
                const isFingerFolded = (tipIdx, mcpIdx) => {
                    const tip = landmarks[tipIdx];
                    const mcp = landmarks[mcpIdx];
                    const wrist = landmarks[0];
                    const distTip = Math.sqrt(Math.pow(tip.x - wrist.x, 2) + Math.pow(tip.y - wrist.y, 2));
                    const distMcp = Math.sqrt(Math.pow(mcp.x - wrist.x, 2) + Math.pow(mcp.y - wrist.y, 2));
                    return distTip < distMcp;
                };
                const isFist = isFingerFolded(8, 5) && isFingerFolded(12, 9) && isFingerFolded(16, 13) && isFingerFolded(20, 17);
                const wrist = landmarks[0];
                const wristRawX = isCameraFlippedRef.current ? (1 - wrist.x) : wrist.x;
                const wristNormX = Math.max(0, Math.min(1, (wristRawX - 0.5) * SENSITIVITY + 0.5));
                const wristNormY = Math.max(0, Math.min(1, (wrist.y - 0.5) * SENSITIVITY + 0.5));
                const wristScreenX = wristNormX * window.innerWidth;
                const wristScreenY = wristNormY * window.innerHeight;

                if (isFist) {
                    if (!activeDragElementRef.current) {
                        const draggableElements = ['cad', 'browser', 'kasa', 'printer', 'camera'];
                        for (const id of draggableElements) {
                            const el = document.getElementById(id);
                            if (el) {
                                const rect = el.getBoundingClientRect();
                                if (finalX >= rect.left && finalX <= rect.right && finalY >= rect.top && finalY <= rect.bottom) {
                                    activeDragElementRef.current = id;
                                    bringToFront(id);
                                    lastWristPosRef.current = { x: wristScreenX, y: wristScreenY };
                                    break;
                                }
                            }
                        }
                    }
                    if (activeDragElementRef.current) {
                        const dx = wristScreenX - lastWristPosRef.current.x;
                        const dy = wristScreenY - lastWristPosRef.current.y;
                        if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
                            updateElementPosition(activeDragElementRef.current, dx, dy);
                        }
                        lastWristPosRef.current = { x: wristScreenX, y: wristScreenY };
                    }
                } else {
                    activeDragElementRef.current = null;
                }

                if (activeDragElementRef.current !== lastActiveDragElementRef.current) {
                    setActiveDragElement(activeDragElementRef.current);
                    lastActiveDragElementRef.current = activeDragElementRef.current;
                }
                lastCursorPosRef.current = { x: finalX, y: finalY };

                if (canvasRef.current) {
                    drawSkeleton(canvasRef.current.getContext('2d'), landmarks);
                }
            }
        }

        // 4. FPS Calculation
        const now = performance.now();
        frameCountRef.current++;
        if (now - lastFrameTimeRef.current >= 1000) {
            setFps(frameCountRef.current);
            frameCountRef.current = 0;
            lastFrameTimeRef.current = now;
        }

        if (isVideoOnRef.current) {
            requestAnimationFrame(predictWebcam);
        }
    };

    const drawSkeleton = (ctx, landmarks) => {
        ctx.strokeStyle = '#00FFFF';
        ctx.lineWidth = 2;

        // Connections
        const connections = HandLandmarker.HAND_CONNECTIONS;
        for (const connection of connections) {
            const start = landmarks[connection.start];
            const end = landmarks[connection.end];
            ctx.beginPath();
            ctx.moveTo(start.x * canvasRef.current.width, start.y * canvasRef.current.height);
            ctx.lineTo(end.x * canvasRef.current.width, end.y * canvasRef.current.height);
            ctx.stroke();
        }
    };

    const stopVideo = () => {
        if (videoRef.current && videoRef.current.srcObject) {
            videoRef.current.srcObject.getTracks().forEach(track => {
                track.stop();
                console.log("[Camera] Track stopped:", track.label);
            });
            videoRef.current.srcObject = null;
        }
        setIsVideoOn(false);
        isVideoOnRef.current = false; // Update ref
        setShowCameraWindow(false); // [NEW] Hide popup on stop
        setFps(0);

        // Clear canvas
        if (canvasRef.current) {
            const ctx = canvasRef.current.getContext('2d');
            ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
        }
    };

    const toggleVideo = () => {
        if (isVideoOn) {
            stopVideo();
        } else {
            startVideo();
        }
    };

    const addMessage = (sender, text) => {
        setMessages(prev => [...prev, { sender, text, time: new Date().toLocaleTimeString() }]);
    };

    const togglePower = () => {
        if (isConnected) {
            socket.emit('stop_audio');
            setIsConnected(false);
            setIsMuted(false); // Reset mute state
        } else {
            const index = micDevices.findIndex(d => d.deviceId === selectedMicId);
            const speakerIndex = speakerDevices.findIndex(d => d.deviceId === selectedSpeakerId);
            socket.emit('start_audio', {
                device_index: index >= 0 ? index : null,
                output_device_index: speakerIndex >= 0 ? speakerIndex : null,
                muted: false
            });
            setIsConnected(true);
            setIsMuted(false); // Start unmuted
        }
    };

    const toggleMute = () => {
        if (!isConnected) return; // Can't mute if not connected

        if (isMuted) {
            socket.emit('resume_audio');
            setIsMuted(false);
        } else {
            socket.emit('pause_audio');
            setIsMuted(true);
        }
    };

    const handleSend = (e) => {
        if (e.key === 'Enter' && inputValue.trim()) {
            socket.emit('user_input', { text: inputValue });
            addMessage('You', inputValue);
            setInputValue('');
        }
    };

    const handleMinimize = () => ipcRenderer.send('window-minimize');
    const handleMaximize = () => ipcRenderer.send('window-maximize');

    // Close Application - memory is now actively saved to project, no prompt needed
    const handleCloseRequest = () => {
        // Emit shutdown signal to backend for graceful shutdown
        // Use volatile emit with timeout fallback to ensure window closes even if server is unresponsive
        const closeWindow = () => ipcRenderer.send('window-close');

        if (socket.connected) {
            console.log('[APP] Sending shutdown signal to backend...');
            socket.emit('shutdown', {}, (ack) => {
                // This callback may not be called if server uses os._exit
                console.log('[APP] Shutdown acknowledged');
                closeWindow();
            });
            // Fallback: close after 500ms if ack doesn't come back
            setTimeout(closeWindow, 500);
        } else {
            // Socket not connected, just close
            closeWindow();
        }
    };

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const textContent = event.target.result;
                // Just send the text content directly
                if (typeof textContent === 'string' && textContent.length > 0) {
                    socket.emit('upload_memory', { memory: textContent });
                    addMessage('System', 'Uploading memory...');
                } else {
                    addMessage('System', 'Empty or invalid memory file');
                }
            } catch (err) {
                console.error("Error reading file:", err);
                addMessage('System', 'Error reading memory file');
            }
        };
        reader.readAsText(file);
    };

    // handleCancelClose removed - no longer using memory prompt

    const handleConfirmTool = () => {
        if (confirmationRequest) {
            socket.emit('confirm_tool', { id: confirmationRequest.id, confirmed: true });
            setConfirmationRequest(null);
        }
    };

    const handleDenyTool = () => {
        if (confirmationRequest) {
            socket.emit('confirm_tool', { id: confirmationRequest.id, confirmed: false });
            setConfirmationRequest(null);
        }
    };

    // Updated Bounds Checking Logic
    const updateElementPosition = (id, dx, dy) => {
        setElementPositions(prev => {
            const currentPos = prev[id];
            const size = elementSizes[id] || { w: 100, h: 100 }; // Fallback
            let newX = currentPos.x + dx;
            let newY = currentPos.y + dy;

            // Bounds Logic
            // Depends on anchor point.
            // Visualizer, Tools, Cad, Browser, Kasa: translate(-50%, -50%) -> Center Anchor
            // Chat: translate(-50%, 0) -> Top-Center Anchor
            // Video: Top-Left Anchor (default div)

            const width = window.innerWidth;
            const height = window.innerHeight;
            const margin = 0; // Strict bounds

            if (id === 'chat') {
                // Anchor: Top-Center (x is center, y is top)
                // X Bounds: size.w/2 <= x <= width - size.w/2
                newX = Math.max(size.w / 2 + margin, Math.min(width - size.w / 2 - margin, newX));
                // Y Bounds: 0 <= y <= height - size.h
                newY = Math.max(margin, Math.min(height - size.h - margin, newY));

            } else if (id === 'video') {
                // Anchor: Top-Left
                newX = Math.max(margin, Math.min(width - size.w - margin, newX));
                newY = Math.max(margin, Math.min(height - size.h - margin, newY));

            } else {
                // Anchor: Center
                newX = Math.max(size.w / 2 + margin, Math.min(width - size.w / 2 - margin, newX));
                newY = Math.max(size.h / 2 + margin, Math.min(height - size.h / 2 - margin, newY));
            }

            return {
                ...prev,
                [id]: {
                    x: newX,
                    y: newY
                }
            };
        });
    };

    // --- MOUSE DRAG HANDLERS ---
    const handleMouseDown = (e, id) => {
        console.log(`[MouseDrag] MouseDown on ${id}`, { target: e.target.tagName });

        // Fixed elements that should never be draggable (even in modular mode)
        const fixedElements = ['visualizer', 'chat', 'video', 'tools'];
        // Note: 'camera' is NOT a fixed element, it is a draggable popup
        if (fixedElements.includes(id)) {
            console.log(`[MouseDrag] ${id} is a fixed element, not draggable`);
            return;
        }

        // Bring clicked element to front (z-index)
        bringToFront(id);

        // Prevent dragging if interacting with inputs, buttons, or canvas (for 3D controls)
        const tagName = e.target.tagName.toLowerCase();
        if (tagName === 'input' || tagName === 'button' || tagName === 'textarea' || tagName === 'canvas' || e.target.closest('button')) {
            console.log("[MouseDrag] Interaction blocked by interactive element");
            return;
        }

        // Check if clicking on a drag handle section (data-drag-handle attribute)
        const isDragHandle = e.target.closest('[data-drag-handle]');
        if (!isDragHandle && !isModularModeRef.current) {
            // If not clicking a drag handle and modular mode is off, don't drag
            // This allows popup windows to have dedicated drag areas
            console.log("[MouseDrag] Not a drag handle and modular mode off");
            return;
        }

        const elPos = elementPositions[id];
        if (!elPos) return;

        // Calculate offset based on anchor point
        // Most are Center Anchored (x, y is center)
        // Chat is Top-Center Anchored (x is center, y is top)
        // Video is Top-Left Anchored (x is left, y is top)

        // We want: MousePos = ElementPos + Offset
        // So: Offset = MousePos - ElementPos
        dragOffsetRef.current = {
            x: e.clientX - elPos.x,
            y: e.clientY - elPos.y
        };

        setActiveDragElement(id);
        activeDragElementRef.current = id;
        isDraggingRef.current = true;

        window.addEventListener('mousemove', handleMouseDrag);
        window.addEventListener('mouseup', handleMouseUp);
    };

    const handleMouseDrag = (e) => {
        if (!isDraggingRef.current || !activeDragElementRef.current) return;

        const id = activeDragElementRef.current;
        const currentPos = elementPositionsRef.current[id];
        if (!currentPos) return;

        // Target Position = MousePos - Offset
        // But we want delta for updateElementPosition??
        // actually updateElementPosition takes dx, dy.
        // Let's just set the position directly or calculate delta.
        // Since updateElementPosition has bounds logic, let's use it, but we need delta from PREVIOUS position?
        // OR we can refactor updateElementPosition to take absolute.
        // Let's stick to calculating new position and manually updating state with bounds logic inside a setter.

        // Actually, updateElementPosition uses setElementPositions(prev => ...).
        // Let's duplicate bounds logic for mouse drag to be precise or reuse.
        // reusing updateElementPosition requires calculating dx/dy from *current state* which might be lagging in the closure?
        // No, functional update is fine.

        // But for smooth mouse drag, absolute position is better.
        const rawNewX = e.clientX - dragOffsetRef.current.x;
        const rawNewY = e.clientY - dragOffsetRef.current.y;

        setElementPositions(prev => {
            const size = elementSizes[id] || { w: 100, h: 100 }; // Fallback
            let newX = rawNewX;
            let newY = rawNewY;

            const width = window.innerWidth;
            const height = window.innerHeight;
            const margin = 0;

            if (id === 'chat') {
                newX = Math.max(size.w / 2 + margin, Math.min(width - size.w / 2 - margin, newX));
                newY = Math.max(margin, Math.min(height - size.h - margin, newY));
            } else if (id === 'video') {
                newX = Math.max(margin, Math.min(width - size.w - margin, newX));
                newY = Math.max(margin, Math.min(height - size.h - margin, newY));
            } else {
                newX = Math.max(size.w / 2 + margin, Math.min(width - size.w / 2 - margin, newX));
                newY = Math.max(size.h / 2 + margin, Math.min(height - size.h / 2 - margin, newY));
            }

            return {
                ...prev,
                [id]: { x: newX, y: newY }
            };
        });
    };

    const handleMouseUp = () => {
        isDraggingRef.current = false;
        setActiveDragElement(null);
        activeDragElementRef.current = null;
        window.removeEventListener('mousemove', handleMouseDrag);
        window.removeEventListener('mouseup', handleMouseUp);
    };

    // Calculate Average Audio Amplitude for Background Pulse
    const audioAmp = aiAudioData.reduce((a, b) => a + b, 0) / aiAudioData.length / 255;

    // Derive UI state for Neural Core [NEW]
    const coreState = React.useMemo(() => {
        // Thinking takes priority
        if (cadThoughts && cadThoughts !== 'SYSTEM ONLINE. AWAITING INPUT.') return 'thinking';
        // Speaking next (AI output)
        if (audioAmp > 0.01) return 'speaking';
        // Listening (User input potential)
        if (isConnected && !isMuted) return 'listening';
        // Analyzing (Tool active)
        if (showBrowserWindow || showCadWindow || (stockData && stockData.loading)) return 'analyzing';
        // Default
        return 'idle';
    }, [cadThoughts, audioAmp, isConnected, isMuted, showBrowserWindow, showCadWindow, stockData]);

    const toggleKasaWindow = () => {
        if (!showKasaWindow) {
            // Maybe trigger discover instantly?
            if (kasaDevices.length === 0) socket.emit('discover_kasa');
        }
        setShowKasaWindow(!showKasaWindow);
    };

    const togglePrinterWindow = () => {
        setShowPrinterWindow(!showPrinterWindow);
    };

    const toggleWakeWord = () => {
        const newState = !wakeWordEnabled;
        setWakeWordEnabled(newState);
        localStorage.setItem('wake_word_enabled', newState);
        socket.emit('toggle_wake_word', { enabled: newState });
    };

    const updateWakeWordSensitivity = (val) => {
        setWakeWordSensitivity(val);
        localStorage.setItem('wake_word_sensitivity', val);
        socket.emit('set_wake_word_sensitivity', { sensitivity: val });
    };

    const applySystemMode = (mode) => {
        console.log(`[Mode] Requesting mode: ${mode}`);
        socket.emit('apply_system_mode', { mode });
    };


    const [showChatWindow, setShowChatWindow] = useState(false);
    const toggleChatWindow = () => {
        setShowChatWindow(!showChatWindow);
    };

    const toggleTaskHUD = () => {
        setShowTaskHUD(!showTaskHUD);
    };

    const handleCompleteTask = (taskId) => {
        socket.emit('complete_task_manual', { id: taskId });
    };



    const handleContextAction = (action) => {
        if (action === 'toggle_focus') {
            setFocusMode(!focusMode);
        } else {
            socket.emit('context_action', { action, window: activeWindow });
        }
    };

    return (
        <div
            className={`h-screen w-screen bg-black ${currentMode === 'Ethical_hacking' ? 'hacker-theme' : ''} text-cyan-100 font-mono overflow-hidden flex flex-col relative selection:bg-cyan-900 selection:text-white`}
        >
            <DragDropZone />
            {/* Splash Screen Overlay */}
            <AnimatePresence>
                {showSplash && <SplashScreen />}
            </AnimatePresence>

            {/* Background Image - Subtle Texture */}

            {/* --- PREMIUM UI LAYER --- */}

            {/* --- PREMIUM UI LAYER --- */}

            {/* --- PREMIUM UI LAYER --- */}

            {/* Logic: Show AuthLock if we are NOT authenticated AND (Lock Screen is visible OR Auth is Enabled) 
                Actually, simpler: isLockScreenVisible is the source of truth for visibility.
                We set isLockScreenVisible = true via socket if auth is required.
             */}

            {isLockScreenVisible && (
                <AuthLock
                    socket={socket}
                    onAuthenticated={() => setIsAuthenticated(true)}
                    onAnimationComplete={() => setIsLockScreenVisible(false)}
                />
            )}

            {/* --- PREMIUM UI LAYER --- */}

            {/* Hand Cursor - Only show if tracking is enabled */}
            {isVideoOn && isHandTrackingEnabled && (
                <div
                    className={`fixed w-6 h-6 border-2 rounded-full pointer-events-none z-[100] transition-transform duration-75 ${isPinching ? 'bg-cyan-400 border-cyan-400 scale-75 shadow-[0_0_15px_rgba(34,211,238,0.8)]' : 'border-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.3)]'}`}
                    style={{
                        left: cursorPos.x,
                        top: cursorPos.y,
                        transform: 'translate(-50%, -50%)'
                    }}
                >
                    {/* Center Dot for precision */}
                    <div className="absolute top-1/2 left-1/2 w-1 h-1 bg-white rounded-full -translate-x-1/2 -translate-y-1/2" />
                </div>
            )}

            {/* Background Grid/Effects - ALIVE BACKGROUND (Fixed: Static opacity) */}
            <div
                className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-gray-900 via-black to-black z-0 pointer-events-none"
                style={{ opacity: 0.6 }}
            ></div>
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 z-0 pointer-events-none mix-blend-overlay"></div>

            {/* Ambient Glow (Fixed: Static) */}
            <div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-cyan-900/10 rounded-full blur-[120px] pointer-events-none"
            />

            {/* Top Bar */}
            <div className="absolute top-0 left-0 right-0 h-[60px] flex items-center justify-between px-4 z-30 bg-gradient-to-b from-black/80 to-transparent backdrop-blur-sm" style={{ WebkitAppRegion: 'drag' }}>
                <div className="flex items-center gap-4 pl-2">
                    <h1 className="text-xl font-bold tracking-[0.2em] text-cyan-400 drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
                        R.E.X
                    </h1>
                    <div className="text-[10px] text-cyan-700 border border-cyan-900 px-1 rounded">
                        V2.0.0
                    </div>
                    {/* FPS Counter */}
                    {isVideoOn && (
                        <div className="text-[10px] text-green-500 border border-green-900 px-1 rounded ml-2">
                            FPS: {fps}
                        </div>
                    )}
                    {/* Connected Printers Count */}
                    {/* (DISABLED) Connected Printers Count
                {printerCount > 0 && (
                    <div className="flex items-center gap-1.5 text-[10px] text-green-400 border border-green-500/30 bg-green-500/10 px-2 py-0.5 rounded ml-2">
                        <Printer size={10} className="text-green-400" />
                        <span>{printerCount} Printer{printerCount !== 1 ? 's' : ''}</span>
                    </div>
                )}
                */}
                    {/* (DISABLED) Kasa Devices
                {kasaDevices.length > 0 && (
                    <div className="flex items-center gap-1.5 text-[10px] text-yellow-400 border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 rounded ml-2">
                        <span>💡</span>
                        <span>{kasaDevices.length} Device{kasaDevices.length !== 1 ? 's' : ''}</span>
                    </div>
                )}
                */}


                </div>

                {/* Top Visualizer (User Mic) - Absolutely Centered */}
                <div className="absolute left-1/2 top-0 -translate-x-1/2 h-[60px] flex items-center pointer-events-none">
                    <TopAudioBar audioData={aiAudioData} shadowTasks={shadowTasks} />
                </div>

                <div className="flex items-center gap-2 pr-2" style={{ WebkitAppRegion: 'no-drag' }}>
                    {/* Live Clock */}
                    <div className="flex items-center gap-1.5 text-[11px] text-cyan-300/70 font-mono px-2">
                        <Clock size={12} className="text-cyan-500/50" />
                        <span>{currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <button onClick={handleMinimize} className="p-1 hover:bg-cyan-900/50 rounded text-cyan-500 transition-colors">
                        <Minus size={18} />
                    </button>
                    <button onClick={handleMaximize} className="p-1 hover:bg-cyan-900/50 rounded text-cyan-500 transition-colors">
                        <div className="w-[14px] h-[14px] border-2 border-current rounded-[2px]" />
                    </button>
                    <button onClick={handleCloseRequest} className="p-1 hover:bg-red-900/50 rounded text-red-500 transition-colors">
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 relative z-10 flex flex-col items-center justify-center">



                {/* Floating Project Label - Absolutely Centered */}
                <div className="absolute top-[65px] left-1/2 -translate-x-1/2 text-cyan-500 text-[10px] font-mono tracking-[0.3em] pointer-events-none z-50 bg-cyan-500/5 backdrop-blur-md px-3 py-1 rounded-full border border-cyan-500/20 shadow-[0_0_15px_rgba(6,182,212,0.1)]">
                    PROJECT: {currentProject?.toUpperCase()}
                </div>

                {/* 3-COLUMN DASHBOARD LAYOUT (Default Mode) */}
                {/* Responsive Grid: Left (Sys), Center (Viz), Right (Chat) */}
                {!isModularMode && (
                    <div className="absolute inset-0 flex items-stretch pt-[70px] pb-[120px] px-6 gap-3 pointer-events-none">

                        {/* LEFT COLUMN: System Monitor (25%) */}
                        {showLeftPanel && (
                            <div className="w-1/4 min-w-[350px] flex flex-col gap-3 pointer-events-auto">
                                <div className="flex-1 backdrop-blur-md bg-black/20 border border-white/5 rounded-2xl overflow-hidden shadow-2xl">
                                    <SystemMonitor
                                        socket={socket}
                                        isVideoOn={isVideoOn}
                                        alerts={maintenanceAlerts}
                                    />
                                </div>
                                <div className="h-[350px] backdrop-blur-md bg-black/20 border border-white/5 rounded-2xl overflow-hidden shadow-2xl relative">
                                    <NetworkMonitor socket={socket} />
                                </div>
                            </div>
                        )}

                        {/* CENTER: R.E.X. Visualizer (Absolutely Centered) */}
                        <div className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center justify-center transition-all duration-500 pointer-events-auto z-10 ${focusMode ? 'scale-110' : ''}`}>
                            {/* AI Thought Stream - Repositioned closer to core */}
                            <div className="mb-8 transform -translate-y-4">
                                <ThoughtStream thoughts={cadThoughts || "SYSTEM ONLINE. AWAITING INPUT."} />
                            </div>

                            {/* Pulsing R.E.X. Neural Core */}
                            <div className="relative w-[600px] h-[500px] flex items-center justify-center">
                                <NeuralCore
                                    width="100%"
                                    height="100%"
                                    intensity={audioAmp}
                                    state={coreState}
                                />
                            </div>
                        </div>

                        {/* RIGHT COLUMN: Network Operations (25%) */}
                        <div className="w-1/4 min-w-[350px] flex flex-col gap-3 pointer-events-auto">

                            {/* Network Globe & Traffic - Hidden via Settings */}
                            {showRightPanel && (
                                <>
                                    {/* Network Globe */}
                                    {showGlobe && (
                                        <div className="h-[300px] backdrop-blur-md bg-black/20 border border-white/5 rounded-2xl overflow-hidden shadow-2xl relative">
                                            <NetworkGlobe connections={activeConnections} />
                                        </div>
                                    )}

                                    {/* Network Traffic (Compact) */}
                                    <NetworkTraffic history={trafficHistory} />
                                </>
                            )}

                            {/* Chat Module (Expands) - ALWAYS VISIBLE */}
                            <div className="flex-1 backdrop-blur-md bg-black/20 border border-white/5 rounded-2xl overflow-hidden shadow-2xl relative">
                                <ChatModule
                                    messages={messages}
                                    inputValue={inputValue}
                                    setInputValue={setInputValue}
                                    handleSend={handleSend}
                                    isModularMode={false}
                                    activeDragElement={null}
                                    width="100%"
                                    height="100%"
                                    socket={socket}
                                />
                            </div>
                        </div>

                    </div>
                )}

                {/* MODULAR MODE ELEMENTS (Fallback) */}
                {/* Only render these if isModularMode is TRUE. 
                    However, maintaining state preservation between modes is tricky if we unmount.
                    For now, we will toggle visibility or existence. 
                    Actually, ChatModule and Visualizer are used in both. 
                    To avoid state loss (chat history), we should keep one instance or lift state. 
                    Chat state (messages) is lifted to App. So re-mounting ChatModule is fine. 
                    Visualizer is purely prop driven.
                */}

                {/* MODULAR MODE ELEMENTS */}
                {isModularMode && (
                    <>
                        {/* Floating Visualizer */}
                        <div
                            id="visualizer"
                            className={`absolute flex items-center justify-center transition-all duration-200 
                                backdrop-blur-xl bg-black/30 border border-white/10 shadow-2xl overflow-visible
                                ${activeDragElement === 'visualizer' ? 'ring-2 ring-green-500 bg-green-500/10' : 'ring-1 ring-yellow-500/30 bg-yellow-500/5'} rounded-2xl pointer-events-auto
                            `}
                            style={{
                                left: elementPositions.visualizer.x,
                                top: elementPositions.visualizer.y,
                                transform: 'translate(-50%, -50%)',
                                width: elementSizes.visualizer.w,
                                height: elementSizes.visualizer.h
                            }}
                            onMouseDown={(e) => handleMouseDown(e, 'visualizer')}
                        >
                            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none mix-blend-overlay z-10"></div>
                            <div className="relative z-20">
                                <Visualizer
                                    audioData={aiAudioData}
                                    isListening={isConnected && !isMuted}
                                    intensity={audioAmp}
                                    width={elementSizes.visualizer.w}
                                    height={elementSizes.visualizer.h}
                                />
                            </div>
                            <div className={`absolute top-2 right-2 text-xs font-bold tracking-widest z-20 ${activeDragElement === 'visualizer' ? 'text-green-500' : 'text-yellow-500/50'}`}>VISUALIZER</div>
                        </div>

                        {/* Floating Chat - Only render in Modular Mode (since it's docked in Dashboard now) */}
                        {(isModularMode) && (
                            <ChatModule
                                messages={messages}
                                inputValue={inputValue}
                                setInputValue={setInputValue}
                                handleSend={handleSend}
                                isModularMode={true} // Always modular behavior when floating
                                activeDragElement={activeDragElement}
                                position={elementPositions.chat}
                                width={elementSizes.chat.w}
                                height={elementSizes.chat.h}
                                onMouseDown={(e) => handleMouseDown(e, 'chat')}
                                socket={socket}
                            />
                        )}

                        {/* Floating Video Window */}
                        <div
                            id="video"
                            className={`fixed bottom-4 right-4 transition-all duration-200 
                                ${isVideoOn ? 'opacity-100' : 'opacity-0 pointer-events-none'} 
                                backdrop-blur-md bg-black/40 border border-white/10 shadow-xl rounded-xl
                            `}
                            style={{ zIndex: 20 }}
                        >
                            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none mix-blend-overlay"></div>
                            <div className="relative border border-cyan-500/30 rounded-lg overflow-hidden shadow-[0_0_20px_rgba(6,182,212,0.1)] w-80 aspect-video bg-black/80">
                                <div className="absolute top-2 left-2 text-[10px] text-cyan-400 bg-black/60 backdrop-blur px-2 py-0.5 rounded border border-cyan-500/20 z-10 font-bold tracking-wider">CAM_01</div>
                                <canvas
                                    ref={canvasRef}
                                    className="absolute inset-0 w-full h-full opacity-80"
                                    style={{ transform: isCameraFlipped ? 'scaleX(-1)' : 'none' }}
                                />
                            </div>
                        </div>
                    </>
                )}

                {/* We need to conditionally render the old "video" and absolute "visualizer/chat" 
                    BASED ON isModularMode. 
                    I will replace the existing absolute blocks with the conditional logic.
                */}


                {/* Settings Modal - Moved outside Video so it shows independently */}
                {showSettings && (
                    <SettingsWindow
                        socket={socket}
                        micDevices={micDevices}
                        speakerDevices={speakerDevices}
                        webcamDevices={webcamDevices}
                        selectedMicId={selectedMicId}
                        setSelectedMicId={setSelectedMicId}
                        selectedSpeakerId={selectedSpeakerId}
                        setSelectedSpeakerId={setSelectedSpeakerId}
                        selectedWebcamId={selectedWebcamId}
                        setSelectedWebcamId={setSelectedWebcamId}
                        cursorSensitivity={cursorSensitivity}
                        setCursorSensitivity={setCursorSensitivity}
                        isCameraFlipped={isCameraFlipped}
                        setIsCameraFlipped={setIsCameraFlipped}
                        // Panel Visibility
                        showLeftPanel={showLeftPanel}
                        setShowLeftPanel={setShowLeftPanel}
                        showRightPanel={showRightPanel}
                        setShowRightPanel={setShowRightPanel}
                        wakeWordEnabled={wakeWordEnabled}
                        onToggleWakeWord={toggleWakeWord}
                        wakeWordSensitivity={wakeWordSensitivity}
                        onUpdateWakeWordSensitivity={updateWakeWordSensitivity}
                        handleFileUpload={handleFileUpload}
                        onClose={() => setShowSettings(false)}
                    />
                )}

                {/* CAD Window Overlay - Moved outside of Video so it can show independently */}
                {showCadWindow && (
                    <div
                        id="cad"
                        className={`absolute flex flex-col transition-all duration-200 
                        backdrop-blur-xl bg-black/40 border border-white/10 shadow-2xl overflow-hidden rounded-2xl
                        ${activeDragElement === 'cad' ? 'ring-2 ring-green-500 bg-green-500/10' : ''}
                    `}
                        style={{
                            left: elementPositions.cad?.x || window.innerWidth / 2,
                            top: elementPositions.cad?.y || window.innerHeight / 2,
                            transform: 'translate(-50%, -50%)',
                            width: `${elementSizes.cad.w}px`,
                            height: `${elementSizes.cad.h}px`,
                            pointerEvents: 'auto',
                            zIndex: getZIndex('cad')
                        }}
                        onMouseDown={(e) => handleMouseDown(e, 'cad')}
                    >
                        {/* Drag Handle Header */}
                        <div
                            data-drag-handle
                            className="h-8 bg-gray-900/80 border-b border-cyan-500/20 flex items-center justify-between px-3 cursor-grab active:cursor-grabbing shrink-0"
                        >
                            <span className="text-xs font-bold tracking-widest text-cyan-500/70">CAD PROTOTYPE</span>
                            <button
                                onClick={() => setShowCadWindow(false)}
                                className="text-gray-400 hover:text-red-400 hover:bg-red-500/20 p-1 rounded transition-colors"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none mix-blend-overlay z-10"></div>
                        <div className="relative z-20 flex-1 min-h-0">
                            <CadWindow
                                data={cadData}
                                thoughts={cadThoughts}
                                retryInfo={cadRetryInfo}
                                onClose={() => setShowCadWindow(false)}
                                socket={socket}
                            />
                        </div>
                    </div>
                )}


                {/* Browser Window Overlay */}
                {showBrowserWindow && (
                    <div
                        id="browser"
                        className={`absolute flex flex-col transition-all duration-200 
                        backdrop-blur-xl bg-black/40 border border-white/10 shadow-2xl overflow-hidden rounded-lg
                        ${activeDragElement === 'browser' ? 'ring-2 ring-green-500 bg-green-500/10' : ''}
                    `}
                        style={{
                            left: elementPositions.browser?.x || window.innerWidth / 2 - 200,
                            top: elementPositions.browser?.y || window.innerHeight / 2,
                            transform: 'translate(-50%, -50%)',
                            width: `${elementSizes.browser.w}px`,
                            height: `${elementSizes.browser.h}px`,
                            pointerEvents: 'auto',
                            zIndex: getZIndex('browser')
                        }}
                        onMouseDown={(e) => handleMouseDown(e, 'browser')}
                    >
                        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 pointer-events-none mix-blend-overlay z-10"></div>
                        <div className="relative z-20 w-full h-full">
                            <BrowserWindow
                                imageSrc={browserData.image}
                                logs={browserData.logs}
                                onClose={() => setShowBrowserWindow(false)}
                                socket={socket}
                            />
                        </div>
                    </div>
                )}

                {/* Camera Feed Popup Window [NEW] */}
                {showCameraWindow && (
                    <div
                        id="camera"
                        className={`absolute flex flex-col transition-all duration-200 
                        backdrop-blur-xl bg-black/40 border border-cyan-500/30 shadow-2xl overflow-hidden rounded-xl
                        ${activeDragElement === 'camera' ? 'ring-2 ring-cyan-500 bg-cyan-500/10' : ''}
                    `}
                        style={{
                            left: elementPositions.camera?.x || 200,
                            top: elementPositions.camera?.y || 150,
                            transform: 'translate(-50%, -50%)',
                            width: `${elementSizes.camera.w}px`,
                            height: `${elementSizes.camera.h}px`,
                            pointerEvents: 'auto',
                            zIndex: getZIndex('camera')
                        }}
                        onMouseDown={(e) => handleMouseDown(e, 'camera')}
                    >
                        {/* Header */}
                        <div
                            data-drag-handle
                            className="h-8 bg-cyan-950/80 border-b border-cyan-500/20 flex items-center justify-between px-3 cursor-grab active:cursor-grabbing shrink-0"
                        >
                            <div className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></div>
                                <span className="text-[10px] font-bold tracking-widest text-cyan-400">CAM_01_FEED</span>
                            </div>
                            <button
                                onClick={() => stopVideo()}
                                className="text-cyan-700 hover:text-red-400 hover:bg-red-500/20 p-1 rounded transition-colors"
                            >
                                <X size={14} />
                            </button>
                        </div>
                        {/* Content */}
                        <div className="relative flex-1 bg-black/60 overflow-hidden group">
                            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none mix-blend-overlay z-10"></div>
                            <canvas
                                ref={canvasRef}
                                className="w-full h-full object-cover opacity-90 transition-opacity group-hover:opacity-100"
                                style={{ transform: isCameraFlipped ? 'scaleX(-1)' : 'none' }}
                            />
                            {/* Overlay Info */}
                            <div className="absolute bottom-2 left-2 flex gap-2 pointer-events-none">
                                <div className="text-[8px] text-cyan-500/50 font-mono tracking-tighter">
                                    RES: 1080P | {fps} FPS
                                </div>
                            </div>
                        </div>
                    </div>
                )}


                {/* Chat Module */}


                {/* Footer Controls / Tools Module */}
                <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 flex justify-center pointer-events-none">
                    <ToolsModule
                        isConnected={isConnected}
                        isMuted={isMuted}
                        isVideoOn={isVideoOn}
                        videoMode={videoMode}
                        onToggleVideoMode={() => {
                            const newMode = videoMode === 'camera' ? 'screen' : 'camera';
                            setVideoMode(newMode);
                            socket.emit('switch_video_mode', { mode: newMode });
                        }}
                        isHandTrackingEnabled={isHandTrackingEnabled}
                        showSettings={showSettings}
                        onTogglePower={togglePower}
                        onToggleMute={toggleMute}
                        onToggleVideo={toggleVideo}
                        onToggleSettings={() => setShowSettings(!showSettings)}
                        onToggleHand={() => setIsHandTrackingEnabled(!isHandTrackingEnabled)}
                        onToggleBrowser={() => setShowBrowserWindow(!showBrowserWindow)}
                        showBrowserWindow={showBrowserWindow}
                        onToggleVision={toggleVision}
                        visionEnabled={visionEnabled}
                        onToggleTaskHUD={toggleTaskHUD}
                        showTaskHUD={showTaskHUD}
                        onToggleGlobe={() => setShowGlobe(!showGlobe)}
                        showGlobe={showGlobe}
                        onToggleControl={toggleControl}
                        controlEnabled={controlEnabled}
                        currentMode={currentMode}
                        onModeSwitch={(explicitMode) => {
                            if (explicitMode) {
                                // If same mode, toggle back to default
                                if (currentMode.toLowerCase() === explicitMode.toLowerCase()) {
                                    applySystemMode('default');
                                } else {
                                    applySystemMode(explicitMode);
                                }
                                return;
                            }
                            const modes = ['Default', 'Work', 'Gaming'];
                            const nextIndex = (modes.indexOf(currentMode) + 1) % modes.length;
                            const nextMode = modes[nextIndex];
                            applySystemMode(nextMode.toLowerCase());
                        }}
                        activeWindow={activeWindow}
                        onContextAction={handleContextAction}
                        position={null}
                        onMouseDown={(e) => handleMouseDown(e, 'tools')}
                        llmProvider={llmProvider}
                        onToggleLLMWindow={() => setShowLLMWindow(!showLLMWindow)}
                        showLLMWindow={showLLMWindow}
                        onToggleLifestyle={() => setShowLifestyleWindow(!showLifestyleWindow)}
                        showLifestyleWindow={showLifestyleWindow}
                    />
                </div>

                <AnimatePresence>
                    {showLLMWindow && (
                        <LlmWindow
                            key="llm_window"
                            socket={socket}
                            llmProvider={llmProvider}
                            onSwitchProvider={(provider) => socket.emit('switch_llm_provider', { provider })}
                            onClose={() => setShowLLMWindow(false)}
                            position={elementPositions.llm}
                            onMouseDown={() => bringToFront('llm')}
                        />
                    )}

                    {showLifestyleWindow && (
                        <LifestyleWindow
                            onClose={() => setShowLifestyleWindow(false)}
                        />
                    )}

                </AnimatePresence>

                {/* Kasa Window */}
                {/* Kasa Window (DISABLED) */}
                {/* 
                {showKasaWindow && (
                    <KasaWindow
                        socket={socket}
                        position={elementPositions.kasa}
                        activeDragElement={activeDragElement}
                        onClose={() => setShowKasaWindow(false)}
                    />
                )}
                */}

                {/* Task HUD Overlay */}
                {showTaskHUD && (
                    <div
                        id="tasks"
                        className={`absolute flex flex-col transition-all duration-200 
                        backdrop-blur-xl bg-black/40 border border-cyan-500/20 shadow-2xl overflow-hidden rounded-2xl
                        ${activeDragElement === 'tasks' ? 'ring-2 ring-cyan-500 bg-cyan-500/10' : ''}
                    `}
                        style={{
                            left: elementPositions.tasks?.x || window.innerWidth - 200,
                            top: elementPositions.tasks?.y || 300,
                            transform: 'translate(-50%, -50%)',
                            width: `${elementSizes.tasks.w}px`,
                            height: `${elementSizes.tasks.h}px`,
                            pointerEvents: 'auto',
                            zIndex: getZIndex('tasks')
                        }}
                        onMouseDown={(e) => handleMouseDown(e, 'tasks')}
                    >
                        <div
                            data-drag-handle
                            className="h-8 bg-black/60 border-b border-cyan-500/10 flex items-center justify-between px-3 cursor-grab active:cursor-grabbing shrink-0"
                        >
                            <span className="text-[9px] font-bold tracking-[0.2em] text-cyan-600">COMMAND_CENTRAL / OBJECTIVES</span>
                            <button
                                onClick={() => setShowTaskHUD(false)}
                                className="text-cyan-900 hover:text-red-400 p-1 rounded transition-colors"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="relative z-20 flex-1 min-h-0 bg-black/20">
                            <TaskHUD
                                tasks={tasks}
                                onCompleteTask={handleCompleteTask}
                            />
                        </div>
                    </div>
                )}

                {/* Printer Window */}
                {/* Printer Window (DISABLED) */}
                {/* 
                {showPrinterWindow && (
                    <PrinterWindow
                        socket={socket}
                        onClose={() => setShowPrinterWindow(false)}
                        position={elementPositions.printer}
                        onMouseDown={(e) => handleMouseDown(e, 'printer')}
                        activeDragElement={activeDragElement}
                        setActiveDragElement={setActiveDragElement}
                        zIndex={getZIndex('printer')}
                    />
                )} 
                */}

                {/* Stock Window */}
                {showStockWindow && stockData && (
                    <div
                        id="stock"
                        className={`absolute flex flex-col transition-all duration-200 
                        backdrop-blur-xl bg-black/40 border border-white/10 shadow-2xl overflow-hidden rounded-2xl
                        ${activeDragElement === 'stock' ? 'ring-2 ring-green-500 bg-green-500/10' : ''}
                    `}
                        style={{
                            left: elementPositions.stock?.x || window.innerWidth / 2,
                            top: elementPositions.stock?.y || window.innerHeight / 2,
                            transform: 'translate(-50%, -50%)',
                            width: `${elementSizes.stock.w}px`,
                            height: `${elementSizes.stock.h}px`,
                            pointerEvents: 'auto',
                            zIndex: getZIndex('stock')
                        }}
                        onMouseDown={(e) => handleMouseDown(e, 'stock')}
                    >
                        <StockWindow
                            data={stockData}
                            onClose={() => setShowStockWindow(false)}
                        />
                    </div>
                )}

                {/* Memory Prompt removed - memory is now actively saved to project */}

                {/* Tool Confirmation Modal */}
                <ConfirmationPopup
                    request={confirmationRequest}
                    onConfirm={handleConfirmTool}
                    onDeny={handleDenyTool}
                />


                <CommunicationGhost
                    notification={commNotification}
                    onClose={() => setCommNotification(null)}
                    onAction={(action) => {
                        console.log("[App] Comm Action:", action);
                        socket.emit('comm_action', { action });
                        setCommNotification(null);
                    }}
                />

                {/* Developer Footer */}
                <div className="fixed bottom-2 left-8 text-[10px] text-cyan-600/60 pointer-events-none z-0 tracking-widest font-mono select-none">
                    DEVELOPED BY RUSHABH MAKIM | ALL RIGHTS RESERVED
                </div>

                {/* Permanent Hidden Video Element for Stable Refs */}
                <video ref={videoRef} autoPlay muted className="hidden" />
            </div>
        </div >
    );
}

export default App;
