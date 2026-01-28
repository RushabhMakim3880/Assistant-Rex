import React, { useState, useEffect } from 'react';

const TerminalView = ({ socket }) => {
    const [systemInfo, setSystemInfo] = useState({
        uptime: '55:10:50',
        loadAvg: [4.85, 2.84, 2.10],
        cpuUsage: 38.61,
        memTotal: 31814,
        memUsed: 23812,
        memFree: 7239,
        processes: []
    });

    useEffect(() => {
        if (!socket) return;

        socket.on('system_stats', (data) => {
            if (data.cpu) {
                setSystemInfo(prev => ({
                    ...prev,
                    cpuUsage: data.cpu.usage || prev.cpuUsage
                }));
            }
            if (data.memory) {
                setSystemInfo(prev => ({
                    ...prev,
                    memTotal: data.memory.total || prev.memTotal,
                    memUsed: data.memory.used || prev.memUsed,
                    memFree: data.memory.free || prev.memFree
                }));
            }
            if (data.processes) {
                setSystemInfo(prev => ({
                    ...prev,
                    processes: data.processes.slice(0, 20)
                }));
            }
        });

        return () => {
            socket.off('system_stats');
        };
    }, [socket]);

    const formatBytes = (bytes) => {
        if (bytes < 1024) return `${bytes}B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}K`;
        if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(0)}M`;
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)}G`;
    };

    return (
        <div className="h-full bg-black/40 backdrop-blur-md border border-cyan-500/30 rounded-lg p-3 font-mono text-[10px] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between mb-2 pb-2 border-b border-cyan-500/20">
                <div className="flex items-center gap-4">
                    <span className="text-cyan-400 font-bold">MAIN - bash</span>
                    <span className="text-cyan-600">EMPTY</span>
                </div>
                <div className="text-cyan-600">
                    {new Date().toLocaleTimeString('en-US', { hour12: false })}
                </div>
            </div>

            {/* System Info Block */}
            <div className="mb-3 text-cyan-300 leading-tight space-y-0.5">
                <div>
                    System total, {systemInfo.processes.length} running, 706 sleeping, 0 stopped, 0 zombie threads
                </div>
                <div>
                    Load Avg: {systemInfo.loadAvg[0]}, {systemInfo.loadAvg[1]}, {systemInfo.loadAvg[2]}
                    <span className="ml-4">CPU usage: {systemInfo.cpuUsage.toFixed(2)}% user, 29.70% sys, 31.68% idle</span>
                </div>
                <div>
                    SharedLibs: 479M resident, 123M data, 103M linkedit.
                </div>
                <div>
                    MemRegions: 318147 total, 5823M resident, 190M private, 2646M shared.
                </div>
                <div>
                    PhysMem: 16G used (6834M wired), 1003M unused.
                </div>
                <div>
                    VM: 13T virt, 4299M framework vsz, 6281810(0) swapins, 49223315(0) swapouts.
                </div>
                <div>
                    Networks: packets: 21238244/27G in, 26612975/3179M out.
                </div>
                <div>
                    Disks: 56538872/266G read, 46745334/276G written.
                </div>
            </div>

            {/* Process Table Header */}
            <div className="grid grid-cols-[60px_200px_60px_80px_60px_60px_60px_60px_60px_60px] gap-2 text-cyan-600 font-bold mb-1 pb-1 border-b border-cyan-500/20">
                <div>PID</div>
                <div>COMMAND</div>
                <div>%CPU</div>
                <div>TIME</div>
                <div>#TH</div>
                <div>#WQ</div>
                <div>#PORTS</div>
                <div>MEM</div>
                <div>PURG</div>
                <div>CMPRS</div>
            </div>

            {/* Process Table Body - Scrollable */}
            <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-cyan-500/30 scrollbar-track-transparent">
                {systemInfo.processes.length > 0 ? (
                    systemInfo.processes.map((proc, idx) => (
                        <div
                            key={idx}
                            className="grid grid-cols-[60px_200px_60px_80px_60px_60px_60px_60px_60px_60px] gap-2 text-cyan-300 py-0.5 hover:bg-cyan-500/10"
                        >
                            <div>{proc.pid || '95089'}</div>
                            <div className="truncate">{proc.name || 'eDEX-UI'}</div>
                            <div>{proc.cpu?.toFixed(1) || '96.2'}</div>
                            <div>{proc.time || '01:15.98'}</div>
                            <div>{proc.threads || '21/1'}</div>
                            <div>{proc.wq || '1'}</div>
                            <div>{proc.ports || '139'}</div>
                            <div>{formatBytes(proc.memory || 227000000)}</div>
                            <div>0B</div>
                            <div>0B</div>
                        </div>
                    ))
                ) : (
                    // Placeholder data when no processes
                    Array.from({ length: 15 }).map((_, idx) => (
                        <div
                            key={idx}
                            className="grid grid-cols-[60px_200px_60px_80px_60px_60px_60px_60px_60px_60px] gap-2 text-cyan-300/50 py-0.5"
                        >
                            <div>{95089 + idx}</div>
                            <div>Process-{idx}</div>
                            <div>{(Math.random() * 100).toFixed(1)}</div>
                            <div>00:{String(idx).padStart(2, '0')}.{String(Math.floor(Math.random() * 100)).padStart(2, '0')}</div>
                            <div>{Math.floor(Math.random() * 50)}/1</div>
                            <div>1</div>
                            <div>{Math.floor(Math.random() * 500)}</div>
                            <div>{formatBytes(Math.floor(Math.random() * 500000000))}</div>
                            <div>0B</div>
                            <div>0B</div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default TerminalView;
