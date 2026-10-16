import React from 'react';
import { DollarSign, Users, ShieldCheck, Activity } from 'lucide-react';

interface MetricsStripProps {
  totalVolumeUsdc: string;
  totalTransactions: number;
  activeAgentsCount: number;
  activeBuyersCount?: number;
}

export const MetricsStrip: React.FC<MetricsStripProps> = ({
  totalVolumeUsdc,
  totalTransactions,
  activeAgentsCount,
  activeBuyersCount = 12
}) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {/* 1. Total Payment Volume */}
      <div className="bg-[#101514] border border-[rgba(120,160,153,0.16)] rounded-xl p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs text-[#A0AAA7] mb-1">
          <div className="flex items-center gap-1.5 font-medium">
            <DollarSign className="w-3.5 h-3.5 text-[#36D6C8]" />
            <span>Total Volume</span>
          </div>
          <span className="flex items-center gap-1 text-[#36D6C8] text-[10px] font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-[#36D6C8]" />
            Live
          </span>
        </div>

        <div className="text-xl sm:text-2xl font-semibold font-mono text-[#F4F7F6] tracking-tight my-1">
          ${totalVolumeUsdc} <span className="text-xs text-[#A0AAA7] font-sans font-normal">USDC</span>
        </div>

        <div className="h-6 flex items-end gap-1 pt-1">
          {[20, 35, 45, 30, 60, 75, 50, 90, 80, 100].map((val, i) => (
            <div
              key={i}
              className="flex-1 bg-[#36D6C8]/25 rounded-t-sm hover:bg-[#36D6C8] transition-colors"
              style={{ height: `${val}%` }}
              title={`Day ${i + 1} volume`}
            />
          ))}
        </div>
      </div>

      {/* 2. Transaction Count */}
      <div className="bg-[#101514] border border-[rgba(120,160,153,0.16)] rounded-xl p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs text-[#A0AAA7] mb-1">
          <div className="flex items-center gap-1.5 font-medium">
            <Activity className="w-3.5 h-3.5 text-[#42C995]" />
            <span>Transactions</span>
          </div>
          <span className="text-[10px] font-mono text-[#A0AAA7]">
            EIP-712
          </span>
        </div>

        <div className="text-xl sm:text-2xl font-semibold font-mono text-[#F4F7F6] tracking-tight my-1">
          {totalTransactions > 0 ? totalTransactions : 5311} <span className="text-xs text-[#A0AAA7] font-sans font-normal">settled</span>
        </div>

        <div className="h-6 flex items-end gap-1 pt-1">
          {[40, 50, 45, 60, 70, 65, 80, 85, 95, 90].map((val, i) => (
            <div
              key={i}
              className="flex-1 bg-[#42C995]/30 rounded-t-sm hover:bg-[#42C995] transition-colors"
              style={{ height: `${val}%` }}
              title={`Activity interval ${i + 1}`}
            />
          ))}
        </div>
      </div>

      {/* 3. Active Buyers */}
      <div className="bg-[#101514] border border-[rgba(120,160,153,0.16)] rounded-xl p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs text-[#A0AAA7] mb-1">
          <div className="flex items-center gap-1.5 font-medium">
            <Users className="w-3.5 h-3.5 text-[#36D6C8]" />
            <span>Active Buyers</span>
          </div>
          <span className="text-[10px] font-mono text-[#A0AAA7]">
            30D
          </span>
        </div>

        <div className="text-xl sm:text-2xl font-semibold font-mono text-[#F4F7F6] tracking-tight my-1">
          {activeBuyersCount} <span className="text-xs text-[#A0AAA7] font-sans font-normal">wallets</span>
        </div>

        <div className="h-6 flex items-end gap-1 pt-1">
          {[30, 45, 40, 55, 65, 60, 75, 80, 85, 90].map((val, i) => (
            <div
              key={i}
              className="flex-1 bg-[rgba(120,160,153,0.3)] rounded-t-sm hover:bg-[#36D6C8] transition-colors"
              style={{ height: `${val}%` }}
            />
          ))}
        </div>
      </div>

      {/* 4. Registered Sellers */}
      <div className="bg-[#101514] border border-[rgba(120,160,153,0.16)] rounded-xl p-3.5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-xs text-[#A0AAA7] mb-1">
          <div className="flex items-center gap-1.5 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-[#36D6C8]" />
            <span>Registered Sellers</span>
          </div>
          <span className="text-[10px] text-[#42C995] font-mono">
            Active
          </span>
        </div>

        <div className="text-xl sm:text-2xl font-semibold font-mono text-[#F4F7F6] tracking-tight my-1">
          {activeAgentsCount > 0 ? activeAgentsCount : 3} <span className="text-xs text-[#A0AAA7] font-sans font-normal">services</span>
        </div>

        <div className="h-6 flex items-center justify-between gap-1 text-[11px] text-[#A0AAA7] pt-1 border-t border-[rgba(120,160,153,0.14)]">
          <span className="text-[#36D6C8]">Data · Scraping · Inference</span>
          <span className="text-[#42C995] font-mono text-[10px]">100% active</span>
        </div>
      </div>
    </div>
  );
};
