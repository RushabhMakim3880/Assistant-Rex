import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Laptop, Loader, CheckCircle, AlertTriangle } from 'lucide-react';
import axios from 'axios';

const DragDropZone = ({ onUploadSuccess }) => {
    const [uploadStatus, setUploadStatus] = useState('idle'); // idle, uploading, success, error
    const [message, setMessage] = useState('');

    const onDrop = useCallback(async (acceptedFiles) => {
        if (acceptedFiles.length === 0) return;

        const file = acceptedFiles[0];
        setUploadStatus('uploading');
        setMessage(`Scanning ${file.name}...`);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post('http://127.0.0.1:8000/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            if (response.data.status === 'success') {
                setUploadStatus('success');
                setMessage('Analysis Complete. Context Injected.');
                if (onUploadSuccess) onUploadSuccess(response.data);

                // Reset after delay
                setTimeout(() => {
                    setUploadStatus('idle');
                    setMessage('');
                }, 3000);
            } else {
                setUploadStatus('error');
                setMessage(`Error: ${response.data.message}`);
            }
        } catch (error) {
            console.error("Upload failed", error);
            setUploadStatus('error');
            setMessage('Upload Failed. Check backend connection.');
        }
    }, [onUploadSuccess]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        noClick: true, // Don't open file dialog on click, only drag
        noKeyboard: true
    });

    if (!isDragActive && uploadStatus === 'idle') return null;

    return (
        <div {...getRootProps()} className="fixed inset-0 z-[100] pointer-events-none">
            <input {...getInputProps()} />

            {/* Holographic Overlay when Dragging */}
            {isDragActive && (
                <div className="absolute inset-0 bg-cyan-500/10 backdrop-blur-sm border-4 border-dashed border-cyan-500/50 flex items-center justify-center animate-pulse pointer-events-auto">
                    <div className="bg-black/90 p-8 rounded-3xl border border-cyan-500/30 flex flex-col items-center gap-4 shadow-[0_0_50px_rgba(6,182,212,0.2)]">
                        <div className="text-cyan-400">
                            <Laptop size={64} strokeWidth={1.5} />
                        </div>
                        <div className="text-xl font-bold tracking-[0.3em] text-cyan-400 uppercase">Drop into Context</div>
                        <div className="text-[10px] text-cyan-500/50 font-mono tracking-widest uppercase">Visual Cortex Analysis</div>
                    </div>
                </div>
            )}

            {/* Status Overlay (Uploading / Success / Error) */}
            {!isDragActive && uploadStatus !== 'idle' && (
                <div className="absolute top-20 left-1/2 -translate-x-1/2 z-[101] pointer-events-auto">
                    <div className={`
                        flex items-center gap-4 px-6 py-4 rounded-xl border backdrop-blur-md shadow-2xl transition-all
                        ${uploadStatus === 'uploading' ? 'bg-black/80 border-cyan-500/30 text-cyan-400' : ''}
                        ${uploadStatus === 'success' ? 'bg-green-900/80 border-green-500/30 text-green-400' : ''}
                        ${uploadStatus === 'error' ? 'bg-red-900/80 border-red-500/30 text-red-400' : ''}
                    `}>
                        {uploadStatus === 'uploading' && <Loader className="animate-spin" />}
                        {uploadStatus === 'success' && <CheckCircle />}
                        {uploadStatus === 'error' && <AlertTriangle />}

                        <div className="flex flex-col">
                            <span className="font-bold uppercase tracking-wider text-xs">{uploadStatus}</span>
                            <span className="text-sm font-mono">{message}</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DragDropZone;
