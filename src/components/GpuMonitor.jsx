import React from 'react';

const GpuMonitor = ({ gpuData }) => {
    // gpuData = { id, name, load, memoryUsed, memoryTotal, temperature }

    if (!gpuData) {
        return (
            <div className="h-full flex items-center justify-center text-cyan-900/40 text-xs font-mono animate-pulse">
                INITIALIZING GPU TELEMETRY...
            </div>
        );
    }

    const vramPercent = (gpuData.memoryUsed / gpuData.memoryTotal) * 100;

    // Circular Gauge Helper
    const Gauge = ({ value, label, unit, color = "stroke-cyan-400" }) => {
        const radius = 26;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (value / 100) * circumference;

        return (
            <div className="flex flex-col items-center relative">
                <svg className="w-16 h-16 transform -rotate-90">
                    <circle
                        className="text-cyan-900/20"
                        strokeWidth="4"
                        stroke="currentColor"
                        fill="transparent"
                        r={radius}
                        cx="32"
                        cy="32"
                    />
                    <circle
                        className={`${color} transition-all duration-500`}
                        strokeWidth="4"
                        strokeDasharray={circumference}
                        strokeDashoffset={offset}
                        strokeLinecap="round"
                        stroke="currentColor"
                        fill="transparent"
                        r={radius}
                        cx="32"
                        cy="32"
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-[10px] font-bold text-cyan-100">{value.toFixed(0)}</span>
                    <span className="text-[7px] text-cyan-600">{unit}</span>
                </div>
                <span className="text-[8px] text-cyan-700 mt-1 uppercase tracking-wider">{label}</span>
            </div>
        );
    };

    return (
        <div className="flex flex-col h-full font-mono text-cyan-400 p-2">

            {/* Header */}
            <div className="flex justify-between items-center border-b border-cyan-500/20 pb-2 mb-3">
                <div className="flex flex-col">
                    <span className="text-[9px] text-cyan-600 uppercase tracking-widest">GPU CORE</span>
                    <span className="text-xs font-bold text-cyan-300 truncate max-w-[150px]">{gpuData.name}</span>
                </div>
                <div className="flex flex-col items-end">
                    <span className="text-[9px] text-cyan-600 uppercase tracking-widest">TEMP</span>
                    <div className="flex items-center gap-1">
                        <span className={`text-xs font-bold ${gpuData.temperature > 80 ? 'text-red-500 animate-pulse' : 'text-cyan-300'}`}>
                            {gpuData.temperature}°C
                        </span>
                    </div>
                </div>
            </div>

            {/* Gauges Grid */}
            <div className="grid grid-cols-2 gap-2 mb-4">
                <Gauge value={gpuData.load} label="CORE LOAD" unit="%" />
                <Gauge
                    value={(gpuData.temperature / 100) * 100}
                    label="THERMAL"
                    unit="%"
                    color={gpuData.temperature > 75 ? "stroke-amber-500" : "stroke-cyan-400"}
                />
            </div>

            {/* VRAM Bar */}
            <div className="flex-1 min-h-0 flex flex-col justify-end">
                <div className="flex justify-between text-[8px] text-cyan-600 mb-1 uppercase tracking-wider">
                    <span>VRAM USAGE</span>
                    <span>{gpuData.memoryUsed} / {gpuData.memoryTotal} MB</span>
                </div>
                <div className="h-14 bg-black/20 border border-cyan-500/10 relative overflow-hidden group">
                    <div
                        className="absolute bottom-0 left-0 right-0 bg-cyan-500/10 transition-all duration-300 group-hover:bg-cyan-500/20"
                        style={{ height: `${vramPercent}%` }}
                    >
                        <div className="absolute top-0 left-0 right-0 h-[1px] bg-cyan-400/50 shadow-[0_0_8px_rgba(34,211,238,0.5)]"></div>
                    </div>

                    {/* Grid Lines */}
                    <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNCIgaGVpZ2h0PSI0IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIGQ9Ik0gMSAwIEwgMSAxIEwgMCAxIiBmaWxsPSJub25lIiBzdHJva2U9InJnYmEoNiwgMTgyLCAyMTIsIDAuMSkiIHN0cm9rZS13aWR0aD0iMC41Ii8+PC9zdmc+')] opacity-30"></div>
                </div>
                <div className="text-center text-[8px] text-cyan-700 mt-1">Video Random Access Memory</div>
            </div>

        </div>
    );
};

export default GpuMonitor;
