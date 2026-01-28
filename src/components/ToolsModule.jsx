import React, { useMemo } from 'react';
import { Mic, MicOff, Settings, Power, Video, VideoOff, Hand, Lightbulb, Printer, Globe, Box, Eye, EyeOff, MousePointer, ShieldAlert, MessageSquare, Laptop, Minimize2, Terminal, Monitor, Save, RefreshCw, Layers, ListTodo, Skull, Cpu, Sun } from 'lucide-react';

// Helper for Tooltips
const TooltipButton = ({ onClick, disabled, isActive, activeColor, inactiveColor, icon: Icon, title }) => (
    <div className="group relative">
        <button
            onClick={onClick}
            disabled={disabled}
            className={`p-2 rounded-full border-2 transition-all duration-300 ${disabled
                ? 'border-gray-800 text-gray-800 cursor-not-allowed'
                : isActive
                    ? `border-${activeColor}-500 bg-${activeColor}-500/10 text-${activeColor}-500 hover:bg-${activeColor}-500/20 shadow-[0_0_15px_rgba(var(--color-${activeColor}),0.3)]`
                    : `border-cyan-900 text-cyan-700 hover:border-${activeColor}-500 hover:text-${activeColor}-500`
                } `}
        >
            {Icon}
        </button>
        {/* Tooltip */}
        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 px-2 py-1 bg-black/80 border border-cyan-500/30 text-cyan-400 text-[10px] rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
            {title}
        </div>
    </div>
);

const ToolsModule = ({
    isConnected,
    isMuted,
    isVideoOn,
    isHandTrackingEnabled,
    showSettings,
    onTogglePower,
    onToggleMute,
    onToggleVideo,
    onToggleSettings,

    videoMode,
    onToggleVideoMode,

    onToggleHand,
    onToggleBrowser,
    showBrowserWindow,
    activeDragElement,

    onToggleVision,
    visionEnabled,
    onToggleTaskHUD,
    showTaskHUD,
    onToggleGlobe,
    showGlobe,
    onToggleControl,
    controlEnabled,
    currentMode,
    onModeSwitch,
    llmProvider,
    onToggleLLMWindow,
    showLLMWindow,
    onToggleLifestyle,
    showLifestyleWindow,

    activeWindow,
    onContextAction,
    position,
    onMouseDown
}) => {

    const contextActions = useMemo(() => {
        const title = (activeWindow || "").toLowerCase();

        if (title.includes('code') || title.includes('visual studio')) {
            return [
                { icon: Save, label: 'COMMIT', action: 'commit_code', color: 'green' },
                { icon: RefreshCw, label: 'LINT', action: 'fix_lint', color: 'yellow' },
                { icon: Terminal, label: 'TEST', action: 'run_tests', color: 'orange' }
            ];
        } else if (title.includes('blender') || title.includes('unity')) {
            return [
                { icon: Box, label: 'RENDER', action: 'render_scene', color: 'purple' },
                { icon: Layers, label: 'BAKE', action: 'bake_textures', color: 'orange' }
            ];
        } else if (title.includes('chrome') || title.includes('edge') || title.includes('firefox')) {
            return [
                { icon: Globe, label: 'SUMMARIZE', action: 'summarize_page', color: 'blue' },
                { icon: Save, label: 'BOOKMARK', action: 'save_bookmark', color: 'green' }
            ];
        }

        // Default System Actions
        return [
            { icon: Terminal, label: 'STATUS', action: 'sys_status', color: 'green' },
            { icon: Monitor, label: 'FOCUS', action: 'toggle_focus', color: 'cyan' } // Focus is toggle, so maybe check state? Passed via prop? For now stateless button.
        ];
    }, [activeWindow]);

    const containerStyle = position ? {
        position: 'absolute',
        left: position.x,
        top: position.y,
        transform: 'translate(-50%, -50%)',
        pointerEvents: 'auto'
    } : {
        pointerEvents: 'auto'
    };

    return (
        <div
            id="tools"
            onMouseDown={onMouseDown}
            className={`px-4 py-2 transition-all duration-200 
                        backdrop-blur-xl bg-black/40 border border-white/10 shadow-2xl rounded-full`}
            style={containerStyle}
        >
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none mix-blend-overlay rounded-full"></div>

            <div className="flex justify-center gap-4 relative z-10">

                {/* GROUP 1: SYSTEM & META */}
                <div className="flex gap-2 items-center">
                    <TooltipButton
                        onClick={onTogglePower}
                        isActive={isConnected}
                        activeColor="green"
                        icon={<Power size={18} />}
                        title={isConnected ? "System Online" : "Power On"}
                    />
                    <TooltipButton
                        onClick={onToggleSettings}
                        isActive={showSettings}
                        activeColor="yellow"
                        icon={<Settings size={18} />}
                        title="System Settings"
                    />
                    <TooltipButton
                        onClick={() => onModeSwitch && onModeSwitch('ethical_hacking')}
                        isActive={currentMode === 'Ethical_hacking'}
                        activeColor="red"
                        icon={<Skull size={18} />}
                        title="Ethical Hacking Mode"
                    />
                </div>

                <div className="w-px bg-white/5 h-8 self-center" />

                {/* GROUP 2: I/O CHANNELS */}
                <div className="flex gap-2 items-center">
                    <TooltipButton
                        onClick={onToggleMute}
                        disabled={!isConnected}
                        isActive={isMuted}
                        activeColor="red"
                        icon={isMuted ? <MicOff size={18} /> : <Mic size={18} />}
                        title={isMuted ? "Unmute Mic" : "Mute Mic"}
                    />
                    <TooltipButton
                        onClick={onToggleVideo}
                        isActive={isVideoOn}
                        activeColor="purple"
                        icon={isVideoOn ? <Video size={18} /> : <VideoOff size={18} />}
                        title={isVideoOn ? "Disable Camera" : "Enable Camera"}
                    />
                    <TooltipButton
                        onClick={onToggleVideoMode}
                        disabled={!isVideoOn}
                        isActive={videoMode === 'screen'}
                        activeColor="blue"
                        icon={videoMode === 'screen' ? <Laptop size={18} /> : <Video size={18} />}
                        title={videoMode === 'screen' ? "Lens: Desk" : "Lens: Screen"}
                    />
                </div>

                <div className="w-px bg-white/5 h-8 self-center" />

                {/* GROUP 3: NEURAL CORE (VISION & LLM) */}
                <div className="flex gap-2 items-center">
                    <TooltipButton
                        onClick={onToggleVision}
                        isActive={visionEnabled}
                        activeColor="cyan"
                        icon={visionEnabled ? <Eye size={18} /> : <EyeOff size={18} />}
                        title={visionEnabled ? "Disable AI Vision" : "Enable AI Vision"}
                    />
                    <TooltipButton
                        onClick={onToggleLLMWindow}
                        isActive={showLLMWindow || llmProvider === 'ollama'}
                        activeColor={llmProvider === 'ollama' ? 'indigo' : 'cyan'}
                        icon={<Cpu size={18} />}
                        title={llmProvider === 'ollama' ? "Local LLM (Ollama)" : "Cloud LLM (Gemini)"}
                    />
                </div>

                <div className="w-px bg-white/5 h-8 self-center" />

                {/* GROUP 4: INTERACTIVITY (HAND & CONTROL) */}
                <div className="flex gap-2 items-center">
                    <TooltipButton
                        onClick={onToggleHand}
                        isActive={isHandTrackingEnabled}
                        activeColor="orange"
                        icon={<Hand size={18} />}
                        title={isHandTrackingEnabled ? "Disable Gestures" : "Enable Gestures"}
                    />
                    <TooltipButton
                        onClick={onToggleControl}
                        disabled={!visionEnabled}
                        isActive={controlEnabled}
                        activeColor="red"
                        icon={controlEnabled ? <MousePointer size={18} /> : <ShieldAlert size={18} />}
                        title={controlEnabled ? "Disable Control" : "Enable Desktop Control"}
                    />
                </div>

                <div className="w-px bg-white/5 h-8 self-center" />

                {/* GROUP 5: MODULES & HUD */}
                <div className="flex gap-2 items-center">
                    <TooltipButton
                        onClick={onToggleTaskHUD}
                        isActive={showTaskHUD}
                        activeColor="green"
                        icon={<ListTodo size={18} />}
                        title={showTaskHUD ? "Hide Objectives" : "Show Objectives"}
                    />
                    <TooltipButton
                        onClick={onToggleBrowser}
                        isActive={showBrowserWindow}
                        activeColor="blue"
                        icon={<Globe size={18} />}
                        title={showBrowserWindow ? "Close Browser" : "Open Browser"}
                    />
                    <TooltipButton
                        onClick={onToggleLifestyle}
                        isActive={showLifestyleWindow}
                        activeColor="amber"
                        icon={<Sun size={18} />}
                        title={showLifestyleWindow ? "Close Briefing" : "Daily Briefing"}
                    />
                </div>

                {/* Divider for Context Actions */}
                {contextActions.length > 0 && <div className="w-px bg-white/10 mx-2 self-stretch" />}

                {/* GROUP 5: CONTEXT ACTIONS */}
                <div className="flex gap-2 items-center">
                    {contextActions.map((btn, i) => (
                        <TooltipButton
                            key={i}
                            onClick={() => onContextAction && onContextAction(btn.action)}
                            isActive={false}
                            activeColor={btn.color}
                            icon={<btn.icon size={18} />}
                            title={btn.label}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
};

export default ToolsModule;
