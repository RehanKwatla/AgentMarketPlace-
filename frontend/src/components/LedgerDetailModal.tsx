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
          color: 'text-emerald-400 bg-emerald-950/40 border-emerald-500/30'
        };
      case 'paid output rejected':
        return {
          title: 'Payment Settled, Output Failed Validation',
          desc: 'The payment was settled, but the data returned by the seller service failed schema validation or quality heuristics in the buyer aggregator.',
          color: 'text-amber-300 bg-amber-950/40 border-amber-500/30'
        };
      case 'refused':
        return {
          title: 'Refused Before Payment',
          desc: 'Task execution was refused prior to initiating payment (e.g., budget exceeded, safety violation, or seller unavailable). Zero funds were deducted.',
          color: 'text-rose-400 bg-rose-950/40 border-rose-500/30'
        };
      case 'failed and not charged':
        return {
          title: 'Confirmed Failure (Zero Charge)',
          desc: 'The service call encountered an unrecoverable error during execution. The payment channel/authorization was not claimed by the seller.',
          color: 'text-slate-400 bg-slate-900 border-slate-700'
        };
      default:
        return {
          title: 'Pending Reconciliation',
          desc: 'Transaction outcome is currently being reconciled against the testnet or seller logs.',
          color: 'text-blue-400 bg-blue-950/40 border-blue-500/30'
        };
    }
  };

  const statusInfo = getStatusExplanation(record.status);
  const explorerUrl = record.tx_hash ? `https://sepolia.basescan.org/tx/${record.tx_hash}` : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-2xl rounded-2xl border border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center font-bold font-mono">
              #
            </div>
            <div>
              <h2 className="text-sm font-bold text-white font-mono">Ledger Record Inspection</h2>
              <p className="text-xs text-slate-400 font-mono">Request ID: {record.request_id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs font-mono">
          {/* Status Alert Banner */}
          <div className={`p-4 rounded-xl border ${statusInfo.color}`}>
            <div className="flex items-center gap-2 font-bold mb-1">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>{statusInfo.title}</span>
            </div>
            <p className="font-sans text-xs opacity-90 leading-relaxed">{statusInfo.desc}</p>
          </div>

          {/* Key Attributes Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Service Target</span>
              <span className="text-blue-400 font-bold text-sm">{record.service_id}</span>
            </div>

            <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Amount Settled</span>
              <span className="text-emerald-400 font-bold text-sm">{record.amount_paid} USDC</span>
              <span className="text-slate-500 text-[10px] block mt-0.5">Listed: {record.listed_price} USDC</span>
            </div>

            <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Timestamp (UTC)</span>
              <span className="text-slate-200">{new Date(record.timestamp).toUTCString()}</span>
            </div>

            <div className="bg-slate-900/60 p-3 rounded-xl border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Roundtrip Latency</span>
              <span className="text-slate-200">{record.latency_ms > 0 ? `${record.latency_ms.toFixed(2)} ms` : 'N/A'}</span>
            </div>
          </div>

          {/* Participants */}
          <div className="bg-slate-900/70 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-slate-400">Buyer Identifier:</span>
              <span className="text-slate-200 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 font-mono">
                {record.buyer_id}
              </span>
            </div>
            <div className="flex justify-between items-center text-[11px]">
              <span className="text-slate-400">Seller Identifier:</span>
              <span className="text-slate-200 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 font-mono">
                {record.seller_id}
              </span>
            </div>
          </div>

          {/* Blockchain Settlement */}
          <div className="bg-slate-900/70 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 text-[11px]">Base Sepolia Transaction Hash:</span>
              <span className="text-[10px] text-slate-500 uppercase">eip155:84532</span>
            </div>
            {record.tx_hash ? (
              <div className="flex items-center justify-between gap-2 bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                <span className="text-blue-400 break-all font-mono text-[11px]">{record.tx_hash}</span>
                {explorerUrl && (
                  <a
                    href={explorerUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 p-1.5 rounded bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 border border-blue-500/30 transition-colors"
                    title="View on BaseScan"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            ) : (
              <p className="text-slate-500 text-[11px] italic">
                No on-chain transaction hash recorded (Refused or Off-chain facilitator settlement).
              </p>
            )}
          </div>

          {/* Error Reason if any */}
          {record.error_reason && (
            <div className="bg-rose-950/20 p-4 rounded-xl border border-rose-500/30 text-rose-300">
              <span className="font-bold text-[11px] block mb-1">Execution / Settlement Failure Reason:</span>
              <p className="font-mono text-[11px]">{record.error_reason}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold font-mono transition-colors border border-slate-700"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
