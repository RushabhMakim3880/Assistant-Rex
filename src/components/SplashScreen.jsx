import React from 'react';
import { motion } from 'framer-motion';

const SplashScreen = () => {
    return (
        <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.8, ease: "easeInOut" } }}
            className="fixed inset-0 z-[100] bg-black flex flex-col items-center justify-center overflow-hidden"
        >
            {/* Background Effects */}
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none mix-blend-overlay"></div>
            <div className="absolute inset-0 bg-gradient-to-b from-cyan-900/10 via-black to-black pointer-events-none"></div>

            {/* Central Content */}
            <div className="relative z-10 flex flex-col items-center">
                {/* Logo / Title */}
                <motion.h1
                    initial={{ opacity: 0, scale: 0.8, filter: "blur(10px)" }}
                    animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    className="text-8xl md:text-9xl font-black text-transparent bg-clip-text bg-gradient-to-b from-cyan-100 to-cyan-500 tracking-tighter drop-shadow-[0_0_25px_rgba(34,211,238,0.5)] mb-4"
                >
                    R.E.X.
                </motion.h1>

                {/* Subtitle / System Text */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5, duration: 1 }}
                    className="flex flex-col items-center gap-2"
                >
                    <p className="text-cyan-700 font-mono text-sm tracking-[0.5em] uppercase">
                        Advanced Agentic Intelligence
                    </p>

                    {/* Animated Separator */}
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: "100px" }}
                        transition={{ delay: 1, duration: 0.8 }}
                        className="h-px bg-cyan-500/50 mt-4"
                    />

                    {/* Status Text Scanning */}
                    <div className="mt-8 h-6 overflow-hidden relative">
                        <motion.p
                            animate={{ opacity: [0.4, 1, 0.4] }}
                            transition={{ repeat: Infinity, duration: 2 }}
                            className="text-cyan-900 font-mono text-xs uppercase"
                        >
                            Initializing Neural Interfaces...
                        </motion.p>
                    </div>
                </motion.div>
            </div>

            {/* Bottom Tech Details */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5, duration: 1 }}
                className="absolute bottom-8 left-0 right-0 text-center"
            >
                <p className="text-cyan-950 font-mono text-[10px] tracking-widest">
                    SYSTEM VERSION 2.0.4 // SECURE CONNECTION ESTABLISHED
                </p>
            </motion.div>
        </motion.div>
    );
};

export default SplashScreen;
