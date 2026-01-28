import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

const NeuralCore = ({ width = 600, height = 500, intensity = 0, state = 'idle' }) => {

    const stateConfigs = {
        idle: { color: '#22d3ee', shadow: 'rgba(34,211,238,0.6)', pulse: 3, scale: 1.1 },
        listening: { color: '#22d3ee', shadow: 'rgba(34,211,238,0.8)', pulse: 1.5, scale: 1.15 },
        thinking: { color: '#a855f7', shadow: 'rgba(168,85,247,0.6)', pulse: 0.8, scale: 1.2 },
        analyzing: { color: '#f59e0b', shadow: 'rgba(245,158,11,0.6)', pulse: 1.2, scale: 1.2 },
        speaking: { color: '#ef4444', shadow: 'rgba(239,68,68,0.6)', pulse: 0.5, scale: 1.3 }
    };

    const config = stateConfigs[state] || stateConfigs.idle;

    return (
        <div className="relative flex items-center justify-center" style={{ width, height }}>
            {/* R.E.X Logo Overlay */}
            <div className="z-20 pointer-events-none">
                <div
                    className="font-bold tracking-[0.5em] transition-colors duration-500 drop-shadow-[0_0_15px_rgba(34,211,238,0.8)]"
                    style={{
                        color: config.color,
                        textShadow: `0 0 20px ${config.shadow}`
                    }}
                >
                    R.E.X
                </div>
            </div>

            {/* Pulsing Rings (CSS/Framer Motion) */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                {/* Ring 1: Fast Pulse (Audio React) */}
                <motion.div
                    animate={{
                        scale: 1 + (intensity * 0.3),
                        opacity: 0.3 + (intensity * 0.5),
                        borderColor: config.color,
                        boxShadow: `0 0 20px ${config.shadow}, inset 0 0 20px ${config.shadow}`
                    }}
                    transition={{ duration: 0.1 }}
                    className="absolute rounded-full border-2"
                    style={{
                        width: '180px',
                        height: '180px'
                    }}
                />

                {/* Ring 2: Dynamic Breathe (Based on State) */}
                <motion.div
                    animate={{
                        scale: [1, config.scale, 1],
                        opacity: [0.1, 0.4, 0.1],
                        borderColor: config.color
                    }}
                    transition={{
                        duration: config.pulse,
                        repeat: Infinity,
                        ease: "easeInOut"
                    }}
                    key={state} // Re-mount or re-trigger animation on state change to reset duration
                    className="absolute rounded-full border"
                    style={{
                        width: '240px',
                        height: '240px'
                    }}
                />

                {/* Core Glow */}
                <motion.div
                    animate={{
                        opacity: 0.2 + (intensity * 0.2),
                        backgroundColor: config.color
                    }}
                    transition={{ duration: 0.5 }}
                    className="absolute rounded-full blur-[40px]"
                    style={{
                        width: '100px',
                        height: '100px'
                    }}
                />
            </div>
        </div>
    );
};

export default NeuralCore;
