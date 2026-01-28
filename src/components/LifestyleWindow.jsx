import React, { useState, useEffect } from 'react';
import { X, RefreshCw, Globe, TrendingUp, TrendingDown, Sun, Trophy, Newspaper } from 'lucide-react';

const LifestyleWindow = ({ onClose }) => {
    const [marketPulse, setMarketPulse] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchPulse = async () => {
            try {
                const res = await fetch('http://localhost:8000/market_pulse');
                const json = await res.json();
                if (json && !json.error) {
                    setMarketPulse(json);
                }
            } catch (e) {
                console.error("Pulse Fetch Error:", e);
            } finally {
                setIsLoading(false);
            }
        };
        fetchPulse();
    }, []);

    const formatDate = (timestamp) => {
        if (!timestamp) return 'LIVE';
        return new Date(timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    if (isLoading) {
        return (
            <div className="fixed inset-48 z-50 flex items-center justify-center bg-[#0a0a0b]/90 backdrop-blur-3xl border border-white/10 rounded-[2rem]">
                <RefreshCw className="text-amber-400 animate-spin" size={32} />
            </div>
        );
    }

    return (
        <div className="fixed inset-8 z-50 flex flex-col bg-[#050505] backdrop-blur-3xl border border-white/5 rounded-[2rem] overflow-hidden shadow-[0_0_150px_rgba(0,0,0,0.8)] font-sans text-white select-none animate-in fade-in zoom-in-95 duration-300">

            {/* Ambient Background - Warmer/Morning Tones */}
            <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-amber-900/10 blur-[150px] rounded-full pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-indigo-900/10 blur-[150px] rounded-full pointer-events-none" />

            {/* Header */}
            <div className="flex items-center justify-between px-10 py-8 z-10 border-b border-white/5 bg-gradient-to-r from-white/[0.02] to-transparent">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20">
                        <Sun className="text-amber-400" size={24} />
                    </div>
                    <div className="flex flex-col">
                        <h2 className="text-3xl font-black tracking-tighter text-white drop-shadow-lg">Daily Briefing</h2>
                        <span className="text-xs font-bold text-gray-500 tracking-[0.2em] uppercase">Lifestyle Intelligence</span>
                    </div>
                </div>
                <button
                    onClick={onClose}
                    className="p-3 rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-all border border-transparent hover:border-white/10"
                >
                    <X size={24} />
                </button>
            </div>

            {/* Content Grid */}
            <div className="flex-1 overflow-y-auto p-10 custom-scrollbar z-10">
                <div className="grid grid-cols-12 gap-8 max-w-7xl mx-auto">

                    {/* LEFT COLUMN: Market Pulse (Commodities & Indices) */}
                    <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
                        <div className="bg-white/[0.02] border border-white/5 p-6 rounded-3xl relative overflow-hidden group hover:border-white/10 transition-colors">
                            <div className="flex items-center gap-2 mb-6">
                                <Globe size={16} className="text-cyan-400" />
                                <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest">Global Markets</h3>
                            </div>
                            <div className="flex flex-col gap-4">
                                {marketPulse?.commodities?.map((c, i) => (
                                    <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-black/40 border border-white/5 hover:bg-white/5 transition-colors">
                                        <div className="flex flex-col">
                                            <span className="text-sm font-bold text-gray-200">{c.name}</span>
                                            <span className="text-[10px] text-gray-500 font-mono">{c.symbol}</span>
                                        </div>
                                        <div className={`text-sm font-bold font-mono ${c.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                            {c.change > 0 ? '+' : ''}{c.change}%
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* CENTER COLUMN: News Feed (Main Focus) */}
                    <div className="col-span-12 lg:col-span-6 flex flex-col gap-6">
                        <div className="flex items-center gap-2 mb-2 px-2">
                            <Newspaper size={16} className="text-emerald-400" />
                            <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest">Top Stories</h3>
                        </div>

                        <div className="flex flex-col gap-4">
                            {marketPulse?.news?.map((news, i) => (
                                <div
                                    key={i}
                                    onClick={() => news.link && window.open(news.link, '_blank')}
                                    className="bg-white/[0.02] border border-white/5 p-6 rounded-3xl hover:bg-white/[0.04] hover:border-emerald-500/30 hover:shadow-[0_0_30px_rgba(16,185,129,0.05)] transition-all cursor-pointer group"
                                >
                                    <div className="flex justify-between items-start gap-4">
                                        <h4 className="text-lg font-bold text-gray-200 leading-snug group-hover:text-white transition-colors">
                                            {news.title}
                                        </h4>
                                        <ArrowUpRight size={20} className="text-gray-600 group-hover:text-emerald-400 opacity-0 group-hover:opacity-100 transition-all -translate-y-2 group-hover:translate-y-0" />
                                    </div>
                                    <div className="flex items-center gap-3 mt-4">
                                        <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest bg-emerald-500/10 px-2 py-1 rounded">
                                            {news.publisher || 'NEWS'}
                                        </span>
                                        <span className="text-[10px] font-mono text-gray-500">
                                            {formatDate(news.time)}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* RIGHT COLUMN: Sports Ticker & Extras */}
                    <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
                        <div className="bg-white/[0.02] border border-white/5 p-6 rounded-3xl relative overflow-hidden h-full">
                            <div className="flex items-center gap-2 mb-6">
                                <Trophy size={16} className="text-amber-400" />
                                <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest">Live Sports</h3>
                            </div>
                            <div className="flex flex-col gap-3">
                                {marketPulse?.sports?.length > 0 ? (
                                    marketPulse.sports.map((s, i) => (
                                        <div
                                            key={i}
                                            onClick={() => window.open(`https://www.google.com/search?q=${s.title}`, '_blank')}
                                            className="p-4 rounded-2xl bg-gradient-to-br from-amber-500/5 to-transparent border border-amber-500/10 hover:border-amber-500/40 hover:from-amber-500/10 transition-all cursor-pointer group"
                                        >
                                            <p className="text-xs font-bold text-gray-300 leading-6 group-hover:text-white transition-colors">
                                                {s.title}
                                            </p>
                                            <div className="flex justify-end mt-2">
                                                <span className="text-[9px] font-black text-amber-500/80 uppercase tracking-widest animate-pulse">LIVE UPDATE</span>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-center py-10 text-gray-600 text-xs italic">
                                        No live matches currently.
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};

// Helper Icon for card link
const ArrowUpRight = ({ size, className }) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
    >
        <path d="M7 17l9.2-9.2M17 17V7H7" />
    </svg>
);

export default LifestyleWindow;
