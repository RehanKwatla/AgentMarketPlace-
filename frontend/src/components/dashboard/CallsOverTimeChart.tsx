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
  const buckets = records.slice(0, 12).map((rec, idx) => {
    let timeLabel = `#${idx + 1}`;
    let fullTime = '';
    if (rec.timestamp) {
      try {
        const d = new Date(rec.timestamp);
        if (!isNaN(d.getTime())) {
          timeLabel = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
          fullTime = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
      } catch {
        timeLabel = `#${idx + 1}`;
      }
    }

    return {
      label: timeLabel,
      fullTime,
      latency: rec.latency_ms || 100,
      service: rec.service_id,
      requestId: rec.request_id,
      status: rec.status,
    };
  });

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

      {/* Responsive Bar Visualization */}
      <div className="relative my-auto flex-1 flex flex-col justify-end pt-3 pb-1">
        {/* Horizontal reference grid lines */}
        <div className="absolute inset-x-0 top-4 bottom-10 pointer-events-none flex flex-col justify-between">
          <div className="border-b border-[#CFC7BB]/50 border-dashed w-full relative">
            <span className="absolute -top-3 right-0 text-[9px] font-mono text-[#82786F]/80">
              {maxLatency} ms
            </span>
          </div>
          <div className="border-b border-[#CFC7BB]/30 border-dashed w-full relative">
            <span className="absolute -top-3 right-0 text-[9px] font-mono text-[#82786F]/60">
              {Math.round(maxLatency / 2)} ms
            </span>
          </div>
          <div className="border-b border-[#CFC7BB] w-full" />
        </div>

        {/* Bars Container */}
        <div className="relative z-10 flex items-end justify-around gap-1 sm:gap-2 px-1 sm:px-2 h-32">
          {buckets.map((b, idx) => {
            const heightPercent = Math.max(10, Math.min(100, (b.latency / maxLatency) * 100));
            const isHovered = hoveredIdx === idx;
            const isPaid = b.status === 'paid';
            const isRejected = b.status === 'paid output rejected';

            return (
              <div
                key={idx}
                className="flex-1 min-w-0 max-w-[64px] h-full flex flex-col justify-end items-center group relative cursor-pointer"
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
              >
                {/* Floating Tooltip */}
                {isHovered && (
                  <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-[#241B19] text-[#F7F4EE] px-3 py-2 rounded-lg shadow-xl text-[10px] font-mono z-30 whitespace-nowrap pointer-events-none border border-[#3E302C] min-w-[130px]">
                    <div className="font-bold text-[#E5D4C0]">{b.service}</div>
                    <div className="text-[11px] font-semibold text-[#A8B3A1] mt-0.5">
                      {b.latency} ms • <span className="capitalize">{b.status}</span>
                    </div>
                    {b.fullTime && (
                      <div className="text-[9px] text-[#CFC7BB]/70 mt-0.5">{b.fullTime}</div>
                    )}
                    <div className="text-[8px] text-[#CFC7BB]/50 truncate max-w-[140px] mt-0.5">
                      {b.requestId}
                    </div>
                  </div>
                )}

                {/* Micro Latency readout on hover */}
                <span
                  className={`text-[9px] font-mono transition-opacity duration-150 mb-1 ${
                    isHovered ? 'text-[#7D292D] font-bold opacity-100' : 'text-[#82786F] opacity-0 group-hover:opacity-100'
                  }`}
                >
                  {b.latency}ms
                </span>

                {/* Bar Track & Fill */}
                <div className="w-full flex justify-center items-end h-20">
                  <div
                    style={{ height: `${heightPercent}%` }}
                    className={`w-full max-w-[28px] rounded-t-sm transition-all duration-200 shadow-sm ${
                      isHovered
                        ? 'bg-[#7D292D] scale-x-105'
                        : isPaid
                        ? 'bg-[#A8B3A1] hover:bg-[#7D292D]'
                        : isRejected
                        ? 'bg-[#A86E24] hover:bg-[#7D292D]'
                        : 'bg-[#DED8CD] hover:bg-[#7D292D]'
                    }`}
                  />
                </div>

                {/* X-Axis Time / Service Label */}
                <div className="mt-1.5 text-center w-full">
                  <span className="block text-[10px] font-mono text-[#82786F] truncate max-w-full">
                    {b.label}
                  </span>
                  <span className="block text-[8px] font-mono text-[#82786F]/70 truncate max-w-full">
                    {b.service.replace(/^(data_|scraping_|inference_)/, '')}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="text-[10px] font-mono text-[#82786F] border-t border-[#CFC7BB]/60 pt-2 flex justify-between items-center">
        <span>Scale: 0 – {maxLatency} ms</span>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-[#38865B] font-medium">
            <span className="w-2 h-2 rounded-full bg-[#A8B3A1]" />
            Settled (Paid)
          </span>
          <span className="flex items-center gap-1.5 text-[#A86E24] font-medium">
            <span className="w-2 h-2 rounded-full bg-[#A86E24]" />
            Rejected
          </span>
        </div>
      </div>
    </div>
  );
};
export default CallsOverTimeChart;
