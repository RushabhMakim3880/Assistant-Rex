import React, { useEffect, useRef } from 'react';
import { Paperclip, Image as ImageIcon, Send } from 'lucide-react';

const ChatModule = ({
    messages,
    inputValue,
    setInputValue,
    handleSend,
    isModularMode,
    activeDragElement,
    position,
    width = 672, // default max-w-2xl
    height,
    onMouseDown,
    socket // [NEW] Pass socket for file uploads
}) => {
    const messagesEndRef = useRef(null);
    const fileInputRef = useRef(null); // [NEW]

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleFileClick = () => {
        fileInputRef.current?.click();
    };

    const onFileChange = (e) => {
        const file = e.target.files[0];
        if (!file || !socket) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            const base64Data = event.target.result.split(',')[1];
            socket.emit('file_drop', {
                name: file.name,
                type: file.type,
                data: base64Data
            });
        };
        reader.readAsDataURL(file);
    };

    return (
        <div
            id="chat"
            onMouseDown={onMouseDown}
            className={`flex flex-col pointer-events-auto transition-all duration-200 
            backdrop-blur-xl bg-black/40 border border-cyan-500/30 shadow-2xl rounded-2xl
            ${isModularMode ? (activeDragElement === 'chat' ? 'ring-2 ring-green-500' : 'ring-1 ring-yellow-500/30') : ''}
        `}
            style={{
                left: position?.x || 0,
                top: position?.y || 0,
                transform: isModularMode ? 'translate(-50%, 0)' : 'none', // Only center in modular mode
                width: width,
                height: height,
                position: isModularMode ? 'absolute' : 'relative' // Use relative in grid
            }}
        >
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none mix-blend-overlay"></div>

            {/* Header Bar */}
            <div
                className="h-8 bg-cyan-950/20 border-b border-cyan-500/10 flex items-center justify-between px-4 shrink-0"
            >
                <div className="flex items-center gap-2">
                    <div className="w-1 h-1 rounded-full bg-cyan-500 animate-pulse"></div>
                    <span className="text-[9px] font-bold tracking-[0.2em] text-cyan-600">COMM_LINK // SYSTEM_LOGS</span>
                </div>
                {!isModularMode && (
                    <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 border border-cyan-800 rounded-sm"></div>
                        <div className="w-1.5 h-1.5 border border-cyan-800 rounded-sm"></div>
                    </div>
                )}
            </div>

            <div
                className="flex-1 flex flex-col gap-3 overflow-y-auto p-6 pb-2 scrollbar-hide mask-image-gradient relative z-10"
            >
                {messages.slice(-5).map((msg, i) => (
                    <div key={i} className="text-sm border-l-2 border-cyan-800/50 pl-3 py-1">
                        <span className="text-cyan-600 font-mono text-xs opacity-70">[{msg.time}]</span> <span className="font-bold text-cyan-300 drop-shadow-sm">{msg.sender}</span>
                        <div className="text-gray-300 mt-1 leading-relaxed">{msg.text}</div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <div className="flex gap-2 relative z-10 px-6 pb-4 items-center">
                <input
                    type="file"
                    ref={fileInputRef}
                    onChange={onFileChange}
                    className="hidden"
                    accept="image/*,.pdf,.txt,.py,.js,.json"
                />
                <button
                    onClick={handleFileClick}
                    className="p-2 text-cyan-700 hover:text-cyan-400 transition-colors"
                    title="Upload File"
                >
                    <Paperclip size={20} />
                </button>
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleSend}
                    placeholder="INITIALIZE COMMAND..."
                    className="flex-1 bg-black/40 border border-cyan-700/30 rounded-lg p-3 text-cyan-50 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all placeholder-cyan-800/50 backdrop-blur-sm"
                />
            </div>
            {isModularMode && <div className={`absolute -top-6 left-0 text-xs font-bold tracking-widest ${activeDragElement === 'chat' ? 'text-green-500' : 'text-yellow-500/50'}`}>CHAT MODULE</div>}
        </div>
    );
};

export default ChatModule;
