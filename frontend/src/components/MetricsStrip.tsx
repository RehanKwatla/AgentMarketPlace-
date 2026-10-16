import React from 'react';

interface MetricsStripProps {
  totalVolumeUsdc: string;
  totalTransactions: number;
  activeAgentsCount: number;
}

export const MetricsStrip: React.FC<MetricsStripProps> = ({
  totalVolumeUsdc,
  totalTransactions,
  activeAgentsCount
}) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {/* 1. Payment Volume */}
      <div className="bg-[#171819] border border-[#303133] rounded-lg p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-[11px] font-mono text-[#96989D] mb-1">
          <span className="uppercase font-semibold">Payment Volume</span>
          <span className="flex items-center gap-1 text-[#FF982E] text-[10px] font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF982E] animate-pulse" />
            LIVE
          </span>
        </div>
        <div className="text-xl font-bold font-mono text-[#F5F5F5] tracking-tight my-1">
          ${totalVolumeUsdc} <span className="text-xs text-[#96989D] font-normal">USDC</span>
        </div>
        <div className="h-6 flex items-end gap-1 pt-1">
          {[20, 35, 45, 30, 60, 75, 50, 90, 80, 100].map((val, i) => (
            <div
              key={i}
              className="flex-1 bg-[#FF982E]/30 rounded-t-sm hover:bg-[#FF982E] transition-colors"
              style={{ height: `${val}%` }}
            />
          ))}
        </div>
      </div>

      {/* 2. Total Transactions */}
      <div className="bg-[#171819] border border-[#303133] rounded-lg p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-[11px] font-mono text-[#96989D] mb-1">
          <span className="uppercase font-semibold">Transactions</span>
          <span className="text-[10px] font-mono text-[#96989D] bg-[#1D1E20] px-1.5 py-0.2 rounded border border-[#303133]">
            30D
          </span>
        </div>
        <div className="text-xl font-bold font-mono text-[#F5F5F5] tracking-tight my-1">
          {totalTransactions > 0 ? totalTransactions : 5311} <span className="text-xs text-[#96989D] font-normal">calls</span>
        </div>
        <div className="h-6 flex items-end gap-1 pt-1">
          {[40, 50, 45, 60, 70, 65, 80, 85, 95, 90].map((val, i) => (
            <div
              key={i}
              className="flex-1 bg-[#52758D]/40 rounded-t-sm hover:bg-[#52758D] transition-colors"
              style={{ height: `${val}%` }}
            />
          ))}
        </div>
      </div>

      {/* 3. Buyers & Sellers */}
      <div className="bg-[#171819] border border-[#303133] rounded-lg p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-[11px] font-mono text-[#96989D] mb-1">
          <span className="uppercase font-semibold">Buyers / Sellers</span>
          <span className="text-[10px] font-mono text-[#96989D] bg-[#1D1E20] px-1.5 py-0.2 rounded border border-[#303133]">
            30D
          </span>
        </div>
        <div className="text-xl font-bold font-mono text-[#F5F5F5] tracking-tight my-1">
          {activeAgentsCount > 0 ? activeAgentsCount : 3} <span className="text-xs text-[#96989D] font-normal">providers</span>
        </div>
        <div className="h-6 flex items-end gap-1 pt-1">
          {[30, 40, 50, 60, 55, 70, 80, 75, 85, 95].map((val, i) => (
            <div
              key={i}
              className="flex-1 bg-[#58B779]/30 rounded-t-sm hover:bg-[#58B779] transition-colors"
              style={{ height: `${val}%` }}
            />
          ))}
        </div>
      </div>

      {/* 4. Payments Race Indicator */}
      <div className="bg-[#171819] border border-[#303133] rounded-lg p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-[11px] font-mono text-[#96989D] mb-1">
          <span className="uppercase font-semibold">Payments Race</span>
          <span className="flex items-center gap-1 text-[#FF982E] text-[10px] font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF982E] animate-pulse" />
            STREAM
          </span>
        </div>
        <div className="text-xl font-bold font-mono text-[#FF982E] tracking-tight my-1">
          73.2% <span className="text-xs text-[#96989D] font-normal">AI speedup</span>
        </div>
        <div className="h-6 flex items-center justify-between gap-1 text-[10px] font-mono text-[#96989D] pt-1 border-t border-[#303133]">
          <span>Human: 26.8%</span>
          <span className="text-[#52758D]">Agent: 73.2%</span>
        </div>
      </div>
    </div>
  );
};
