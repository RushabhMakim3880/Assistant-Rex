import React, { useMemo } from 'react';
import { X, TrendingUp, TrendingDown, Activity, DollarSign, AlertTriangle, RefreshCw, BarChart3, Globe, Shield, Target, Plus, Zap, Info, Download, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, PieChart, Pie, Cell } from 'recharts';

const StockWindow = ({ data, onClose, isLoading }) => {
    const [timeframe, setTimeframe] = React.useState('1M');

    if (isLoading || data?.loading) {
        return (
            <div className="flex flex-col h-full bg-[#0a0a0b] backdrop-blur-3xl border border-white/10 rounded-[2rem] overflow-hidden shadow-2xl relative items-center justify-center">
                <div className="relative">
                    <div className="absolute inset-0 bg-cyan-500/20 blur-[100px] rounded-full animate-pulse" />
                    <RefreshCw className="text-cyan-400 animate-spin relative z-10" size={64} />
                </div>
                <span className="text-cyan-400 font-mono tracking-[0.3em] mt-8 animate-pulse uppercase text-xs">Proprietary AI Analysis in Progress...</span>
                <button
                    onClick={onClose}
                    className="absolute top-8 right-8 p-3 rounded-2xl hover:bg-white/5 text-gray-500 hover:text-white transition-all group border border-transparent hover:border-white/10"
                >
                    <X size={24} className="group-hover:rotate-90 transition-transform" />
                </button>
            </div>
        );
    }

    const isBullish = data.prediction?.trend === 'Bullish';
    const accentColor = isBullish ? '#10b981' : '#ef4444';

    const formatCurrency = (val, decimals = 2) => {
        if (!val && val !== 0) return 'N/A';
        return `₹${val.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
    };

    const formatLargeNumber = (num) => {
        if (!num) return 'N/A';
        if (num > 1000000000000) return (num / 1000000000000).toFixed(2) + 'T';
        if (num > 10000000) return (num / 10000000).toFixed(2) + 'Cr';
        return num.toLocaleString('en-IN');
    };

    // Sentiment Gauge Data
    const sentimentValue = data.sentiment?.score || 50;
    const gaugeData = [
        { value: sentimentValue },
        { value: 100 - sentimentValue }
    ];

    // Combine Historical and Projection for the main chart
    const combinedChartData = useMemo(() => {
        if (!data.history) return [];

        // 1. Merge History and Projections by Date
        const merged = new Map();

        // Add History
        data.history.forEach(h => {
            merged.set(h.date, { ...h, type: 'actual' });
        });

        // Add Projections (Enhanced)
        if (data.performance_tracking) {
            data.performance_tracking.forEach(p => {
                if (merged.has(p.date)) {
                    // Merge projection into existing history point
                    const existing = merged.get(p.date);
                    merged.set(p.date, { ...existing, ...p }); // Contains range_max/min
                } else {
                    // Future date? (Unlikely with current backend logic but safe to handle)
                    merged.set(p.date, { ...p, type: 'projection', close: p.ai_projection });
                }
            });
        }

        let sortedData = Array.from(merged.values()).sort((a, b) => new Date(a.date) - new Date(b.date));

        // 2. Filter by Timeframe
        if (timeframe === '1M') {
            sortedData = sortedData.slice(-22);
        } else if (timeframe === '1Y') {
            sortedData = sortedData.slice(-252);
        }
        // 5Y is default (all data)

        return sortedData;
    }, [data.history, data.performance_tracking, timeframe]);

    return (
        <div className="flex flex-col h-full bg-[#050505] backdrop-blur-3xl border border-white/5 rounded-[2rem] overflow-hidden shadow-[0_0_120px_rgba(0,0,0,0.9)] relative font-sans text-white select-none">

            {/* Background Ambience */}
            <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-cyan-900/10 blur-[150px] rounded-full pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-emerald-900/5 blur-[150px] rounded-full pointer-events-none" />

            {/* 1. Ultra-Clean Header */}
            <div className="flex items-center justify-between px-12 py-8 bg-gradient-to-b from-white/[0.02] to-transparent">
                <div className="flex items-center gap-8">
                    <div className="flex flex-col">
                        <h2 className="text-5xl font-black tracking-tighter text-white drop-shadow-2xl">{data.name}</h2>
                        <div className="flex items-center gap-3 mt-1">
                            <span className="text-xl font-bold text-gray-500 font-mono tracking-widest uppercase">{data.symbol}</span>
                            <div className={`flex items-center gap-2 px-3 py-1 rounded-md text-sm font-black tracking-widest uppercase border shadow-[0_0_15px_rgba(0,0,0,0.5)] ${data.recommendation?.signal === 'BUY' ? 'bg-emerald-500 text-black border-emerald-400 shadow-emerald-500/20' : data.recommendation?.signal === 'SELL' ? 'bg-red-500 text-white border-red-400 shadow-red-500/20' : 'bg-amber-400 text-black border-amber-300 shadow-amber-500/20'}`}>
                                {data.recommendation?.signal || 'HOLD'} RATING
                            </div>
                        </div>
                    </div>

                    <div className="h-16 w-px bg-white/10 mx-4" />

                    <div className="flex flex-col">
                        <div className="text-6xl font-black tracking-tighter text-white tabular-nums drop-shadow-lg">
                            {formatCurrency(data.current_price).replace('₹', '')}<span className="text-2xl text-gray-400 align-top mt-2">.{(data.current_price % 1).toFixed(2).split('.')[1]}</span>
                        </div>
                        <div className={`flex items-center gap-2 text-lg font-bold tracking-tight ${data.change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {data.change >= 0 ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
                            {data.change > 0 ? '+' : ''}{data.change} ({data.change_pct}%)
                        </div>
                    </div>
                </div>

                <button
                    onClick={onClose}
                    className="p-4 rounded-full bg-white/5 hover:bg-white/10 hover:scale-110 transition-all text-gray-400 hover:text-white group border border-white/5"
                >
                    <X size={24} className="group-hover:rotate-90 transition-transform duration-500" />
                </button>
            </div>

            {/* 2. Key Metrics Strip */}
            <div className="grid grid-cols-4 gap-px bg-white/5 border-y border-white/5">
                {[
                    { label: '52 WEEK HIGH', value: formatCurrency(data.fundamentals?.fiftyTwoWeekHigh) },
                    { label: '52 WEEK LOW', value: formatCurrency(data.fundamentals?.fiftyTwoWeekLow) },
                    { label: 'MARKET CAP', value: formatLargeNumber(data.fundamentals?.market_cap) },
                    { label: 'P/E RATIO', value: data.fundamentals?.pe_ratio }
                ].map((stat, i) => (
                    <div key={i} className="bg-[#050505] p-6 hover:bg-white/[0.01] transition-colors group relative overflow-hidden">
                        <div className="relative z-10">
                            <span className="text-[9px] font-black text-gray-600 uppercase tracking-[0.2em] mb-2 block">{stat.label}</span>
                            <div className="text-2xl font-bold text-gray-200 tracking-tight group-hover:text-white transition-colors">{stat.value}</div>
                        </div>
                        <div className="absolute right-0 bottom-0 top-0 w-24 bg-gradient-to-l from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                ))}
            </div>

            {/* 3. Main Dashboard Grid */}
            <div className="flex-1 overflow-hidden grid grid-cols-12">

                {/* Left: Intelligence (3 Cols) */}
                <div className="col-span-3 bg-black/20 border-r border-white/5 p-8 flex flex-col gap-8 overflow-y-auto custom-scrollbar">

                    {/* Sentiment Gauge */}
                    <div className="flex flex-col items-center">
                        <div className="relative w-48 h-24 z-10">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={gaugeData}
                                        cx="50%" cy="100%"
                                        innerRadius={70}
                                        outerRadius={85}
                                        startAngle={180}
                                        endAngle={0}
                                        dataKey="value"
                                        stroke="none"
                                        cornerRadius={4}
                                        paddingAngle={2}
                                    >
                                        <Cell fill={sentimentValue > 60 ? "#10b981" : sentimentValue < 40 ? "#ef4444" : "#f59e0b"} />
                                        <Cell fill="#1a1a1c" />
                                    </Pie>
                                </PieChart>
                            </ResponsiveContainer>
                            <div className="absolute inset-x-0 bottom-0 flex flex-col items-center justify-end h-full">
                                <span className={`text-4xl font-black tracking-tighter ${sentimentValue > 60 ? "text-emerald-400" : sentimentValue < 40 ? "text-red-400" : "text-amber-400"}`}>{sentimentValue}</span>
                            </div>
                        </div>
                        <span className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] mt-4">Market Sentiment</span>
                    </div>

                    {/* Forecast List */}
                    <div className="flex flex-col gap-4">
                        <h3 className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em] pl-1">Short Term AI Models</h3>
                        <div className="flex flex-col gap-3">
                            {data.short_term_predictions?.map((p, i) => (
                                <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-all group">
                                    <div className="flex flex-col">
                                        <span className="text-[9px] font-bold text-gray-500 uppercase">{p.period}</span>
                                        <div className="flex items-center gap-1.5 mt-0.5">
                                            {p.direction === 'Increase' ? <ArrowUpRight size={14} className="text-emerald-400" /> : <ArrowDownRight size={14} className="text-red-400" />}
                                            <span className={`text-sm font-bold tracking-tight ${p.direction === 'Increase' ? 'text-emerald-400' : 'text-red-400'}`}>{formatCurrency(p.predicted)}</span>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-end">
                                        <div className="text-[8px] font-black text-gray-700 bg-white/5 px-1.5 py-0.5 rounded border border-white/5">{90 - (i * 3)}% CONF</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Center: Main Chart (6 Cols) */}
                <div className="col-span-6 p-8 flex flex-col relative">
                    <div className="flex items-center justify-between mb-6 z-10">
                        <div className="flex flex-col">
                            <h3 className="text-lg font-bold text-gray-200 tracking-tight">Price Action vs AI Corridor</h3>
                            <p className="text-xs text-gray-600 font-medium">Historical performance visualization</p>
                        </div>
                        <div className="flex p-0.5 rounded-lg bg-white/5 border border-white/5">
                            {['1M', '1Y', '5Y'].map(t => (
                                <button
                                    key={t}
                                    onClick={() => setTimeframe(t)}
                                    className={`px-4 py-1.5 rounded-md text-[10px] font-bold transition-all ${timeframe === t ? 'bg-white/10 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'}`}
                                >
                                    {t}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="w-full h-[400px] relative z-10 text-xs text-white">
                        {combinedChartData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={combinedChartData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                                    <defs>
                                        <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="#00d1b2" stopOpacity={0.2} />
                                            <stop offset="100%" stopColor="#00d1b2" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#6b7280', fontSize: 10, fontWeight: 500 }} minTickGap={50} tickFormatter={(d) => ''} />
                                    <YAxis hide domain={['auto', 'auto']} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#050505', borderColor: '#333', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}
                                        itemStyle={{ color: '#fff', fontSize: '12px', fontWeight: 'bold' }}
                                        labelStyle={{ color: '#9ca3af', fontSize: '10px', marginBottom: '4px' }}
                                    />
                                    <Area type="monotone" dataKey="range_max" stroke="none" fill="#00d1b2" fillOpacity={0.05} />
                                    <Area type="monotone" dataKey="close" stroke="#00d1b2" strokeWidth={2} fill="url(#chartFill)" activeDot={{ r: 4, stroke: '#00d1b2', strokeWidth: 2, fill: '#000' }} />
                                    <Area type="monotone" dataKey="range_min" stroke="none" fill="#000000" fillOpacity={0.6} />
                                </AreaChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full border border-white/5 rounded-2xl bg-white/[0.01]">
                                <div className="flex flex-col items-center gap-2">
                                    <Activity className="text-gray-700 animate-pulse" />
                                    <span className="text-[10px] font-mono text-gray-600 uppercase tracking-wider">Acquiring Market Data...</span>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Right: Live Feed (3 Cols) - CLEARED */}
                <div className="col-span-3 bg-black/20 border-l border-white/5 p-8 flex flex-col items-center justify-center text-center opacity-50">
                    <div className="p-4 rounded-full bg-white/5 mb-4">
                        <BarChart3 className="text-gray-600" size={32} />
                    </div>
                    <h3 className="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Stock Focus</h3>
                    <p className="text-[10px] text-gray-600 max-w-[150px]">
                        Global Pulse & News have moved to the Daily Briefing window.
                    </p>
                </div>

            </div>

            {/* Footer */}
            <div className="h-8 bg-[#020202] border-t border-white/5 flex items-center justify-between px-6">
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    <span className="text-[9px] font-bold text-gray-700 tracking-widest uppercase">REX QUANT ENGINE V2.0 ACTIVE</span>
                </div>
                <span className="text-[9px] font-mono text-gray-800">ENCRYPTED // SECURE</span>
            </div>
        </div>
    );
};

export default StockWindow;
