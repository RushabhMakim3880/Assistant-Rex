import React from 'react';
import { Wifi, WifiOff, Activity } from 'lucide-react';

const NetworkStatus = ({ stats = {} }) => {
    const {
        ip = '0.0.0.0',
        ping = 0,
        online = false,
        endpoint = 'Unknown'
    } = stats;

    return (
        <div className="bg-black/40 backdrop-blur-md border border-cyan-500/30 rounded-lg p-4 pointer-events-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-cyan-400 text-xs font-bold tracking-wider">NETWORK STATUS</h3>
                {online ? (
                    <Wifi size={14} className="text-green-400" />
                ) : (
                    <WifiOff size={14} className="text-red-400" />
                )}
            </div>

            {/* Status Grid */}
            <div className="grid grid-cols-2 gap-3 text-[10px]">
                {/* IP Address */}
                <div>
                    <div className="text-cyan-600 mb-1">IP ADDRESS</div>
                    <div className="text-cyan-300 font-mono font-bold">{ip}</div>
                </div>

                {/* Ping */}
                <div>
                    <div className="text-cyan-600 mb-1 flex items-center gap-1">
                        <Activity size={10} />
                        PING
                    </div>
                    <div className="text-cyan-300 font-mono font-bold">{ping}ms</div>
                </div>

                {/* Online Status */}
                <div>
                    <div className="text-cyan-600 mb-1">STATUS</div>
                    <div className={`font-bold ${online ? 'text-green-400' : 'text-red-400'}`}>
                        {online ? 'ONLINE' : 'OFFLINE'}
                    </div>
                </div>

                {/* Endpoint */}
                <div>
                    <div className="text-cyan-600 mb-1">ENDPOINT</div>
                    <div className="text-cyan-300 font-bold truncate">{endpoint}</div>
                </div>
            </div>
        </div>
    );
};

export default NetworkStatus;
