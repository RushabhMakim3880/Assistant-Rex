import React, { useMemo } from 'react';
import { Code, Box, Globe, Terminal, Save, RefreshCw, Layers, Monitor } from 'lucide-react';

const ContextShortcuts = ({ activeWindow, onAction }) => {
    const contextActions = useMemo(() => {
        const title = (activeWindow || "").toLowerCase();

        if (title.includes('code') || title.includes('visual studio')) {
            return [
                { icon: Save, label: 'COMMIT', action: 'commit_code' },
                { icon: RefreshCw, label: 'LINT', action: 'fix_lint' },
                { icon: Terminal, label: 'TEST', action: 'run_tests' }
            ];
        } else if (title.includes('blender') || title.includes('unity')) {
            return [
                { icon: Box, label: 'RENDER', action: 'render_scene' },
                { icon: Layers, label: 'BAKE', action: 'bake_textures' }
            ];
        } else if (title.includes('chrome') || title.includes('edge') || title.includes('firefox')) {
            return [
                { icon: Globe, label: 'SUMMARIZE', action: 'summarize_page' },
                { icon: Save, label: 'BOOKMARK', action: 'save_bookmark' }
            ];
        }

        // Default System Actions
        return [
            { icon: Terminal, label: 'STATUS', action: 'sys_status' },
            { icon: Monitor, label: 'FOCUS', action: 'toggle_focus' }
        ];
    }, [activeWindow]);

    return (
        <div className="flex items-center gap-2 px-4 py-2 bg-black/40 backdrop-blur-md rounded-full border border-cyan-500/20 shadow-[0_0_15px_rgba(6,182,212,0.1)] transition-all duration-500 animate-fade-in pointer-events-auto text-cyan-500">
            <div className="text-[10px] text-cyan-700 font-mono tracking-widest mr-2 uppercase border-r border-cyan-900/50 pr-2 max-w-[100px] truncate">
                CTX: {activeWindow ? activeWindow.split(' - ')[0] : 'IDLE'}
            </div>
            {contextActions.map((btn, i) => (
                <button
                    key={i}
                    className="flex items-center gap-1.5 px-3 py-1.5 hover:bg-cyan-500/10 rounded-md transition-all group active:scale-95"
                    onClick={() => onAction && onAction(btn.action)}
                >
                    <btn.icon size={14} className="text-cyan-500 group-hover:text-cyan-300 transition-colors group-hover:shadow-[0_0_10px_rgba(34,211,238,0.5)]" />
                    <span className="text-[10px] font-mono text-cyan-500 group-hover:text-cyan-200">{btn.label}</span>
                </button>
            ))}
        </div>
    );
};

export default ContextShortcuts;
