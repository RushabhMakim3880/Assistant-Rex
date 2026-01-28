import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const TOOLS = [
    { id: 'autonomous_control', label: '⚡ MASTER CONTROL (RISKY)' },
    { id: 'run_web_agent', label: 'Web Agent' },
    { id: 'run_terminal_command', label: 'Terminal / Shell' },
    { id: 'create_directory', label: 'Create Folder' },
    { id: 'write_file', label: 'Write File' },
    { id: 'read_directory', label: 'Read Directory' },
    { id: 'read_file', label: 'Read File' },
    { id: 'create_project', label: 'Create Project' },
    { id: 'switch_project', label: 'Switch Project' },
    { id: 'list_projects', label: 'List Projects' },
];

const SettingsWindow = ({
    socket,
    micDevices,
    speakerDevices,
    webcamDevices,
    selectedMicId,
    setSelectedMicId,
    selectedSpeakerId,
    setSelectedSpeakerId,
    selectedWebcamId,
    setSelectedWebcamId,
    cursorSensitivity,
    setCursorSensitivity,
    isCameraFlipped,
    setIsCameraFlipped,
    wakeWordEnabled,
    onToggleWakeWord,
    wakeWordSensitivity,
    onUpdateWakeWordSensitivity,
    handleFileUpload,
    // Panel Visibility
    showLeftPanel,
    setShowLeftPanel,
    showRightPanel,
    setShowRightPanel,
    onClose
}) => {
    const [permissions, setPermissions] = useState({});
    const [faceAuthEnabled, setFaceAuthEnabled] = useState(false);

    useEffect(() => {
        socket.emit('get_settings');
        const handleSettings = (settings) => {
            if (settings) {
                if (settings.tool_permissions) setPermissions(settings.tool_permissions);
                if (typeof settings.face_auth_enabled !== 'undefined') {
                    setFaceAuthEnabled(settings.face_auth_enabled);
                    localStorage.setItem('face_auth_enabled', settings.face_auth_enabled);
                }
            }
        };
        socket.on('settings', handleSettings);
        return () => socket.off('settings', handleSettings);
    }, [socket]);

    const togglePermission = (toolId) => {
        const nextVal = permissions[toolId] === false;
        socket.emit('update_settings', { tool_permissions: { [toolId]: nextVal } });
    };

    const toggleFaceAuth = () => {
        const newVal = !faceAuthEnabled;
        setFaceAuthEnabled(newVal);
        localStorage.setItem('face_auth_enabled', newVal);
        socket.emit('update_settings', { face_auth_enabled: newVal });
    };

    const toggleCameraFlip = () => {
        const newVal = !isCameraFlipped;
        setIsCameraFlipped(newVal);
        socket.emit('update_settings', { camera_flipped: newVal });
    };

    return (
        <div className="absolute top-20 right-10 bg-black/90 border border-cyan-500/50 p-4 rounded-lg z-50 w-80 backdrop-blur-xl shadow-[0_0_30px_rgba(6,182,212,0.2)]">
            <div className="flex justify-between items-center mb-4 border-b border-cyan-900/50 pb-2">
                <h2 className="text-cyan-400 font-bold text-sm uppercase tracking-wider">Settings</h2>
                <button onClick={onClose} className="text-cyan-600 hover:text-cyan-400">
                    <X size={16} />
                </button>
            </div>

            {/* Interface Settings */}
            <div className="mb-4">
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Interface</h3>
                <div className="space-y-2">
                    {/* Left Panel Toggle */}
                    <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                        <span className="text-cyan-100/80">System Monitor (Left)</span>
                        <button onClick={() => setShowLeftPanel(!showLeftPanel)} className={`relative w-8 h-4 rounded-full transition-colors ${showLeftPanel ? 'bg-cyan-500' : 'bg-gray-700'}`}>
                            <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform ${showLeftPanel ? 'translate-x-4' : 'translate-x-0'}`} />
                        </button>
                    </div>
                    {/* Right Panel Toggle */}
                    <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                        <span className="text-cyan-100/80">Network Widgets (Right)</span>
                        <button onClick={() => setShowRightPanel(!showRightPanel)} className={`relative w-8 h-4 rounded-full transition-colors ${showRightPanel ? 'bg-cyan-500' : 'bg-gray-700'}`}>
                            <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform ${showRightPanel ? 'translate-x-4' : 'translate-x-0'}`} />
                        </button>
                    </div>
                </div>
            </div>

            {/* Authentication */}
            <div className="mb-4">
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Security</h3>
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                    <span className="text-cyan-100/80">Face Authentication</span>
                    <button onClick={toggleFaceAuth} className={`relative w-8 h-4 rounded-full transition-colors ${faceAuthEnabled ? 'bg-cyan-500' : 'bg-gray-700'}`}>
                        <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform ${faceAuthEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
                    </button>
                </div>
            </div>

            {/* Audio Devices */}
            <div className="mb-4 space-y-3">
                <div className="flex flex-col gap-1">
                    <label className="text-[10px] text-cyan-500/60 uppercase">Microphone</label>
                    <select value={selectedMicId} onChange={(e) => setSelectedMicId(e.target.value)} className="w-full bg-gray-900 border border-cyan-800 rounded p-1 text-xs text-cyan-100 outline-none">
                        {micDevices.map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `Mic ${i + 1}`}</option>)}
                    </select>
                </div>
                <div className="flex flex-col gap-1">
                    <label className="text-[10px] text-cyan-500/60 uppercase">Speaker</label>
                    <select value={selectedSpeakerId} onChange={(e) => setSelectedSpeakerId(e.target.value)} className="w-full bg-gray-900 border border-cyan-800 rounded p-1 text-xs text-cyan-100 outline-none">
                        {speakerDevices.map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `Speaker ${i + 1}`}</option>)}
                    </select>
                </div>
            </div>

            {/* Sensitivity */}
            <div className="mb-4">
                <div className="flex justify-between mb-1">
                    <span className="text-[10px] text-cyan-500/60 uppercase">Cursor Sensitivity</span>
                    <span className="text-[10px] text-cyan-300">{cursorSensitivity}x</span>
                </div>
                <input type="range" min="1.0" max="5.0" step="0.1" value={cursorSensitivity} onChange={(e) => setCursorSensitivity(parseFloat(e.target.value))} className="w-full accent-cyan-400 h-1 bg-gray-800 rounded-lg appearance-none" />
            </div>

            {/* Wake Word */}
            <div className="mb-4 border-t border-cyan-900/30 pt-3">
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Voice Activation</h3>
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30 mb-2">
                    <span className="text-cyan-100/80">"Hey Rex" Wake-Word</span>
                    <button onClick={onToggleWakeWord} className={`relative w-8 h-4 rounded-full transition-colors ${wakeWordEnabled ? 'bg-cyan-500' : 'bg-gray-700'}`}>
                        <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform ${wakeWordEnabled ? 'translate-x-4' : 'translate-x-0'}`} />
                    </button>
                </div>
                {wakeWordEnabled && (
                    <div className="px-1">
                        <div className="flex justify-between mb-1">
                            <span className="text-[10px] text-cyan-500/60 uppercase">Sensitivity</span>
                            <span className="text-[10px] text-cyan-300">{(wakeWordSensitivity * 100).toFixed(0)}%</span>
                        </div>
                        <input type="range" min="0.1" max="1.0" step="0.05" value={wakeWordSensitivity} onChange={(e) => onUpdateWakeWordSensitivity(parseFloat(e.target.value))} className="w-full accent-cyan-400 h-1 bg-gray-800 rounded-lg appearance-none" />
                    </div>
                )}
            </div>

            {/* Tool Permissions */}
            <div className="mb-4">
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Permissions</h3>
                <div className="space-y-1 max-h-32 overflow-y-auto pr-1 custom-scrollbar">
                    {TOOLS.map(tool => (
                        <div key={tool.id} className="flex items-center justify-between text-[10px] bg-gray-900/30 p-1.5 rounded border border-cyan-900/20">
                            <span className="text-cyan-100/60 truncate mr-2">{tool.label}</span>
                            <button onClick={() => togglePermission(tool.id)} className={`relative w-6 h-3 shrink-0 rounded-full transition-colors ${permissions[tool.id] !== false ? 'bg-cyan-600' : 'bg-gray-800'}`}>
                                <div className={`absolute top-0.5 left-0.5 w-2 h-2 bg-white rounded-full transition-transform ${permissions[tool.id] !== false ? 'translate-x-3' : 'translate-x-0'}`} />
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            {/* Memory */}
            <div className="border-t border-cyan-900/30 pt-3">
                <label className="text-[10px] text-cyan-500/60 uppercase block mb-1">Upload Memory</label>
                <input type="file" accept=".txt" onChange={handleFileUpload} className="w-full text-[10px] text-cyan-100 bg-gray-900 border border-cyan-800 rounded p-1 file:bg-cyan-900 file:text-cyan-400 file:border-0 file:rounded file:px-2 file:py-0.5 cursor-pointer" />
            </div>
        </div>
    );
};

export default SettingsWindow;
