import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, MeshDistortMaterial, Float, Stars } from '@react-three/drei';
import * as THREE from 'three';

const GlobeShader = {
    uniforms: {
        time: { value: 0 },
        color: { value: new THREE.Color("#00f2ff") },
    },
    vertexShader: `
        varying vec2 vUv;
        varying vec3 vNormal;
        void main() {
            vUv = uv;
            vNormal = normalize(normalMatrix * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
    `,
    fragmentShader: `
        uniform float time;
        uniform vec3 color;
        varying vec2 vUv;
        varying vec3 vNormal;
        void main() {
            float intensity = pow(0.7 - dot(vNormal, vec3(0, 0, 1.0)), 3.0);
            float scanline = sin(vUv.y * 100.0 + time * 5.0) * 0.1;
            gl_FragColor = vec4(color, intensity + scanline);
        }
    `
};

// Helper: Convert Lat/Lon to 3D Vector
const latLonToVector3 = (lat, lon, radius) => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = (radius * Math.sin(phi) * Math.sin(theta));
    const y = (radius * Math.cos(phi));
    return new THREE.Vector3(x, y, z);
};

const NetworkArcs = ({ connections = [] }) => {
    // Memoize arcs based on connections change
    const arcs = useMemo(() => {
        const radius = 2.05;
        // Default home (US/NY approx)
        const start = latLonToVector3(40.7, -74.0, radius);

        return connections.slice(0, 20).map(conn => { // Limit to 20 lines
            if (!conn.lat || !conn.lon) return null;

            const end = latLonToVector3(parseFloat(conn.lat), parseFloat(conn.lon), radius);

            // Curve control point
            const mid = start.clone().lerp(end, 0.5).normalize().multiplyScalar(radius * 1.3);
            const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
            return { points: curve.getPoints(40), color: "#00f2ff" };
        }).filter(Boolean); // Filter out nulls
    }, [connections]);

    // Fallback if no connections (idle animation)
    const idleArcs = useMemo(() => {
        if (connections.length > 0) return [];
        return Array.from({ length: 5 }).map(() => {
            const start = new THREE.Vector3().setFromSphericalCoords(2.05, Math.random() * Math.PI, Math.random() * Math.PI * 2);
            const end = new THREE.Vector3().setFromSphericalCoords(2.05, Math.random() * Math.PI, Math.random() * Math.PI * 2);
            const mid = start.clone().lerp(end, 0.5).normalize().multiplyScalar(2.5);
            return { points: new THREE.QuadraticBezierCurve3(start, mid, end).getPoints(40), color: "#00f2ff" };
        });
    }, [connections.length]);

    const displayArcs = connections.length > 0 ? arcs : idleArcs;

    return (
        <group>
            {displayArcs.map((arc, i) => (
                <line key={i}>
                    <bufferGeometry attach="geometry">
                        <bufferAttribute
                            attach="attributes-position"
                            count={arc.points.length}
                            array={new Float32Array(arc.points.flatMap(p => [p.x, p.y, p.z]))}
                            itemSize={3}
                        />
                    </bufferGeometry>
                    <lineBasicMaterial attach="material" color={arc.color} transparent opacity={0.4} />
                </line>
            ))}
        </group>
    );
};

// ... DataNodes ...
const DataNodes = ({ count = 40 }) => {
    const positions = useMemo(() => {
        const pos = [];
        for (let i = 0; i < count; i++) {
            const p = new THREE.Vector3().setFromSphericalCoords(
                2.02,
                Math.random() * Math.PI,
                Math.random() * Math.PI * 2
            );
            pos.push(p.x, p.y, p.z);
        }
        return new Float32Array(pos);
    }, [count]);

    return (
        <points>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={count}
                    array={positions}
                    itemSize={3}
                />
            </bufferGeometry>
            <pointsMaterial size={0.03} color="#00f2ff" transparent opacity={0.8} />
        </points>
    );
};

const HolographicGlobe = ({ connections }) => {
    const globeRef = useRef();
    const meshRef = useRef();

    useFrame((state) => {
        const time = state.clock.getElapsedTime();
        if (globeRef.current) globeRef.current.rotation.y = time * 0.1;
        if (meshRef.current) meshRef.current.material.uniforms.time.value = time;
    });

    return (
        <group ref={globeRef}>
            {/* Core Wireframe */}
            <Sphere args={[2, 64, 64]}>
                <meshBasicMaterial wireframe color="#00f2ff" transparent opacity={0.15} />
            </Sphere>

            {/* Holographic Glow Layer */}
            <mesh ref={meshRef}>
                <sphereGeometry args={[2.05, 64, 64]} />
                <shaderMaterial
                    fragmentShader={GlobeShader.fragmentShader}
                    vertexShader={GlobeShader.vertexShader}
                    uniforms={GlobeShader.uniforms}
                    transparent
                />
            </mesh>

            <DataNodes />
            <NetworkArcs connections={connections} />
        </group>
    );
};

const NetworkGlobe = ({ className, connections }) => {
    return (
        <div className={`w-full h-full relative ${className}`}>
            <Canvas camera={{ position: [0, 0, 6], fov: 45 }}>
                <ambientLight intensity={0.5} />
                <pointLight position={[10, 10, 10]} intensity={1} />

                <Float speed={1.5} rotationIntensity={0.5} floatIntensity={0.5}>
                    <HolographicGlobe connections={connections} />
                </Float>

                <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
                <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.5} />
            </Canvas>

            {/* HUD Overlay Elements */}
            <div className="absolute top-4 left-4 pointer-events-none">
                <div className="flex flex-col gap-1 border-l-2 border-cyan-400/50 pl-3">
                    <span className="text-[10px] text-cyan-400/70 uppercase tracking-widest font-mono">Global Link Est.</span>
                    <span className="text-xl text-cyan-400 font-mono font-bold tracking-tighter">CONNECTED</span>
                </div>
            </div>

            <div className="absolute bottom-4 right-4 pointer-events-none text-right">
                <div className="flex flex-col gap-1 border-r-2 border-cyan-400/50 pr-3">
                    <span className="text-[10px] text-cyan-400/70 uppercase tracking-widest font-mono">Traffic Stream</span>
                    <span className="text-lg text-cyan-100/90 font-mono">0.84 TB/S</span>
                </div>
            </div>

            {/* Active Targets List */}
            <div className="absolute top-4 right-4 pointer-events-none text-right">
                <div className="flex flex-col gap-1">
                    <span className="text-[9px] text-cyan-600 uppercase tracking-widest font-mono mb-1">Active Targets</span>
                    {connections.slice(0, 5).map((conn, i) => (
                        <div key={i} className="text-[10px] text-cyan-400 font-mono opacity-80">
                            {conn.ip} <span className="text-cyan-700">::</span> {conn.country || 'UNK'}
                        </div>
                    ))}
                    {connections.length > 5 && (
                        <div className="text-[9px] text-cyan-700 font-mono mt-1">
                            + {connections.length - 5} MORE
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default NetworkGlobe;
