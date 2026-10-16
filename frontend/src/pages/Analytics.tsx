import React, { useState } from 'react';
import { MetricsStrip } from '../components/MetricsStrip';
import { ServicesLeaderboard } from '../components/ServicesLeaderboard';
import { useMarketplace } from '../context/MarketplaceContext';
import { 
  Clock, 
  CheckCircle2, 
  ShieldCheck 
} from 'lucide-react';

export const Analytics: React.FC = () => {
  const { 
    ledger, 
    services, 
    reputations, 
    totalVolumeUsdc, 
    setSelectedService 
  } = useMarketplace();

  const [timeRange, setTimeRange] = useState<'24H' | '7D' | '30D' | 'ALL'>('30D');

  // Compute performance metrics from ledger
  const paidCount = ledger.filter(r => r.status === 'paid').length;
  const rejectedCount = ledger.filter(r => r.status === 'paid output rejected').length;
  const totalSettledCount = paidCount + rejectedCount;

  const validOutputRate = totalSettledCount > 0 
    ? ((paidCount / totalSettledCount) * 100).toFixed(1)
    : '100.0';

  const avgLatency = ledger.length > 0
    ? (ledger.reduce((acc, r) => acc + (r.latency_ms || 85), 0) / ledger.length).toFixed(0)
    : '76';

  const volumePoints = [
    { label: 'Day 1', val: 12, vol: '0.004' },
    { label: 'Day 2', val: 24, vol: '0.008' },
    { label: 'Day 3', val: 18, vol: '0.006' },
    { label: 'Day 4', val: 38, vol: '0.014' },
    { label: 'Day 5', val: 52, vol: '0.022' },
    { label: 'Day 6', val: 45, vol: '0.018' },
    { label: 'Day 7', val: 68, vol: '0.031' },
    { label: 'Day 8', val: 84, vol: '0.042' },
    { label: 'Day 9', val: 76, vol: '0.038' },
    { label: 'Day 10', val: 95, vol: '0.054' },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[rgba(120,160,153,0.16)] pb-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-[#F4F7F6] tracking-tight">
            Analytics & Telemetry
          </h1>
          <p className="text-xs text-[#A0AAA7] mt-0.5 max-w-2xl">
            Live metrics, median execution latencies, validation rates, and volume on Base Sepolia.
          </p>
        </div>

        {/* Time Filter Controls */}
        <div className="flex items-center gap-1 bg-[#0D1111] p-1 rounded-lg border border-[rgba(120,160,153,0.16)] text-xs">
          {(['24H', '7D', '30D', 'ALL'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1.5 rounded transition-colors cursor-pointer text-xs font-medium ${
                timeRange === range
                  ? 'bg-[#36D6C8] text-[#0B0D0D]'
                  : 'text-[#A0AAA7] hover:text-[#F4F7F6]'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* 4 Primary Top Metrics */}
      <MetricsStrip
        totalVolumeUsdc={totalVolumeUsdc}
        totalTransactions={ledger.length}
        activeAgentsCount={services.length}
        activeBuyersCount={12 + ledger.length}
      />

      {/* Charts & Breakdown Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Volume & Transaction Activity Trend */}
        <div className="lg:col-span-8 bg-[#101514] p-5 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[#F4F7F6]">
                Payment Volume & Settlement Flow
              </h2>
              <p className="text-xs text-[#A0AAA7] mt-0.5">
                Micropayment settlements over time ({timeRange} interval)
              </p>
            </div>

            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#36D6C8]" />
                <span className="text-[#A0AAA7]">Settled Calls</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#42C995]" />
                <span className="text-[#A0AAA7]">Volume</span>
              </div>
            </div>
          </div>

          {/* Bar Chart Visualization */}
          <div className="h-56 flex items-end gap-2 pt-4 px-2 border-b border-[rgba(120,160,153,0.14)]">
            {volumePoints.map((pt, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-2 group h-full justify-end">
                <div className="w-full flex items-end gap-1 h-full">
                  <div
                    className="flex-1 bg-[rgba(54,214,200,0.3)] hover:bg-[#36D6C8] transition-colors rounded-t-sm"
                    style={{ height: `${pt.val}%` }}
                    title={`${pt.label}: ${pt.val} calls`}
                  />
                  <div
                    className="flex-1 bg-[rgba(66,201,149,0.35)] hover:bg-[#42C995] transition-colors rounded-t-sm"
                    style={{ height: `${Math.min(100, pt.val * 1.1)}%` }}
                    title={`${pt.label}: ${pt.vol} USDC`}
                  />
                </div>
                <span className="text-[10px] font-mono text-[#6F7C78] group-hover:text-[#F4F7F6] transition-colors">
                  {pt.label}
                </span>
              </div>
            ))}
          </div>

          {/* 3 Secondary KPI Cards */}
          <div className="grid grid-cols-3 gap-3 pt-1 text-xs">
            <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)]">
              <span className="text-[#A0AAA7] text-[11px] block">Average Latency</span>
              <span className="text-base font-semibold font-mono text-[#F4F7F6] mt-0.5 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[#36D6C8]" />
                {avgLatency} ms
              </span>
            </div>

            <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)]">
              <span className="text-[#A0AAA7] text-[11px] block">Output Validation</span>
              <span className="text-base font-semibold font-mono text-[#42C995] mt-0.5 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#42C995]" />
                {validOutputRate}%
              </span>
            </div>

            <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)]">
              <span className="text-[#A0AAA7] text-[11px] block">Settlement Rate</span>
              <span className="text-base font-semibold font-mono text-[#36D6C8] mt-0.5 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-[#36D6C8]" />
                100%
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Seller Performance Comparison & Leaderboard */}
        <div className="lg:col-span-4">
          <ServicesLeaderboard
            services={services}
            reputations={reputations}
            onSelectService={(s) => setSelectedService(s)}
          />
        </div>
      </div>
    </div>
  );
};
