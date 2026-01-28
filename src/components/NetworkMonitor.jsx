import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere } from '@react-three/drei';
import { Activity, Globe, Wifi, ArrowUp, ArrowDown } from 'lucide-react';
import * as THREE from 'three';

// --- 3D Components ---

// Helper: Convert Lat/Lon to 3D Vector
const latLonToVector3 = (lat, lon, radius) => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = (radius * Math.sin(phi) * Math.sin(theta));
    const y = (radius * Math.cos(phi));
    return new THREE.Vector3(x, y, z);
};

const ConnectionLines = ({ connections, radius = 1.6 }) => {
    // Arbitrary "Home" location (e.g., New York, or wherever user is approximately)
    // In a real app, we'd fetch this. Using Lat 30, Lon -90 (US) for demo.
    const homePos = useMemo(() => latLonToVector3(30, -90, radius), [radius]);

    return (
        <group>
            {connections.map((conn, i) => {
                if (!conn.lat || !conn.lon) return null;
                const targetPos = latLonToVector3(conn.lat, conn.lon, radius);

                // Curve control point (midpoint + height)
                const mid = new THREE.Vector3().addVectors(homePos, targetPos).multiplyScalar(0.5);
                const distance = homePos.distanceTo(targetPos);
                mid.normalize().multiplyScalar(radius + distance * 0.5); // Arc height based on distance

                // Create Curve
                const curve = new THREE.QuadraticBezierCurve3(homePos, mid, targetPos);
                const points = curve.getPoints(20);

                return (
                    <line key={conn.ip + i}>
                        <bufferGeometry>
                            <bufferAttribute
                                attach="attributes-position"
                                count={points.length}
                                array={new Float32Array(points.flatMap(p => [p.x, p.y, p.z]))}
                                itemSize={3}
                            />
                        </bufferGeometry>
                        <lineBasicMaterial color="#06b6d4" transparent opacity={0.6} linewidth={1} />
                    </line>
                );
            })}
            {/* Home Marker */}
            <mesh position={homePos}>
                <sphereGeometry args={[0.03, 8, 8]} />
                <meshBasicMaterial color="#ffffff" />
            </mesh>
        </group>
    );
};

const DottedGlobe = ({ connections = [] }) => {
    const globeRef = useRef();

    useFrame((state, delta) => {
        if (globeRef.current) {
            globeRef.current.rotation.y += delta * 0.05; // Very slow auto-spin
        }
    });

    // Create dots geometry
    const dots = useMemo(() => {
        const temp = [];
        const numPoints = 2000;
        for (let i = 0; i < numPoints; i++) {
            const phi = Math.acos(-1 + (2 * i) / numPoints);
            const theta = Math.sqrt(numPoints * Math.PI) * phi;
            const x = 1.6 * Math.cos(theta) * Math.sin(phi);
            const y = 1.6 * Math.sin(theta) * Math.sin(phi);
            const z = 1.6 * Math.cos(phi);
            temp.push(new THREE.Vector3(x, y, z));
        }
        return temp;
    }, []);

    return (
        <group ref={globeRef}>
            {/* Dots */}
            {dots.map((pos, i) => (
                <mesh key={i} position={pos}>
                    <sphereGeometry args={[0.015, 4, 4]} />
                    <meshBasicMaterial color="#06b6d4" />
                </mesh>
            ))}
            {/* Minimal inner core for depth */}
            <Sphere args={[1.55, 32, 32]}>
                <meshBasicMaterial color="#0891b2" transparent opacity={0.1} wireframe={false} />
            </Sphere>

            {/* Active Connections Arcs */}
            <ConnectionLines connections={connections} />
        </group>
    );
};


// --- 2D Graph Component ---

const TrafficGraph = ({ data, width, height }) => {
    // data is array of {up: val, down: val}
    // we scale to width/height
    if (data.length < 2) return null;

    const maxVal = Math.max(...data.map(d => Math.max(d.up, d.down, 1024))); // Min 1KB scale

    // Polyline points
    const getPoints = (key) => {
        return data.map((d, i) => {
            const x = (i / (data.length - 1)) * width || 0;
            const val = d[key] || 0;
            const y = height - ((val / (maxVal || 1)) * height) || 0;
            return `${x},${y}`;
        }).join(' ');
    };

    return (
        <svg width={width} height={height} className="overflow-visible">
            {/* Upload Line (Blue) */}
            <polyline
                points={getPoints('up')}
                fill="none"
                stroke="#3b82f6"
                strokeWidth="1.5"
                vectorEffect="non-scaling-stroke"
            />
            {/* Download Line (Cyan) */}
            <polyline
                points={getPoints('down')}
                fill="none"
                stroke="#22d3ee"
                strokeWidth="1.5"
                vectorEffect="non-scaling-stroke"
            />
        </svg>
    );
};


// --- Main Component ---

const NetworkMonitor = ({ socket }) => {
    const [netStats, setNetStats] = useState({ up_rate: 0, down_rate: 0, ip: 'LOADING...' });
    const [trafficHistory, setTrafficHistory] = useState(new Array(30).fill({ up: 0, down: 0 }));

    useEffect(() => {
        if (!socket) return;

        const handleStats = (data) => {
            if (data.network) {
                setNetStats(data.network);
                setTrafficHistory(prev => {
                    const next = [...prev, { up: data.network.up_rate, down: data.network.down_rate }];
                    if (next.length > 30) next.shift();
                    return next;
                });
            }
        };

        socket.on('system_stats', handleStats);
        return () => socket.off('system_stats', handleStats);
    }, [socket]);

    const formatBytes = (bytes) => {
        if (!bytes || isNaN(bytes) || bytes === 0) return '0 B/s';
        const k = 1024;
        const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        if (i < 0) return '0 B/s';
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    return (
        <div className="h-full w-full flex flex-col font-mono text-cyan-500 overflow-hidden relative">

            {/* Header */}
            <div className="flex items-center justify-between border-b border-cyan-500/30 pb-2 px-4 pt-4 shrink-0 bg-black/20">
                <div className="flex items-center gap-2">
                    <Wifi size={16} className="text-cyan-400" />
                    <span className="font-bold tracking-widest text-sm uppercase">Link Status</span>
                </div>
                <div className="text-[10px] text-cyan-600">
                    STATUS: <span className="text-green-400 font-bold">STABLE</span>
                </div>
            </div>

            {/* Link Details */}
            <div className="flex-1 flex flex-col p-4 gap-4 overflow-y-auto">
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-cyan-500/5 border border-cyan-500/20 p-3 rounded-lg">
                        <div className="text-[10px] text-cyan-700 uppercase mb-1">Local Address</div>
                        <div className="text-sm font-bold text-cyan-100">{netStats.ip || '127.0.0.1'}</div>
                    </div>
                    <div className="bg-cyan-500/5 border border-cyan-500/20 p-3 rounded-lg text-right">
                        <div className="text-[10px] text-cyan-700 uppercase mb-1">Latency</div>
                        <div className="text-sm font-bold text-cyan-300">24ms</div>
                    </div>
                </div>

                <div className="space-y-3">
                    <div className="flex justify-between items-center text-[10px] text-cyan-600 uppercase tracking-tighter">
                        <span>Signal Integrity</span>
                        <span className="text-cyan-400">98.4%</span>
                    </div>
                    <div className="h-1 bg-cyan-900/30 rounded-full overflow-hidden">
                        <div className="h-full bg-cyan-500/50 w-[98%] shadow-[0_0_8px_rgba(6,182,212,0.5)]"></div>
                    </div>

                    <div className="flex justify-between items-center text-[10px] text-cyan-600 uppercase tracking-tighter">
                        <span>Packet Loss</span>
                        <span className="text-green-400">0.00%</span>
                    </div>
                    <div className="h-1 bg-cyan-900/30 rounded-full overflow-hidden">
                        <div className="h-full bg-green-500/30 w-[1%]"></div>
                    </div>
                </div>

                <div className="mt-auto pt-4 border-t border-cyan-500/10">
                    <div className="flex justify-between text-[10px] text-cyan-700 mb-2 font-bold uppercase">
                        <span>Traffic Analysis</span>
                        <span>30 Sec Window</span>
                    </div>
                </div>
            </div>

            {/* Traffic Monitor (Bottom) */}
            <div className="h-32 bg-black/40 flex flex-col p-3 shrink-0 border-t border-cyan-500/20">
                <div className="flex justify-between items-center mb-2 text-[10px]">
                    <span className="flex items-center gap-1 text-blue-400"><ArrowUp size={10} /> {formatBytes(netStats.up_rate)}</span>
                    <span className="flex items-center gap-1 text-cyan-400"><ArrowDown size={10} /> {formatBytes(netStats.down_rate)}</span>
                </div>

                <div className="flex-1 relative border-l border-b border-cyan-500/10 ml-1 mb-1">
                    <div className="absolute inset-0">
                        <TrafficGraph data={trafficHistory} width={320} height={60} />
                    </div>
                </div>
            </div>

        </div>
    );
};

export default NetworkMonitor;
