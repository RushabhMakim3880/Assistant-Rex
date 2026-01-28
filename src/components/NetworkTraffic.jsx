import React from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';

const NetworkTraffic = ({ history = [] }) => {
    // Get last 30 data points for upload/download
    const uploadData = history.slice(-30).map(h => h?.upload || 0);
    const downloadData = history.slice(-30).map(h => h?.download || 0);

    // Current rates (last value)
    const currentUpload = uploadData[uploadData.length - 1] || 0;
    const currentDownload = downloadData[downloadData.length - 1] || 0;

    // Generate SVG path for compact line chart
    const generatePath = (data, maxVal) => {
        if (data.length < 2) return "M0,40 L300,40";

        const max = maxVal || Math.max(...data, 1);
        const width = 300;
        const height = 40;
        const stepX = width / (data.length - 1);

        return data.map((val, i) => {
            const x = i * stepX;
            const y = height - ((val / max) * height);
            return `${i === 0 ? 'M' : 'L'}${x},${y}`;
        }).join(' ');
    };

    const maxUpload = Math.max(...uploadData, 1);
    const maxDownload = Math.max(...downloadData, 1);

    return (
        <div className="bg-black/40 backdrop-blur-md border border-cyan-500/30 rounded-lg p-3 pointer-events-auto">
            {/* Upload Section */}
            <div className="mb-3">
                <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1 text-[9px] text-cyan-600 uppercase tracking-wider">
                        <ArrowUp size={10} />
                        <span>Upload</span>
                    </div>
                    <div className="text-cyan-300 text-[10px] font-mono font-bold">
                        {currentUpload.toFixed(2)} KB/s
                    </div>
                </div>
                <svg width="100%" height="40" className="overflow-visible">
                    <path
                        d={generatePath(uploadData, maxUpload)}
                        fill="none"
                        stroke="rgba(34, 211, 238, 0.7)"
                        strokeWidth="1.5"
                    />
                </svg>
            </div>

            {/* Download Section */}
            <div>
                <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1 text-[9px] text-cyan-600 uppercase tracking-wider">
                        <ArrowDown size={10} />
                        <span>Download</span>
                    </div>
                    <div className="text-cyan-300 text-[10px] font-mono font-bold">
                        {currentDownload.toFixed(2)} KB/s
                    </div>
                </div>
                <svg width="100%" height="40" className="overflow-visible">
                    <path
                        d={generatePath(downloadData, maxDownload)}
                        fill="none"
                        stroke="rgba(34, 211, 238, 0.7)"
                        strokeWidth="1.5"
                    />
                </svg>
            </div>
        </div>
    );
};

export default NetworkTraffic;
