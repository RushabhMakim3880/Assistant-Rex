import React, { useState, useEffect } from 'react';
import GpuMonitor from './GpuMonitor';
import SystemSchematic from './SystemSchematic';

const SystemMonitor = ({ socket, isVideoOn, alerts }) => {
    const [stats, setStats] = useState({
        cpu: 0,
        ram: { percent: 0, used: 0, total: 0 },
        disk: { percent: 0, free: 0 },
        gpu: null, // [NEW]
        processes: [],
        info: { node: 'UNKNOWN', os: 'WIN-SYSTEM', processor: 'INTEL' }
    });

    const [viewMode, setViewMode] = useState('SYS'); // SYS | GPU | MAP
    const [cpuHistory, setCpuHistory] = useState(new Array(50).fill(0));
    const [ramHistory, setRamHistory] = useState(new Array(50).fill(0));
    const [currentTime, setCurrentTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        if (!socket) return;
        const handleStats = (data) => {
            if (data) {
                setStats(prev => ({
                    ...prev,
                    ...data,
                    cpu: data.cpu ?? prev.cpu ?? 0,
                    ram: { ...prev.ram, ...(data.ram || {}) },
                    disk: { ...prev.disk, ...(data.disk || {}) },
                    gpu: data.gpu || prev.gpu || null,
                    processes: data.processes || []
                }));
                setCpuHistory(prev => {
                    const next = [...prev, data.cpu ?? 0];
                    if (next.length > 50) next.shift();
                    return next;
                });
                setRamHistory(prev => {
                    const next = [...prev, data.ram?.percent ?? 0];
                    if (next.length > 50) next.shift();
                    return next;
                });
            }
        };
        socket.on('system_stats', handleStats);
        return () => socket.off('system_stats', handleStats);
    }, [socket]);

    const getGraphPath = (history, height = 40) => {
        if (history.length < 2) return `0,${height} 100,${height}`;
        return history.map((val, i) => {
            const x = (i / (history.length - 1)) * 100;
            const y = height - ((val / 100) * height);
            return `${x},${y}`;
        }).join(' ');
    };

    return (
        <div className="h-full w-full flex flex-col p-4 font-mono text-cyan-400 overflow-hidden bg-black/40 select-none relative">

            {/* Header Tabs */}
            <div className="flex justify-between items-center mb-4 pb-2 border-b border-cyan-500/20 z-10">
                <div className="flex gap-4">
                    {['SYS', 'GPU', 'MAP'].map(mode => (
                        <button
                            key={mode}
                            onClick={() => setViewMode(mode)}
                            className={`text-[10px] tracking-widest font-bold transition-colors hover:text-cyan-200 
                                ${viewMode === mode ? 'text-cyan-400 border-b border-cyan-400' : 'text-cyan-800'}`}
                        >
                            {mode}
                        </button>
                    ))}
                </div>
                <div className="text-[10px] text-cyan-700 font-bold">
                    {currentTime.toLocaleTimeString([], { hour12: false })}
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto min-h-0 relative">

                {viewMode === 'SYS' && (
                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                        {/* System Info Grid */}
                        <div className="grid grid-cols-4 gap-3 text-[10px] mb-4 text-cyan-600">
                            <div className="flex flex-col">
                                <span className="text-cyan-400 font-bold">2051</span>
                                <span className="text-cyan-700">SEP 9</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-cyan-400 font-bold">{stats.cpu?.toFixed(0) || 0}%</span>
                                <span className="text-cyan-700">UPTIME</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-cyan-400 font-bold">{stats.info?.os?.split(' ')[0] || 'linux'}</span>
                                <span className="text-cyan-700">TYPE</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-cyan-400 font-bold">ON</span>
                                <span className="text-cyan-700">POWER</span>
                            </div>
                        </div>

                        {/* Manufacturer Info */}
                        <div className="grid grid-cols-3 gap-3 text-[9px] mb-4 text-cyan-700">
                            <div className="flex flex-col">
                                <span className="text-cyan-800 text-[8px] uppercase">MANUFACTURER</span>
                                <span className="text-cyan-500 font-bold truncate">{stats.info?.manufacturer || 'LOADING...'}</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-cyan-800 text-[8px] uppercase">MODEL</span>
                                <span className="text-cyan-500 font-bold truncate">{stats.info?.model || 'LOADING...'}</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-cyan-800 text-[8px] uppercase">BIOS</span>
                                <span className="text-cyan-500 font-bold truncate">{stats.info?.bios || 'LOADING...'}</span>
                            </div>
                        </div>

                        {/* CPU Usage Graph */}
                        <div className="mb-4">
                            <div className="flex justify-between text-[10px] mb-1.5">
                                <span className="text-cyan-700 font-bold">CPU USAGE</span>
                                <span className="text-cyan-400 font-bold">{stats.cpu?.toFixed(1) || 0}%</span>
                            </div>
                            <div className="h-12 bg-black/60 border border-cyan-500/20 relative">
                                <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 40">
                                    <polyline
                                        points={getGraphPath(cpuHistory, 40)}
                                        fill="none"
                                        stroke="#22d3ee"
                                        strokeWidth="0.8"
                                        vectorEffect="non-scaling-stroke"
                                    />
                                </svg>
                            </div>
                        </div>

                        {/* Memory Visualization */}
                        <div className="mb-4">
                            <div className="flex justify-between items-end mb-1.5 text-[10px] uppercase font-mono tracking-wider">
                                <span className="text-cyan-500 font-bold">MEMORY</span>
                                <span className="text-cyan-700">USING {stats.ram?.used || 0} OUT OF {stats.ram?.total || 16} GIB</span>
                            </div>
                            <div className="flex flex-wrap gap-[2px]">
                                {Array.from({ length: 240 }).map((_, i) => {
                                    const filled = i < ((stats.ram?.percent || 0) / 100) * 240;
                                    return (
                                        <div
                                            key={i}
                                            className={`w-[3px] h-[3px] rounded-[0.5px] ${filled ? 'bg-cyan-400 shadow-[0_0_2px_rgba(34,211,238,0.8)]' : 'bg-cyan-900/20'}`}
                                        />
                                    );
                                })}
                            </div>
                            <div className="flex justify-between text-[8px] text-cyan-800 mt-1 uppercase tracking-widest opacity-60">
                                <span>DIMM 0</span>
                                <span>{stats.ram?.percent || 0}% ALLOCATED</span>
                            </div>
                        </div>

                        {/* Top Processes */}
                        <div className="flex-1 min-h-0">
                            <div className="text-[10px] text-cyan-700 mb-2 font-bold">TOP PROCESSES</div>
                            <div className="space-y-1 overflow-y-auto max-h-[180px]">
                                {stats.processes.slice(0, 8).map((p, i) => (
                                    <div key={i} className="flex justify-between text-[9px] text-cyan-600 leading-relaxed">
                                        <span className="truncate max-w-[60px] text-cyan-500">{p.pid || (73497 + i)}</span>
                                        <span className="truncate max-w-[100px] text-cyan-400">{p.name || 'process'}</span>
                                        <span className="text-cyan-300 font-bold">{Number(p.cpu || (Math.random() * 10)).toFixed(1)}%</span>
                                        <span className="text-cyan-300 font-bold">{Number(p.mem || (Math.random() * 5)).toFixed(1)}%</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {viewMode === 'GPU' && (
                    <div className="h-full animate-in fade-in slide-in-from-right-2 duration-300">
                        <GpuMonitor gpuData={stats.gpu} />
                    </div>
                )}

                {viewMode === 'MAP' && (
                    <div className="h-full animate-in fade-in slide-in-from-right-2 duration-300">
                        <SystemSchematic cpuTemp={50 + (stats.cpu / 3)} gpuTemp={stats.gpu?.temperature || 55} />
                    </div>
                )}

            </div>
        </div>
    );
};

export default SystemMonitor;
