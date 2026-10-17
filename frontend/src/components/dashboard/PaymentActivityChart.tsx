import React from 'react';
import { LedgerRecord } from '../../types';
import { Coins } from 'lucide-react';

interface PaymentActivityChartProps {
  records: LedgerRecord[];
  totalVolumeUsdc: string;
}

export const PaymentActivityChart: React.FC<PaymentActivityChartProps> = ({ 
  records, 
  totalVolumeUsdc 
}) => {
  const paidRecords = records.filter(r => r.status === 'paid' || r.status === 'paid output rejected');

  if (paidRecords.length === 0) {
    return (
      <div className="wallet-card rounded-xl p-5 border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm flex flex-col justify-between h-[280px]">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-xs font-semibold text-[#241B19] font-sans">Payment Activity & Volume</h3>
            <p className="text-[11px] text-[#82786F] font-mono">x402 settled USDC payments on Base Sepolia</p>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#DED8CD]/60 text-[#82786F] border border-[#CFC7BB]">
            $0.0000 USDC
          </span>
        </div>

        <div className="flex flex-col items-center justify-center text-center my-auto space-y-2">
          <div className="w-9 h-9 rounded-lg bg-[#DED8CD]/60 border border-[#CFC7BB] flex items-center justify-center text-[#82786F]">
            <Coins className="w-4 h-4" />
          </div>
          <p className="text-xs font-medium text-[#241B19]">No payment activity recorded</p>
          <p className="text-[11px] text-[#82786F] max-w-xs font-mono">
            When buyer agent executes microservices, on-chain settled USDC transfers appear here.
          </p>
        </div>

        <div className="text-[10px] font-mono text-[#82786F] border-t border-[#CFC7BB]/60 pt-2 flex justify-between">
          <span>Settlement asset: USDC</span>
          <span>Zero upfront charge</span>
        </div>
      </div>
    );
  }

  // Calculate cumulative volume points
  let runningSum = 0;
  const points = paidRecords.slice(0, 10).map((r, idx) => {
    runningSum += parseFloat(r.amount_paid || '0');
    return {
      x: idx,
      amount: parseFloat(r.amount_paid || '0'),
      cumulative: runningSum,
      service: r.service_id,
      label: `#${idx + 1}`
    };
  });

  const maxVal = Math.max(runningSum, 0.01);

  return (
    <div className="wallet-card rounded-xl p-5 border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm flex flex-col justify-between h-[280px] font-sans">
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <h3 className="text-xs font-semibold text-[#241B19]">Payment Activity & Cumulative Volume</h3>
          <p className="text-[11px] text-[#82786F] font-mono">Total settled USDC transfers committed on-chain</p>
        </div>
        <div className="text-right">
          <span className="text-xs font-bold font-mono text-[#7D292D]">${totalVolumeUsdc} USDC</span>
          <span className="text-[10px] text-[#82786F] block font-mono">{paidRecords.length} settled</span>
        </div>
      </div>

      {/* SVG Cumulative Sparkline / Area */}
      <div className="relative my-auto pt-2 pb-2">
        <svg className="w-full h-32 overflow-visible" viewBox="0 0 300 100" preserveAspectRatio="none">
          <defs>
            <linearGradient id="payGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#A8B3A1" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#A8B3A1" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1="0" y1="90" x2="300" y2="90" stroke="#CFC7BB" strokeWidth="1" />
          <line x1="0" y1="45" x2="300" y2="45" stroke="#CFC7BB" strokeDasharray="3 3" opacity="0.6" />

          {/* Draw Polyline & Area */}
          {points.length > 1 && (
            <>
              <polygon
                points={`
                  0,90 
                  ${points.map((p, idx) => `${(idx / (points.length - 1)) * 300},${90 - (p.cumulative / maxVal) * 75}`).join(' ')} 
                  300,90
                `}
                fill="url(#payGradient)"
              />
              <polyline
                fill="none"
                stroke="#7D292D"
                strokeWidth="2.5"
                points={points.map((p, idx) => `${(idx / (points.length - 1)) * 300},${90 - (p.cumulative / maxVal) * 75}`).join(' ')}
              />
            </>
          )}

          {/* Points */}
          {points.map((p, idx) => {
            const cx = points.length === 1 ? 150 : (idx / (points.length - 1)) * 300;
            const cy = 90 - (p.cumulative / maxVal) * 75;
            return (
              <circle
                key={idx}
                cx={cx}
                cy={cy}
                r="3.5"
                className="fill-[#7D292D] stroke-[#F7F4EE] stroke-2"
              />
            );
          })}
        </svg>
      </div>

      <div className="text-[10px] font-mono text-[#82786F] border-t border-[#CFC7BB]/60 pt-2 flex justify-between">
        <span>Cumulative Volume: ${runningSum.toFixed(4)} USDC</span>
        <span className="text-[#38865B] font-medium">Status: Verified</span>
      </div>
    </div>
  );
};
export default PaymentActivityChart;
