import React from 'react';
import { LedgerRecord } from '../types';

interface PaymentTickerProps {
  records: LedgerRecord[];
  totalVolumeUsdc: string;
}

export const PaymentTicker: React.FC<PaymentTickerProps> = ({ records, totalVolumeUsdc }) => {
  return (
    <div className="bg-[#DED8CD]/50 border-b border-[#CFC7BB] h-11 px-4 sm:px-6 flex items-center overflow-x-auto text-xs font-mono text-[#82786F] select-none scrollbar-none backdrop-blur-sm">
      <div className="flex items-center gap-6 shrink-0 mr-6">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase font-bold text-[#82786F] tracking-wider">24H VOLUME:</span>
          <span className="text-[#7D292D] font-bold text-sm tracking-tight font-sans">
            ${totalVolumeUsdc} <span className="text-[#241B19] text-xs font-mono">USDC</span>
          </span>
        </div>
        <div className="h-4 w-px bg-[#CFC7BB]" />
      </div>

      {records.length > 0 ? (
        <div className="flex items-center gap-5 overflow-hidden whitespace-nowrap">
          {records.slice(0, 8).map((r, i) => (
            <div key={r.request_id + i} className="flex items-center gap-2 shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-[#38865B] animate-pulse" />
              <span className="text-[#241B19] font-semibold">
                {r.buyer_id ? `${r.buyer_id.slice(0, 8)}...` : r.request_id}
              </span>
              <span className="text-[#82786F]">settled</span>
              <span className="text-[#7D292D] font-bold">{r.amount_paid} USDC</span>
              <span className="text-[#82786F]">via</span>
              <span className="text-[#586452] font-medium">{r.service_id}</span>
              <span className="text-[10px] text-[#82786F] bg-[#F7F4EE] px-1.5 py-0.2 rounded border border-[#CFC7BB]">
                Base Sepolia
              </span>
              {i < Math.min(records.length, 8) - 1 && (
                <span className="text-[#CFC7BB] ml-2">/</span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2 text-xs font-mono text-[#82786F]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#A8B3A1]" />
          <span>Awaiting recorded micropayments on Base Sepolia audit ledger</span>
        </div>
      )}
    </div>
  );
};

export default PaymentTicker;
