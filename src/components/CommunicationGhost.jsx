import React, { useEffect, useState } from 'react';
import { MessageSquare, Phone, X, Check, PhoneOff } from 'lucide-react';

const CommunicationGhost = ({ notification, onAction, onClose }) => {
    if (!notification) return null;

    const { type, contact, message, time } = notification;

    return (
        <div className="fixed top-8 right-8 z-[100] animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="bg-black/80 backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-2xl w-80 overflow-hidden group">
                <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-xl ${type === 'call' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'}`}>
                        {type === 'call' ? <Phone className="w-6 h-6 animate-pulse" /> : <MessageSquare className="w-6 h-6" />}
                    </div>

                    <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-white/40 text-xs font-medium tracking-wider uppercase">
                                Incoming {type}
                            </span>
                            <span className="text-white/20 text-[10px]">{time}</span>
                        </div>
                        <h3 className="text-white font-semibold mb-1 text-lg">{contact}</h3>
                        {message && (
                            <p className="text-white/60 text-sm line-clamp-2 leading-relaxed italic">
                                "{message}"
                            </p>
                        )}
                    </div>

                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-white/5 rounded-lg transition-colors text-white/20 hover:text-white/40"
                    >
                        <X size={16} />
                    </button>
                </div>

                <div className="mt-4 flex gap-2">
                    {type === 'call' ? (
                        <>
                            <button
                                onClick={() => onAction('accept')}
                                className="flex-1 bg-green-500/80 hover:bg-green-500 text-white rounded-xl py-2 flex items-center justify-center gap-2 transition-all font-medium"
                            >
                                <Check size={18} /> Answer
                            </button>
                            <button
                                onClick={() => onAction('decline')}
                                className="flex-1 bg-red-500/20 hover:bg-red-500/40 text-red-400 rounded-xl py-2 flex items-center justify-center gap-2 transition-all font-medium border border-red-500/20"
                            >
                                <PhoneOff size={18} /> Decline
                            </button>
                        </>
                    ) : (
                        <button
                            className="w-full bg-blue-500/20 hover:bg-blue-500/40 text-blue-400 rounded-xl py-2 flex items-center justify-center gap-2 transition-all font-medium border border-blue-500/20"
                        >
                            <MessageSquare size={18} /> AI Draft Reply
                        </button>
                    )}
                </div>

                {/* Glass reflection effect */}
                <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent pointer-events-none" />
            </div>
        </div>
    );
};

export default CommunicationGhost;
