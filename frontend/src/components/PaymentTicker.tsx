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
    <div className="bg-[#171819] border-b border-[#303133] h-11 px-4 sm:px-6 flex items-center overflow-x-auto text-xs font-mono text-[#96989D] select-none scrollbar-none">
      <div className="flex items-center gap-6 shrink-0 mr-6">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase font-bold text-[#96989D]">1D PAYMENT VOL:</span>
          <span className="text-[#F5F5F5] font-bold text-sm tracking-tight">${totalVolumeUsdc} <span className="text-[#FF982E] text-xs">USDC</span></span>
        </div>
        <div className="h-4 w-px bg-[#303133]" />
      </div>

      <div className="flex items-center gap-5 overflow-hidden whitespace-nowrap">
        {displayRecords.slice(0, 8).map((r, i) => (
          <div key={r.request_id + i} className="flex items-center gap-2 shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF982E] animate-pulse" />
            <span className="text-[#F5F5F5] font-semibold">{r.buyer_id.slice(0, 8)}...</span>
            <span className="text-[#96989D]">paid</span>
            <span className="text-[#FF982E] font-bold">{r.amount_paid} USDC</span>
            <span className="text-[#96989D]">to</span>
            <span className="text-[#52758D] font-medium">{r.service_id}</span>
            <span className="text-[10px] text-[#96989D] bg-[#1D1E20] px-1 py-0.2 rounded border border-[#303133]">Base Sepolia</span>
            {i < displayRecords.length - 1 && <span className="text-[#303133] ml-2">/</span>}
          </div>
        ))}
      </div>
    </div>
  );
};
