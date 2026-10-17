import React from 'react';
import { LedgerRecord } from '../../types';
import { PieChart } from 'lucide-react';

interface OutcomeDistributionChartProps {
  records: LedgerRecord[];
}

export const OutcomeDistributionChart: React.FC<OutcomeDistributionChartProps> = ({ records }) => {
  const total = records.length;
  const paidCount = records.filter(r => r.status === 'paid').length;
  const rejectedCount = records.filter(r => r.status === 'paid output rejected').length;
  const failedCount = records.filter(r => r.status === 'failed and not charged' || r.status === 'refused').length;

  if (total === 0) {
    return (
      <div className="wallet-card rounded-xl p-5 border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm flex flex-col justify-between h-[280px]">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-xs font-semibold text-[#241B19] font-sans">Outcome Distribution</h3>
            <p className="text-[11px] text-[#82786F] font-mono">Execution settlement and validation results</p>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#DED8CD]/60 text-[#82786F] border border-[#CFC7BB]">
            No telemetry
          </span>
        </div>

        <div className="flex flex-col items-center justify-center text-center my-auto space-y-2">
          <div className="w-9 h-9 rounded-lg bg-[#DED8CD]/60 border border-[#CFC7BB] flex items-center justify-center text-[#82786F]">
            <PieChart className="w-4 h-4" />
          </div>
          <p className="text-xs font-medium text-[#241B19]">No outcomes recorded</p>
          <p className="text-[11px] text-[#82786F] max-w-xs font-mono">
            Requires at least 1 executed call to display settlement vs rejection ratios.
          </p>
        </div>

        <div className="text-[10px] font-mono text-[#82786F] border-t border-[#CFC7BB]/60 pt-2 flex justify-between">
          <span>Categories: Paid, Rejected, Failed</span>
          <span>Zero fabricated data</span>
        </div>
      </div>
    );
  }

  const paidPct = Math.round((paidCount / total) * 100);
  const rejectedPct = Math.round((rejectedCount / total) * 100);
  const failedPct = Math.max(0, 100 - paidPct - rejectedPct);

  return (
    <div className="wallet-card rounded-xl p-5 border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm flex flex-col justify-between h-[280px] font-sans">
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <h3 className="text-xs font-semibold text-[#241B19]">Execution Outcome Distribution</h3>
          <p className="text-[11px] text-[#82786F] font-mono">Audited proportion of settled calls vs schema rejections</p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB]">
          {total} total
        </span>
      </div>

      {/* Segmented Distribution Bar */}
      <div className="my-auto space-y-3 pt-2">
        <div className="w-full h-4 rounded-full bg-[#DED8CD] overflow-hidden flex border border-[#CFC7BB]">
          {paidPct > 0 && (
            <div 
              style={{ width: `${paidPct}%` }} 
              className="bg-[#38865B] h-full transition-all duration-500" 
              title={`Paid & Output Validated: ${paidCount} (${paidPct}%)`}
            />
          )}
          {rejectedPct > 0 && (
            <div 
              style={{ width: `${rejectedPct}%` }} 
              className="bg-[#A86E24] h-full transition-all duration-500" 
              title={`Paid Output Rejected: ${rejectedCount} (${rejectedPct}%)`}
            />
          )}
          {failedPct > 0 && (
            <div 
              style={{ width: `${failedPct}%` }} 
              className="bg-[#82786F] h-full transition-all duration-500" 
              title={`Refused / Failed: ${failedCount} (${failedPct}%)`}
            />
          )}
        </div>

        {/* Legend with exact numbers */}
        <div className="grid grid-cols-3 gap-2 text-[11px] font-mono pt-1">
          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5 text-[#38865B]">
              <span className="w-2 h-2 rounded-full bg-[#38865B]" />
              <span className="font-semibold">Paid</span>
            </div>
            <span className="text-[#241B19] font-bold block">{paidCount} ({paidPct}%)</span>
            <span className="text-[9px] text-[#82786F] block">Settled & verified</span>
          </div>

          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5 text-[#A86E24]">
              <span className="w-2 h-2 rounded-full bg-[#A86E24]" />
              <span className="font-semibold">Rejected</span>
            </div>
            <span className="text-[#241B19] font-bold block">{rejectedCount} ({rejectedPct}%)</span>
            <span className="text-[9px] text-[#82786F] block">Schema invalid</span>
          </div>

          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5 text-[#82786F]">
              <span className="w-2 h-2 rounded-full bg-[#82786F]" />
              <span className="font-semibold">Not Charged</span>
            </div>
            <span className="text-[#241B19] font-bold block">{failedCount} ({failedPct}%)</span>
            <span className="text-[9px] text-[#82786F] block">Zero budget risk</span>
          </div>
        </div>
      </div>

      <div className="text-[10px] font-mono text-[#82786F] border-t border-[#CFC7BB]/60 pt-2 flex justify-between">
        <span>Verified settlement evidence</span>
        <span className="text-[#38865B] font-medium">{paidPct}% Success</span>
      </div>
    </div>
  );
};
export default OutcomeDistributionChart;
