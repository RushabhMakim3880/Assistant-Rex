
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { GoogleGenAI, LiveServerMessage, Modality, Chat } from '@google/genai';
import { LogType, NeuralLogItem, SystemStats } from './types';
import { encodeAudio, decodeAudio, decodeAudioData } from './services/audioUtils';

// --- Sub-components ---

const Header: React.FC<{ stats: SystemStats }> = ({ stats }) => (
  <header class="flex justify-between items-start z-20">
    <div class="flex items-center gap-4">
      <div class="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
        <span class="material-symbols-outlined text-2xl">bubble_chart</span>
      </div>
      <div>
        <h1 class="font-display font-medium tracking-tight text-xl text-white">
          R.E.X. <span class="ml-2 text-[10px] font-mono px-2 py-0.5 bg-blue-500/10 text-blue-400 rounded-full border border-blue-500/20 uppercase tracking-widest">Organic Core</span>
        </h1>
        <p class="text-[10px] font-mono text-slate-500 mt-0.5 tracking-[0.2em] uppercase">Status: Neural Fluidic State Optimal</p>
      </div>
    </div>
    <div class="flex items-center gap-8 font-mono text-[11px] text-slate-400">
      <div class="flex items-center gap-3 bg-white/5 px-4 py-2 rounded-full border border-white/5">
        <span class="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
        <span>ACTIVE NODE: O-CORE_PRIMARY</span>
      </div>
      <div class="flex items-center gap-6 border-l border-white/10 pl-8">
        <div class="text-right">
          <div class="text-white font-medium">{stats.time}</div>
          <div class="text-[9px] text-slate-500 uppercase">System Time</div>
        </div>
        <div class="flex gap-2">
          <button class="w-8 h-8 flex items-center justify-center hover:bg-white/5 rounded-full transition-colors"><span class="material-symbols-outlined text-lg">minimize</span></button>
          <button class="w-8 h-8 flex items-center justify-center hover:bg-white/5 rounded-full transition-colors"><span class="material-symbols-outlined text-lg">close</span></button>
        </div>
      </div>
    </div>
  </header>
);

const OrganicCore: React.FC<{ stats: SystemStats }> = ({ stats }) => {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 20;
      const y = (e.clientY / window.innerHeight - 0.5) * 20;
      setMousePos({ x, y });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div class="flex-1 flex items-center justify-center relative">
      <div class="relative flex flex-col items-center">
        <div 
          className="organic-blob opacity-80"
          style={{ transform: `translate(${mousePos.x}px, ${mousePos.y}px)` }}
        ></div>
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="w-32 h-32 rounded-full border border-white/10 flex items-center justify-center backdrop-blur-sm">
            <span class="font-display text-sm font-light tracking-[0.4em] text-white">REX</span>
          </div>
        </div>
        <div class="mt-20 text-center">
          <div class="font-mono text-[11px] tracking-[0.3em] text-blue-400/80 mb-3 uppercase">
            Pulse synchronization active<span class="animate-pulse">_</span>
          </div>
          <div class="flex gap-8 justify-center text-[10px] text-slate-500 font-mono">
            <span class="flex items-center gap-2"><span class="w-1 h-1 rounded-full bg-blue-500/40"></span>FLOW: {stats.flow}</span>
            <span class="flex items-center gap-2"><span class="w-1 h-1 rounded-full bg-blue-500/40"></span>TEMP: {stats.temp}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

const NeuralLog: React.FC<{ logs: NeuralLogItem[], onSendMessage: (msg: string) => void }> = ({ logs, onSendMessage }) => {
  const [inputValue, setInputValue] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onSendMessage(inputValue);
      setInputValue('');
    }
  };

  return (
    <aside class="fixed right-8 top-32 bottom-40 w-72 glass-panel rounded-3xl p-6 flex flex-col z-20">
      <div class="flex items-center justify-between mb-6">
        <span class="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Neural Log</span>
        <span class="material-symbols-outlined text-blue-400 text-sm">waves</span>
      </div>
      <div ref={scrollRef} class="flex-1 overflow-y-auto custom-scrollbar space-y-6 font-mono text-[11px] leading-relaxed">
        {logs.map((log) => (
          <div key={log.id} class="space-y-1">
            <div class="flex items-center gap-2 opacity-50">
              <span class="text-blue-400">{(log.id + 1).toString().padStart(2, '0')}</span>
              <span>[{log.type}]</span>
            </div>
            <div className={`p-3 rounded-2xl border ${log.isAi ? 'text-blue-300 bg-blue-500/5 border-blue-500/10 italic' : 'text-slate-200 border-white/5 bg-white/5'}`}>
              {log.message}
            </div>
          </div>
        ))}
      </div>
      <form onSubmit={handleSubmit} class="mt-6">
        <div class="relative group">
          <input 
            class="w-full bg-white/5 border border-white/5 text-[11px] font-mono rounded-2xl py-3 pl-4 pr-10 focus:ring-1 focus:ring-blue-500/40 focus:border-blue-500/40 placeholder-slate-600 text-blue-100 transition-all outline-none" 
            placeholder="Speak to the core..." 
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
          />
          <button type="submit" class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-lg text-blue-400/40 group-focus-within:text-blue-400 transition-colors">
            keyboard_command_key
          </button>
        </div>
      </form>
    </aside>
  );
};

const ControlDrawer: React.FC<{ isOpen: boolean }> = ({ isOpen }) => (
  <div className={`control-drawer absolute bottom-24 left-1/2 -translate-x-1/2 w-[600px] glass-panel rounded-3xl p-6 pb-8 border border-white/10 transition-all duration-500 ${isOpen ? 'opacity-100 translate-y-0 pointer-events-auto' : 'opacity-0 translate-y-full pointer-events-none'}`}>
    <div class="flex justify-between items-center mb-6 px-4">
      <h3 class="font-mono text-[10px] text-blue-400/80 uppercase tracking-widest">System Control Suite</h3>
      <div class="h-px flex-1 mx-6 bg-gradient-to-r from-blue-400/20 to-transparent"></div>
    </div>
    <div class="grid grid-cols-4 gap-6 px-4">
      {[
        { icon: 'wifi_tethering', label: 'Link State', val: 'STABLE' },
        { icon: 'settings_input_component', label: 'Audio Matrix', val: 'NEURAL_IO' },
        { icon: 'palette', label: 'Interface', val: 'CYBER_DRK' },
        { icon: 'tune', label: 'AI Params', val: 'v4.2.0' },
      ].map((item, i) => (
        <div key={i} class="flex flex-col items-center gap-3 group cursor-pointer">
          <div class="w-14 h-14 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-center group-hover:bg-blue-500/10 group-hover:border-blue-500/20 transition-all duration-300">
            <span class="material-symbols-outlined neon-icon text-2xl">{item.icon}</span>
          </div>
          <span class="font-mono text-[9px] text-slate-400 uppercase tracking-wider text-center leading-tight">
            {item.label}<br/><span class="text-blue-400/60 font-medium">{item.val}</span>
          </span>
        </div>
      ))}
    </div>
  </div>
);

// --- Main App Component ---

export default function App() {
  const [logs, setLogs] = useState<NeuralLogItem[]>([
    { id: 0, type: LogType.SYSTEM, message: "Fluidic environment stabilized at 98.4% cohesion.", timestamp: "14:42:00", isAi: true },
    { id: 1, type: LogType.NEURAL, message: "The organic core feels... more responsive today. Shall we explore the datasets?", timestamp: "14:42:05", isAi: true }
  ]);
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [showControls, setShowControls] = useState(false);
  const [stats, setStats] = useState<SystemStats>({
    flow: '1.2GB/s',
    temp: '32°C',
    cohesion: '98.4%',
    time: '00:00:00'
  });

  const ai = useRef(new GoogleGenAI({ apiKey: process.env.API_KEY }));
  const chatRef = useRef<Chat | null>(null);
  
  // Audio state
  const audioCtxRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef(0);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());

  // Update System Time
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      setStats(prev => ({
        ...prev,
        time: now.toLocaleTimeString('en-US', { hour12: false })
      }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const addLog = useCallback((type: LogType, message: string, isAi: boolean = false) => {
    setLogs(prev => [...prev, {
      id: prev.length,
      type,
      message,
      timestamp: new Date().toLocaleTimeString(),
      isAi
    }]);
  }, []);

  // Handle Text Chat
  const handleSendMessage = async (msg: string) => {
    addLog(LogType.USER, msg, false);
    
    if (!chatRef.current) {
      chatRef.current = ai.current.chats.create({
        model: 'gemini-3-flash-preview',
        config: {
          systemInstruction: 'You are R.E.X., an advanced organic AI core. Your tone is futuristic, analytical, yet subtly poetic and "fluidic". Keep responses concise for the neural log.'
        }
      });
    }

    try {
      const result = await chatRef.current.sendMessage({ message: msg });
      addLog(LogType.NEURAL, result.text || "...", true);
    } catch (err) {
      addLog(LogType.ERROR, "Link failure detected. Retrying...", true);
    }
  };

  // Handle Voice Mode (Live API)
  const toggleVoiceMode = async () => {
    if (isVoiceActive) {
      setIsVoiceActive(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const inputAudioContext = new AudioContext({ sampleRate: 16000 });
      const outputAudioContext = new AudioContext({ sampleRate: 24000 });
      audioCtxRef.current = outputAudioContext;

      const sessionPromise = ai.current.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        callbacks: {
          onopen: () => {
            setIsVoiceActive(true);
            addLog(LogType.SYSTEM, "Neural link established. Voice mode active.", true);
            
            const source = inputAudioContext.createMediaStreamSource(stream);
            const scriptProcessor = inputAudioContext.createScriptProcessor(4096, 1, 1);
            
            scriptProcessor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              const l = inputData.length;
              const int16 = new Int16Array(l);
              for (let i = 0; i < l; i++) int16[i] = inputData[i] * 32768;
              
              const pcmBlob = {
                data: encodeAudio(new Uint8Array(int16.buffer)),
                mimeType: 'audio/pcm;rate=16000',
              };

              sessionPromise.then((session) => {
                session.sendRealtimeInput({ media: pcmBlob });
              });
            };
            
            source.connect(scriptProcessor);
            scriptProcessor.connect(inputAudioContext.destination);
          },
          onmessage: async (message: LiveServerMessage) => {
            const audioData = message.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (audioData) {
              const outputCtx = outputAudioContext;
              nextStartTimeRef.current = Math.max(nextStartTimeRef.current, outputCtx.currentTime);
              
              const buffer = await decodeAudioData(decodeAudio(audioData), outputCtx, 24000, 1);
              const source = outputCtx.createBufferSource();
              source.buffer = buffer;
              source.connect(outputCtx.destination);
              source.start(nextStartTimeRef.current);
              nextStartTimeRef.current += buffer.duration;
              sourcesRef.current.add(source);
            }
          },
          onerror: () => setIsVoiceActive(false),
          onclose: () => setIsVoiceActive(false),
        },
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Zephyr' } } },
          systemInstruction: "You are R.E.X. Speak in a calm, analytical, and fluidic manner."
        },
      });
    } catch (err) {
      console.error(err);
      addLog(LogType.ERROR, "Microphone access denied.", true);
    }
  };

  return (
    <div class="h-screen mesh-gradient selection:bg-blue-500/30">
      <main class="relative h-full w-full flex flex-col p-8">
        <Header stats={stats} />
        
        <OrganicCore stats={stats} />
        
        <NeuralLog logs={logs} onSendMessage={handleSendMessage} />

        <div 
          class="footer-container fixed bottom-0 left-0 right-0 z-50"
          onMouseEnter={() => setShowControls(true)}
          onMouseLeave={() => setShowControls(false)}
        >
          <ControlDrawer isOpen={showControls} />
          
          <footer class="glass-footer h-24 flex items-center px-12 relative z-10">
            <div class="max-w-7xl mx-auto w-full flex justify-between items-center">
              <div class="flex items-center gap-2">
                <button class="w-12 h-12 rounded-2xl bg-blue-500/10 text-blue-400 flex items-center justify-center hover:bg-blue-500/20 transition-all">
                  <span class="material-symbols-outlined">power_settings_new</span>
                </button>
                <button class="w-12 h-12 rounded-2xl text-slate-500 flex items-center justify-center hover:text-white hover:bg-white/5 transition-all">
                  <span class="material-symbols-outlined">settings_suggest</span>
                </button>
              </div>

              <div class="flex items-center gap-1 bg-white/5 p-1.5 rounded-3xl border border-white/5">
                <button 
                  onClick={toggleVoiceMode}
                  className={`px-6 h-11 rounded-2xl flex items-center gap-2 text-[11px] font-mono uppercase tracking-widest transition-all ${isVoiceActive ? 'bg-blue-500 text-white shadow-[0_0_15px_rgba(79,168,255,0.4)]' : 'bg-blue-500/10 text-blue-400 hover:bg-blue-500/20'}`}
                >
                  <span className={`material-symbols-outlined text-lg ${isVoiceActive ? 'animate-pulse' : ''}`}>mic</span>
                  {isVoiceActive ? 'Voice Active' : 'Voice Mode'}
                </button>
                <div class="w-px h-6 bg-white/10 mx-2"></div>
                <div class="flex gap-1">
                  <button class="w-11 h-11 rounded-2xl text-slate-500 flex items-center justify-center hover:text-blue-400 transition-all"><span class="material-symbols-outlined">visibility</span></button>
                  <button class="w-11 h-11 rounded-2xl text-slate-500 flex items-center justify-center hover:text-blue-400 transition-all"><span class="material-symbols-outlined">auto_graph</span></button>
                  <button class="w-11 h-11 rounded-2xl text-slate-500 flex items-center justify-center hover:text-blue-400 transition-all"><span class="material-symbols-outlined">layers</span></button>
                </div>
              </div>

              <div class="flex items-center gap-6">
                <div class="flex flex-col items-end gap-1">
                  <span class="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Core Health</span>
                  <div class="w-24 h-1 bg-white/10 rounded-full overflow-hidden">
                    <div class="w-4/5 h-full bg-blue-400/60 shadow-[0_0_8px_rgba(79,168,255,0.5)]"></div>
                  </div>
                </div>
                <button class="w-12 h-12 rounded-2xl border border-white/10 text-slate-400 flex items-center justify-center hover:border-blue-500/30 hover:text-blue-400 transition-all">
                  <span class="material-symbols-outlined">grid_view</span>
                </button>
              </div>
            </div>
          </footer>
        </div>

        <div class="fixed bottom-28 left-8 z-20 font-mono text-[9px] uppercase tracking-[0.3em] text-slate-600">
          Organic Interface Protocol Alpha-1
        </div>
        <div class="fixed bottom-28 right-8 z-20 font-mono text-[9px] uppercase tracking-[0.3em] text-slate-600">
          Syncing: Neural Network 0x3F2
        </div>
      </main>
    </div>
  );
}
