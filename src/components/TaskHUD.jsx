import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Circle, Clock, AlertCircle } from 'lucide-react';

const TaskHUD = ({ tasks = [], onCompleteTask }) => {
    // Sort tasks: high priority first, then pending first
    const sortedTasks = [...tasks].sort((a, b) => {
        const priorityScore = { high: 3, medium: 2, low: 1 };
        if (a.status !== b.status) return a.status === 'pending' ? -1 : 1;
        return priorityScore[b.priority] - priorityScore[a.priority];
    });

    const pendingTasks = sortedTasks.filter(t => t.status === 'pending');

    return (
        <div className="w-full h-full flex flex-col gap-4 p-4 font-mono">
            {/* Header */}
            <div className="flex justify-between items-center border-b border-cyan-500/30 pb-2">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                    <span className="text-cyan-400 font-bold tracking-widest text-sm uppercase">Active Objectives</span>
                </div>
                <span className="text-cyan-600 text-[10px]">{pendingTasks.length} PENDING</span>
            </div>

            {/* Task List */}
            <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-2 pr-2">
                <AnimatePresence mode="popLayout">
                    {pendingTasks.length > 0 ? (
                        pendingTasks.map((task) => (
                            <motion.div
                                key={task.id}
                                layout
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 20 }}
                                className={`group relative p-3 border border-cyan-500/20 bg-cyan-950/20 hover:bg-cyan-900/30 transition-all rounded-sm flex gap-3 items-start overflow-hidden`}
                            >
                                {/* Priority Indicator */}
                                <div className={`absolute top-0 left-0 w-1 h-full ${task.priority === 'high' ? 'bg-red-500/60' :
                                        task.priority === 'medium' ? 'bg-yellow-500/60' : 'bg-green-500/60'
                                    }`} />

                                <button
                                    onClick={() => onCompleteTask?.(task.id)}
                                    className="mt-0.5 text-cyan-700 hover:text-cyan-400 transition-colors"
                                >
                                    <Circle className="w-5 h-5" />
                                </button>

                                <div className="flex flex-col gap-1 flex-1">
                                    <span className="text-xs font-bold text-cyan-100/90 leading-tight">
                                        {task.title}
                                    </span>
                                    {task.description && (
                                        <span className="text-[10px] text-cyan-400/60 italic leading-tight line-clamp-2">
                                            {task.description}
                                        </span>
                                    )}
                                    <div className="flex items-center gap-3 mt-1">
                                        <div className="flex items-center gap-1">
                                            <Clock className="w-3 h-3 text-cyan-800" />
                                            <span className="text-[9px] text-cyan-800">
                                                {new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <AlertCircle className="w-3 h-3 text-cyan-800" />
                                            <span className="text-[9px] text-cyan-800 uppercase">
                                                {task.priority}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        ))
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full opacity-30 gap-2">
                            <CheckCircle2 className="w-8 h-8 text-cyan-400" />
                            <span className="text-[10px] text-cyan-400 tracking-tighter uppercase font-bold">All Objectives Secured</span>
                        </div>
                    )}
                </AnimatePresence>
            </div>

            {/* Footer Stats */}
            <div className="bg-cyan-400/5 p-2 rounded flex justify-around items-center border border-cyan-400/10">
                <div className="flex flex-col items-center">
                    <span className="text-cyan-500/50 text-[8px] uppercase tracking-widest font-bold">Accuracy</span>
                    <span className="text-cyan-200 text-xs font-mono">100%</span>
                </div>
                <div className="h-4 w-px bg-cyan-500/20" />
                <div className="flex flex-col items-center">
                    <span className="text-cyan-500/50 text-[8px] uppercase tracking-widest font-bold">Efficiency</span>
                    <span className="text-cyan-200 text-xs font-mono">OPTIMAL</span>
                </div>
            </div>
        </div>
    );
};

export default TaskHUD;
