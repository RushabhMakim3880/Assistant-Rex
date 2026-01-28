import React, { useEffect, useState, useRef } from 'react';
import { Cpu, RefreshCw, Check, X, Box, Info, Server, Activity } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const LlmWindow = ({
    onClose,
    socket,
    llmProvider,
    onSwitchProvider,
    position,
    onMouseDown
}) => {
    const [models, setModels] = useState([]);
    const [loading, setLoading] = useState(false);
    const [currentModel, setCurrentModel] = useState('');
    const [error, setError] = useState(null);
    const [status, setStatus] = useState('Checking server...');
    const fetchTimeoutRef = useRef(null);
    const isLoadingRef = useRef(false);

    const fetchModels = () => {
        console.log("[LLM DEBUG] fetchModels called");
        setLoading(true);
        isLoadingRef.current = true;
        setStatus('Connecting to Ollama...');
        setError(null);
        console.log("[LLM DEBUG] Emitting get_ollama_models...");
        socket.emit('get_ollama_models');

        // Clear existing timeout
        if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);

        // Set 10s timeout for safety
        fetchTimeoutRef.current = setTimeout(() => {
            console.log("[LLM DEBUG] Timeout reached, isLoadingRef.current:", isLoadingRef.current);
            if (isLoadingRef.current) {
                console.log("[LLM] Connection timed out");
                setLoading(false);
                isLoadingRef.current = false;
                setStatus('Connection Timeout');
                setError('Could not reach Ollama server. Ensure it is running at http://127.0.0.1:11434');
            }
        }, 10000);
    };

    useEffect(() => {
        fetchModels();

        const handleModels = (data) => {
            console.log("[LLM] Received models:", data);

            // Clear timeout as we got a response
            if (fetchTimeoutRef.current) {
                clearTimeout(fetchTimeoutRef.current);
                fetchTimeoutRef.current = null;
            }

            setModels(data);
            setLoading(false);
            isLoadingRef.current = false;
            if (data && data.length > 0) {
                setStatus('Server Online');
                setError(null);
            } else {
                setStatus('Online (No Models)');
                setError('No models found. Run "ollama pull llama3" in your terminal.');
            }
        };

        socket.on('ollama_models', handleModels);

        return () => {
            socket.off('ollama_models', handleModels);
            if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
        };
    }, []);

    const selectModel = (modelName) => {
        setCurrentModel(modelName);
        socket.emit('set_ollama_model', { model: modelName });
    };

    return (
        <motion.div
            id="llm"
            onMouseDown={onMouseDown}
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="absolute z-50 w-80 backdrop-blur-2xl bg-black/60 border border-indigo-500/30 rounded-2xl shadow-[0_0_30px_rgba(99,102,241,0.2)] overflow-hidden"
            style={{
                left: position?.x || '50%',
                top: position?.y || '50%',
                transform: 'translate(-50%, -50%)',
                pointerEvents: 'auto'
            }}
        >
            {/* Header */}
            <div className="px-4 py-3 border-b border-indigo-500/20 flex justify-between items-center bg-indigo-500/10">
                <div className="flex items-center gap-2">
                    <Cpu size={18} className="text-indigo-400 animate-pulse" />
                    <span className="text-xs font-bold tracking-widest text-indigo-300 uppercase">Local LLM Core</span>
                </div>
                <button onClick={onClose} className="text-indigo-400 hover:text-white transition-colors">
                    <X size={18} />
                </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
                {/* Status Card */}
                <div className="bg-black/40 border border-indigo-500/10 rounded-xl p-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${models.length > 0 ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
                            <Server size={16} />
                        </div>
                        <div>
                            <div className="text-[10px] text-indigo-300/50 uppercase font-bold">Ollama Status</div>
                            <div className="text-xs text-white font-medium">{status}</div>
                        </div>
                    </div>
                    <button
                        onClick={fetchModels}
                        className={`p-2 rounded-lg hover:bg-white/5 text-indigo-400 transition-all ${loading ? 'animate-spin' : ''}`}
                    >
                        <RefreshCw size={14} />
                    </button>
                </div>

                {/* Provider Toggle */}
                <div className="flex bg-black/40 p-1 rounded-xl border border-white/5">
                    <button
                        onClick={() => onSwitchProvider('gemini')}
                        className={`flex-1 py-2 text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all ${llmProvider === 'gemini'
                            ? 'bg-cyan-500 text-white shadow-[0_0_10px_rgba(6,182,212,0.5)]'
                            : 'text-cyan-400/50 hover:text-cyan-400'}`}
                    >
                        Gemini 2.0
                    </button>
                    <button
                        onClick={() => onSwitchProvider('ollama')}
                        className={`flex-1 py-2 text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all ${llmProvider === 'ollama'
                            ? 'bg-indigo-500 text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]'
                            : 'text-indigo-400/50 hover:text-indigo-400'}`}
                    >
                        Local Ollama
                    </button>
                </div>

                {/* Model List */}
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
                    <div className="text-[10px] text-indigo-300/30 uppercase font-bold px-1">Available Models</div>
                    {models.length === 0 && !loading && (
                        <div className="text-center py-4 text-white/20 text-xs italic">
                            No local models detected.
                        </div>
                    )}
                    {models.map((m) => (
                        <button
                            key={m.name}
                            onClick={() => selectModel(m.name)}
                            className={`w-full group px-3 py-2 rounded-xl border transition-all duration-300 flex items-center justify-between ${currentModel === m.name
                                ? 'bg-indigo-500/20 border-indigo-500/50 text-white'
                                : 'bg-white/5 border-transparent text-white/60 hover:border-indigo-500/30 hover:bg-indigo-500/5 hover:text-white'}`}
                        >
                            <div className="flex items-center gap-3">
                                <Box size={14} className={currentModel === m.name ? 'text-indigo-400' : 'text-white/20'} />
                                <div className="text-left">
                                    <div className="text-xs font-medium">{m.name}</div>
                                    <div className="text-[8px] opacity-40 uppercase tracking-tighter">
                                        {(m.size / (1024 * 1024 * 1024)).toFixed(1)} GB • {m.details?.parameter_size || '?'}
                                    </div>
                                </div>
                            </div>
                            {currentModel === m.name && (
                                <motion.div layoutId="check" initial={{ scale: 0 }} animate={{ scale: 1 }}>
                                    <Check size={14} className="text-indigo-400" />
                                </motion.div>
                            )}
                        </button>
                    ))}
                </div>
            </div>

            {/* Footer */}
            <div className="px-4 py-2 bg-black/40 border-t border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[8px] text-indigo-300/40 uppercase font-bold">
                    <Activity size={10} />
                    <span>Neural Inference active</span>
                </div>
                <div className="text-[8px] text-white/20">v1.2.0-OLLAMA</div>
            </div>
        </motion.div>
    );
};

export default LlmWindow;
