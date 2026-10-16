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
          color: 'text-[#58B779] bg-[#58B779]/10 border-[#58B779]/30'
        };
      case 'paid output rejected':
        return {
          title: 'Payment Settled, Output Failed Validation',
          desc: 'The payment was settled, but the data returned by the seller service failed schema validation or quality heuristics in the buyer aggregator.',
          color: 'text-[#FF982E] bg-[#FF982E]/10 border-[#FF982E]/30'
        };
      case 'refused':
        return {
          title: 'Refused Before Payment',
          desc: 'Task execution was refused prior to initiating payment (e.g., budget exceeded, safety violation, or seller unavailable). Zero funds were deducted.',
          color: 'text-[#E15D52] bg-[#E15D52]/10 border-[#E15D52]/30'
        };
      case 'failed and not charged':
        return {
          title: 'Confirmed Failure (Zero Charge)',
          desc: 'The service call encountered an unrecoverable error during execution. The payment channel/authorization was not claimed by the seller.',
          color: 'text-[#A0A1A5] bg-[#202123] border-[#303133]'
        };
      default:
        return {
          title: 'Pending Reconciliation',
          desc: 'Transaction outcome is currently being reconciled against the testnet or seller logs.',
          color: 'text-[#FF982E] bg-[#FF982E]/10 border-[#FF982E]/30'
        };
    }
  };

  const statusInfo = getStatusExplanation(record.status);
  const explorerUrl = record.tx_hash ? `https://sepolia.basescan.org/tx/${record.tx_hash}` : null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl bg-[#191A1C] border border-[#303133] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#303133] bg-[#171819]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#202123] text-[#FF982E] border border-[#303133] flex items-center justify-center font-bold font-mono">
              #
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#F5F5F5] font-mono">Ledger Record Inspection</h2>
              <p className="text-[11px] text-[#777980] font-mono">Request ID: {record.request_id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#777980] hover:text-[#FF982E] hover:bg-[#202123] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs font-mono">
          {/* Status Alert Banner */}
          <div className={`p-3.5 rounded-lg border ${statusInfo.color}`}>
            <div className="flex items-center gap-2 font-bold mb-1">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>{statusInfo.title}</span>
            </div>
            <p className="font-sans text-xs opacity-90 leading-relaxed">{statusInfo.desc}</p>
          </div>

          {/* Key Attributes Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="bg-[#202123] p-3 rounded-lg border border-[#303133]">
              <span className="text-[#777980] block text-[10px] mb-1 uppercase">Service Target</span>
              <span className="text-[#FF982E] font-bold text-sm">{record.service_id}</span>
            </div>

            <div className="bg-[#202123] p-3 rounded-lg border border-[#303133]">
              <span className="text-[#777980] block text-[10px] mb-1 uppercase">Amount Settled</span>
              <span className="text-[#F5F5F5] font-bold text-sm">{record.amount_paid} USDC</span>
              <span className="text-[#777980] text-[10px] block mt-0.5">Listed: {record.listed_price} USDC</span>
            </div>

            <div className="bg-[#202123] p-3 rounded-lg border border-[#303133]">
              <span className="text-[#777980] block text-[10px] mb-1 uppercase">Timestamp (UTC)</span>
              <span className="text-[#F5F5F5]">{new Date(record.timestamp).toUTCString()}</span>
            </div>

            <div className="bg-[#202123] p-3 rounded-lg border border-[#303133]">
              <span className="text-[#777980] block text-[10px] mb-1 uppercase">Roundtrip Latency</span>
              <span className="text-[#F5F5F5]">{record.latency_ms > 0 ? `${record.latency_ms.toFixed(2)} ms` : 'N/A'}</span>
            </div>
          </div>

          {/* Participants */}
          <div className="bg-[#111214] p-3.5 rounded-lg border border-[#303133] space-y-2">
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-[#777980]">Buyer Identifier:</span>
              <span className="text-[#A0A1A5] bg-[#202123] px-2 py-0.5 rounded border border-[#303133] font-mono">
                {record.buyer_id}
              </span>
            </div>
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-[#777980]">Seller Identifier:</span>
              <span className="text-[#A0A1A5] bg-[#202123] px-2 py-0.5 rounded border border-[#303133] font-mono">
                {record.seller_id}
              </span>
            </div>
          </div>

          {/* Blockchain Settlement */}
          <div className="bg-[#111214] p-3.5 rounded-lg border border-[#303133] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[#777980] text-[11px]">Base Sepolia Transaction Hash:</span>
              <span className="text-[10px] text-[#FF982E] uppercase">eip155:84532</span>
            </div>
            {record.tx_hash ? (
              <div className="flex items-center justify-between gap-2 bg-[#202123] p-2.5 rounded border border-[#303133]">
                <span className="text-[#FF982E] break-all font-mono text-[11px]">{record.tx_hash}</span>
                {explorerUrl && (
                  <a
                    href={explorerUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 p-1 rounded bg-[#171819] text-[#A0A1A5] hover:text-[#FF982E] border border-[#303133] transition-colors"
                    title="View on BaseScan"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            ) : (
              <p className="text-[#777980] text-[11px] italic">
                No on-chain transaction hash recorded (Refused or Off-chain facilitator settlement).
              </p>
            )}
          </div>

          {/* Error Reason if any */}
          {record.error_reason && (
            <div className="bg-[#E15D52]/10 p-3 rounded-lg border border-[#E15D52]/30 text-[#E15D52]">
              <span className="font-bold text-[10px] uppercase block mb-1">Execution / Settlement Failure:</span>
              <p className="font-mono text-[11px]">{record.error_reason}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 border-t border-[#303133] bg-[#171819] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-[#202123] hover:bg-[#303133] text-[#A0A1A5] hover:text-[#F5F5F5] text-xs font-semibold font-mono transition-colors border border-[#303133]"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
