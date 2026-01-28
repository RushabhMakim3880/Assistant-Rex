import React, { useEffect, useRef } from 'react';

const ThoughtStream = ({ thoughts = "" }) => {
    const containerRef = useRef(null);

    // Auto-scroll logic if needed, but for a single stream line it's simple

    if (!thoughts) return null;

    return (
        <div className="absolute top-[160px] left-1/2 -translate-x-1/2 w-[500px] pointer-events-none z-30 flex flex-col items-center">
            <div className="relative overflow-hidden w-full text-center">
                <div className="text-cyan-500/90 font-mono text-[10px] tracking-[0.2em] uppercase voice-text drop-shadow-[0_0_5px_rgba(34,211,238,0.5)]">
                    {/* Prefix with R.E.X. marker */}
                    <span className="text-cyan-700 mr-2">R.E.X. //</span>
                    <span className="typing-effect">{thoughts}</span>
                    <span className="inline-block w-1.5 h-3 bg-cyan-400 ml-1 animate-pulse align-middle"></span>
                </div>
            </div>
            {/* Decorative line */}
            <div className="w-[100px] h-[1px] bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent mt-1"></div>
        </div>
    );
};

export default ThoughtStream;
