import React, { useEffect, useRef } from 'react';

const TopAudioBar = ({ audioData, shadowTasks = [] }) => {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        let animationFrame;
        const draw = () => {
            const width = canvas.width;
            const height = canvas.height;
            ctx.clearRect(0, 0, width, height);

            const barWidth = 4;
            const gap = 2;
            const totalBars = Math.floor(width / (barWidth + gap));

            const center = width / 2;

            for (let i = 0; i < totalBars / 2; i++) {
                const value = audioData[i % audioData.length] || 0;
                const percent = value / 255;
                const barHeight = Math.max(2, percent * height);

                ctx.fillStyle = `rgba(34, 211, 238, ${0.2 + percent * 0.8})`;

                // Right side
                ctx.fillRect(center + i * (barWidth + gap), (height - barHeight) / 2, barWidth, barHeight);
                // Left side
                ctx.fillRect(center - (i + 1) * (barWidth + gap), (height - barHeight) / 2, barWidth, barHeight);
            }
            animationFrame = requestAnimationFrame(draw);
        };

        draw();
        return () => cancelAnimationFrame(animationFrame);
    }, [audioData]);

    return (
        <div className="relative">
            {shadowTasks.length > 0 && (
                <div className="absolute top-0 right-0 flex items-center gap-2 px-2 py-1 bg-cyan-900/40 rounded-full border border-cyan-400/30 text-[10px] text-cyan-300 animate-pulse">
                    <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full" />
                    SHADOW: {shadowTasks.length}
                </div>
            )}
            <canvas
                ref={canvasRef}
                width={300}
                height={40}
                className="opacity-80"
            />
        </div>
    );
};

export default TopAudioBar;
