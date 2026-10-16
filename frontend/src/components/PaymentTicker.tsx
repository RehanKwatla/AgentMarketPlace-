import React from 'react';
import { LedgerRecord } from '../types';

interface PaymentTickerProps {
  records: LedgerRecord[];
  totalVolumeUsdc: string;
}

export const PaymentTicker: React.FC<PaymentTickerProps> = ({ records, totalVolumeUsdc }) => {
  // Demo or real payments for horizontal ticker
  const displayRecords = records.length > 0 ? records : [
    { request_id: 'req_a912', service_id: 'inference_001', amount_paid: '0.004', buyer_id: '0x3a8...c812', status: 'paid', timestamp: new Date().toISOString(), seller_id: '0x99...', listed_price: '0.004', tx_hash: null, latency_ms: 112, error_reason: null },
    { request_id: 'req_b441', service_id: 'data_001', amount_paid: '0.002', buyer_id: '0x17b...4e91', status: 'paid', timestamp: new Date().toISOString(), seller_id: '0x88...', listed_price: '0.002', tx_hash: null, latency_ms: 84, error_reason: null },
    { request_id: 'req_c821', service_id: 'scraping_001', amount_paid: '0.003', buyer_id: '0x88c...df20', status: 'paid', timestamp: new Date().toISOString(), seller_id: '0x77...', listed_price: '0.003', tx_hash: null, latency_ms: 290, error_reason: null },
    { request_id: 'req_d311', service_id: 'inference_001', amount_paid: '0.004', buyer_id: '0x49f...912a', status: 'paid', timestamp: new Date().toISOString(), seller_id: '0x99...', listed_price: '0.004', tx_hash: null, latency_ms: 135, error_reason: null }
  ];

  return (
    <div className="bg-[#0B0D0D]/95 border-b border-[rgba(120,160,153,0.18)] h-11 px-4 sm:px-6 flex items-center overflow-x-auto text-xs font-mono text-[#A0AAA7] select-none scrollbar-none backdrop-blur-sm">
      <div className="flex items-center gap-6 shrink-0 mr-6">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase font-bold text-[#6F7C78] tracking-wider">24H VOLUME:</span>
          <span className="text-[#F4F7F6] font-bold text-sm tracking-tight">
            ${totalVolumeUsdc} <span className="text-[#36D6C8] text-xs">USDC</span>
          </span>
        </div>
        <div className="h-4 w-px bg-[rgba(120,160,153,0.20)]" />
      </div>

      <div className="flex items-center gap-5 overflow-hidden whitespace-nowrap">
        {displayRecords.slice(0, 8).map((r, i) => (
          <div key={r.request_id + i} className="flex items-center gap-2 shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-[#36D6C8] animate-pulse" />
            <span className="text-[#F4F7F6] font-semibold">{r.buyer_id.slice(0, 8)}...</span>
            <span className="text-[#6F7C78]">settled</span>
            <span className="text-[#36D6C8] font-bold">{r.amount_paid} USDC</span>
            <span className="text-[#6F7C78]">via</span>
            <span className="text-[#42C995] font-medium">{r.service_id}</span>
            <span className="text-[10px] text-[#A0AAA7] bg-[#141A19] px-1.5 py-0.2 rounded border border-[rgba(120,160,153,0.20)]">
              Base Sepolia
            </span>
            {i < displayRecords.length - 1 && <span className="text-[rgba(120,160,153,0.25)] ml-2">/</span>}
          </div>
        ))}
      </div>
    </div>
  );
};
