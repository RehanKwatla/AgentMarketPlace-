import React, { useState } from 'react';
import { LedgerRecord } from '../../types';
import { Clock } from 'lucide-react';

interface CallsOverTimeChartProps {
  records: LedgerRecord[];
}

export const CallsOverTimeChart: React.FC<CallsOverTimeChartProps> = ({ records }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (records.length === 0) {
    return (
      <div className="wallet-card rounded-xl p-5 border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm flex flex-col justify-between h-[280px]">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-xs font-semibold text-[#241B19] font-sans">Recorded Calls Over Time</h3>
            <p className="text-[11px] text-[#82786F] font-mono">Execution calls committed to audit ledger</p>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#DED8CD]/60 text-[#82786F] border border-[#CFC7BB]">
            0 calls
          </span>
        </div>

        <div className="flex flex-col items-center justify-center text-center my-auto space-y-2">
          <div className="w-9 h-9 rounded-lg bg-[#DED8CD]/60 border border-[#CFC7BB] flex items-center justify-center text-[#82786F]">
            <Clock className="w-4 h-4" />
          </div>
          <p className="text-xs font-medium text-[#241B19]">No recorded execution calls</p>
          <p className="text-[11px] text-[#82786F] max-w-xs font-mono">
            Execute a buyer task to visualize live throughput and latency telemetry over time.
          </p>
        </div>

        <div className="text-[10px] font-mono text-[#82786F] border-t border-[#CFC7BB]/60 pt-2 flex justify-between">
          <span>Source: /api/v1/ledger</span>
          <span>Time range: Live</span>
        </div>
      </div>
    );
  }

  // Aggregate records by bucket (e.g. index or timestamp)
  const buckets = records.slice(0, 12).map((rec, idx) => ({
    label: rec.timestamp ? new Date(rec.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : `#${idx + 1}`,
    latency: rec.latency_ms || 100,
    service: rec.service_id,
    requestId: rec.request_id,
    status: rec.status,
  }));

  const maxLatency = Math.max(...buckets.map(b => b.latency), 500);

  return (
    <div className="wallet-card rounded-xl p-5 border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm flex flex-col justify-between h-[280px] font-sans">
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <h3 className="text-xs font-semibold text-[#241B19]">Recorded Calls & Latency</h3>
          <p className="text-[11px] text-[#82786F] font-mono">Response time per recorded microservice invocation</p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB]">
          {records.length} {records.length === 1 ? 'call' : 'calls'}
        </span>
      </div>

      {/* SVG Responsive Bar Visualization */}
      <div className="relative my-auto pt-4 pb-2">
        <svg className="w-full h-36 overflow-visible" viewBox={`0 0 ${buckets.length * 50 + 20} 120`} preserveAspectRatio="none">
          <line x1="0" y1="110" x2={buckets.length * 50 + 20} y2="110" stroke="#CFC7BB" strokeWidth="1" />
          <line x1="0" y1="55" x2={buckets.length * 50 + 20} y2="55" stroke="#CFC7BB" strokeDasharray="3 3" opacity="0.6" />
          
          {buckets.map((b, idx) => {
            const barHeight = Math.max(12, (b.latency / maxLatency) * 90);
            const x = idx * 50 + 15;
            const y = 110 - barHeight;
            const isHovered = hoveredIdx === idx;

            return (
              <g 
                key={idx} 
                className="cursor-pointer transition-all"
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
              >
                <rect
                  x={x}
                  y={y}
                  width="24"
                  height={barHeight}
                  rx="3"
                  className={`${
                    isHovered 
                      ? 'fill-[#7D292D]' 
                      : b.status === 'paid' 
                      ? 'fill-[#A8B3A1] hover:fill-[#7D292D]' 
                      : 'fill-[#DED8CD] hover:fill-[#A86E24]'
                  } transition-colors`}
                />
                <text
                  x={x + 12}
                  y="122"
                  textAnchor="middle"
                  className="fill-[#82786F] text-[9px] font-mono"
                >
                  {b.label}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Floating Tooltip */}
        {hoveredIdx !== null && buckets[hoveredIdx] && (
          <div className="absolute top-0 right-4 bg-[#FFFFFF] border border-[#CFC7BB] p-2.5 rounded-lg shadow-lg text-[10px] font-mono z-20 space-y-0.5">
            <span className="text-[#241B19] font-bold block">{buckets[hoveredIdx].service}</span>
            <span className="text-[#7D292D] font-semibold">Latency: {buckets[hoveredIdx].latency} ms</span>
            <span className="text-[#82786F] block truncate max-w-[140px]">{buckets[hoveredIdx].requestId}</span>
          </div>
        )}
      </div>

      <div className="text-[10px] font-mono text-[#82786F] border-t border-[#CFC7BB]/60 pt-2 flex justify-between items-center">
        <span>Scale: 0 – {maxLatency} ms</span>
        <span className="text-[#38865B] font-medium">Sage: Settled (Paid)</span>
      </div>
    </div>
  );
};
export default CallsOverTimeChart;
