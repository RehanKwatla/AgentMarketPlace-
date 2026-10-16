import React from 'react';
import { LedgerRecord } from '../types';
import { X, ExternalLink, ShieldCheck } from 'lucide-react';

interface LedgerDetailModalProps {
  record: LedgerRecord | null;
  onClose: () => void;
}

export const LedgerDetailModal: React.FC<LedgerDetailModalProps> = ({ record, onClose }) => {
  if (!record) return null;

  const getStatusExplanation = (status: string) => {
    switch (status) {
      case 'paid':
        return {
          title: 'Settled & Verified Payment',
          desc: 'The seller emitted an HTTP 402 challenge with cryptographic payment requirements. The buyer generated a valid EIP-712 payment authorization, the seller verified it, executed the service, and returned an authentic settlement proof.',
          color: 'text-[#42C995] bg-[rgba(66,201,149,0.12)] border-[rgba(66,201,149,0.3)]'
        };
      case 'paid output rejected':
        return {
          title: 'Payment Settled, Output Failed Validation',
          desc: 'The payment was settled, but the data returned by the seller service failed schema validation or quality heuristics in the buyer aggregator.',
          color: 'text-[#E7B96A] bg-[rgba(231,185,106,0.12)] border-[rgba(231,185,106,0.3)]'
        };
      case 'refused':
        return {
          title: 'Refused Before Payment',
          desc: 'Task execution was refused prior to initiating payment (e.g., budget exceeded, safety violation, or seller unavailable). Zero funds were deducted.',
          color: 'text-[#E16D6D] bg-[rgba(225,109,109,0.12)] border-[rgba(225,109,109,0.3)]'
        };
      case 'failed and not charged':
        return {
          title: 'Confirmed Failure (Zero Charge)',
          desc: 'The service call encountered an unrecoverable error during execution. The payment channel/authorization was not claimed by the seller.',
          color: 'text-[#A0AAA7] bg-[#141A19] border-[rgba(120,160,153,0.20)]'
        };
      default:
        return {
          title: 'Pending Reconciliation',
          desc: 'Transaction outcome is currently being reconciled against the testnet or seller logs.',
          color: 'text-[#36D6C8] bg-[rgba(54,214,200,0.12)] border-[rgba(54,214,200,0.3)]'
        };
    }
  };

  const statusInfo = getStatusExplanation(record.status);
  const explorerUrl = record.tx_hash ? `https://sepolia.basescan.org/tx/${record.tx_hash}` : null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl bg-[#101514] border border-[rgba(120,160,153,0.22)] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[rgba(120,160,153,0.16)] bg-[#0D1111]">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#141A19] text-[#36D6C8] border border-[rgba(54,214,200,0.25)] flex items-center justify-center font-mono text-xs font-medium">
              #
            </div>
            <div>
              <h2 className="text-sm font-semibold text-[#F4F7F6]">Ledger Record Details</h2>
              <p className="text-[11px] text-[#A0AAA7] font-mono">Request ID: {record.request_id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-[#A0AAA7] hover:text-[#F4F7F6] hover:bg-[#141A19] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          {/* Status Alert Banner */}
          <div className={`p-3 rounded-lg border ${statusInfo.color}`}>
            <div className="flex items-center gap-1.5 font-medium mb-0.5">
              <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
              <span>{statusInfo.title}</span>
            </div>
            <p className="text-xs opacity-90 leading-relaxed">{statusInfo.desc}</p>
          </div>

          {/* Key Attributes Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)]">
              <span className="text-[#A0AAA7] block text-[11px] mb-0.5">Service Target</span>
              <span className="text-[#36D6C8] font-mono font-medium text-xs">{record.service_id}</span>
            </div>

            <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)]">
              <span className="text-[#A0AAA7] block text-[11px] mb-0.5">Amount Settled</span>
              <span className="text-[#F4F7F6] font-mono font-medium text-xs">{record.amount_paid} USDC</span>
              <span className="text-[#6F7C78] font-mono text-[10px] block mt-0.5">Listed: {record.listed_price} USDC</span>
            </div>

            <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)]">
              <span className="text-[#A0AAA7] block text-[11px] mb-0.5">Buyer Wallet</span>
              <span className="text-[#F4F7F6] truncate block text-[11px] font-mono">{record.buyer_id}</span>
            </div>

            <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)]">
              <span className="text-[#A0AAA7] block text-[11px] mb-0.5">Seller Payee</span>
              <span className="text-[#36D6C8] truncate block text-[11px] font-mono">{record.seller_id}</span>
            </div>
          </div>

          {/* Blockchain & Latency Details */}
          <div className="bg-[#0D1111] p-3.5 rounded-lg border border-[rgba(120,160,153,0.16)] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[#A0AAA7]">Timestamp:</span>
              <span className="text-[#F4F7F6] font-mono text-[11px]">{new Date(record.timestamp).toLocaleString()}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[#A0AAA7]">Execution Latency:</span>
              <span className="text-[#F4F7F6] font-mono text-[11px]">{record.latency_ms > 0 ? `${record.latency_ms} ms` : '—'}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[#A0AAA7]">Testnet Network:</span>
              <span className="text-[#42C995] font-mono text-[11px]">Base Sepolia (eip155:84532)</span>
            </div>

            {explorerUrl && (
              <div className="pt-2 border-t border-[rgba(120,160,153,0.14)] flex items-center justify-between">
                <span className="text-[#A0AAA7]">On-Chain Transaction:</span>
                <a
                  href={explorerUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#36D6C8] hover:underline flex items-center gap-1 font-mono text-[11px]"
                >
                  <span className="truncate max-w-[200px]">{record.tx_hash}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            )}
          </div>

          {record.error_reason && (
            <div className="p-3 bg-[rgba(225,109,109,0.08)] border border-[rgba(225,109,109,0.25)] rounded-lg text-[#E16D6D]">
              <span className="font-medium block mb-0.5">Error Reason Recorded:</span>
              <span className="text-xs">{record.error_reason}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[rgba(120,160,153,0.16)] bg-[#0D1111] flex justify-end">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-lg bg-[#141A19] hover:bg-[#1A2221] text-[#F4F7F6] text-xs font-medium transition-colors border border-[rgba(120,160,153,0.20)] cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
