import React from 'react';

const SystemSchematic = ({ cpuTemp = 50, gpuTemp = 55 }) => {
    // Thresholds for warning colors
    const cpuColor = cpuTemp > 80 ? "#ef4444" : (cpuTemp > 60 ? "#f59e0b" : "#22d3ee");
    const gpuColor = gpuTemp > 80 ? "#ef4444" : (gpuTemp > 60 ? "#f59e0b" : "#22d3ee");

    return (
        <div className="h-full w-full flex flex-col items-center justify-center p-4 relative">
            <svg viewBox="0 0 200 150" className="w-full h-full max-w-[240px] drop-shadow-[0_0_10px_rgba(34,211,238,0.2)]">
                {/* Chassis Outline */}
                <path
                    d="M10,10 L190,10 L190,140 L10,140 Z"
                    fill="none"
                    stroke="#0e7490"
                    strokeWidth="1"
                    className="opacity-50"
                />

                {/* Motherboard */}
                <path
                    d="M20,20 L160,20 L160,130 L20,130 Z"
                    fill="rgba(6,182,212,0.05)"
                    stroke="#0891b2"
                    strokeWidth="0.5"
                />

                {/* CPU Socket Area */}
                <g transform="translate(60, 40)">
                    <rect x="0" y="0" width="40" height="40" fill="none" stroke={cpuColor} strokeWidth="1.5" className="transition-colors duration-500" />
                    <rect x="10" y="10" width="20" height="20" fill={cpuColor} fillOpacity="0.2" />
                    <text x="20" y="55" textAnchor="middle" fill={cpuColor} fontSize="8" fontFamily="monospace">CPU</text>
                    {/* Heat Lines Animation */}
                    {cpuTemp > 60 && (
                        <path d="M5,0 L5,-10 M20,0 L20,-15 M35,0 L35,-10" stroke={cpuColor} strokeWidth="1" className="animate-pulse" />
                    )}
                </g>

                {/* RAM Slots */}
                <g transform="translate(110, 30)">
                    <rect x="0" y="0" width="6" height="60" fill="none" stroke="#0891b2" strokeWidth="0.5" />
                    <rect x="10" y="0" width="6" height="60" fill="none" stroke="#0891b2" strokeWidth="0.5" />
                    <rect x="20" y="0" width="6" height="60" fill="none" stroke="#0891b2" strokeWidth="0.5" />
                    <rect x="30" y="0" width="6" height="60" fill="none" stroke="#0891b2" strokeWidth="0.5" />
                </g>

                {/* GPU Slot */}
                <g transform="translate(30, 95)">
                    <rect x="0" y="0" width="120" height="25" fill="none" stroke={gpuColor} strokeWidth="1.5" rx="2" className="transition-colors duration-500" />
                    {/* Fan Blades (Spinner) */}
                    <circle cx="30" cy="12.5" r="8" fill="none" stroke={gpuColor} strokeWidth="0.5" strokeDasharray="2 2" className={gpuTemp > 50 ? "animate-spin origin-[30px_12.5px]" : ""} />
                    <circle cx="90" cy="12.5" r="8" fill="none" stroke={gpuColor} strokeWidth="0.5" strokeDasharray="2 2" className={gpuTemp > 50 ? "animate-spin origin-[90px_12.5px]" : ""} />

                    <text x="135" y="15" fill={gpuColor} fontSize="8" fontFamily="monospace">GPU</text>
                </g>

                {/* PSU / Power */}
                <g transform="translate(165, 100)">
                    <rect x="0" y="0" width="25" height="40" fill="none" stroke="#0e7490" strokeWidth="0.5" />
                    <text x="12.5" y="25" textAnchor="middle" fill="#0e7490" fontSize="6" fontFamily="monospace" transform="rotate(-90 12.5 25)">PWR</text>
                </g>
            </svg>

            {/* Overlay Info */}
            <div className="absolute top-2 right-2 text-[8px] text-cyan-700 font-mono flex flex-col items-end">
                <span>THERMAL MAP</span>
                <span className="text-cyan-900">REALTIME</span>
            </div>
        </div>
    );
};

export default SystemSchematic;
