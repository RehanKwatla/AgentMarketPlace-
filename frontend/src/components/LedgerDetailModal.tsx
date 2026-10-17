import React from 'react';
import { LedgerRecord, getBaseSepoliaExplorerUrl } from '../types';
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
          color: 'text-[#38865B] bg-[#38865B]/10 border-[#38865B]/30'
        };
      case 'paid output rejected':
        return {
          title: 'Payment Settled, Output Failed Validation',
          desc: 'The payment was settled, but the data returned by the seller service failed schema validation or quality heuristics in the buyer aggregator.',
          color: 'text-[#A86E24] bg-[#A86E24]/10 border-[#A86E24]/30'
        };
      case 'refused':
        return {
          title: 'Refused Before Payment',
          desc: 'Task execution was refused prior to initiating payment (e.g., budget exceeded, safety violation, or seller unavailable). Zero funds were deducted.',
          color: 'text-[#82786F] bg-[#DED8CD]/50 border-[#CFC7BB]'
        };
      case 'failed and not charged':
        return {
          title: 'Confirmed Failure (Zero Charge)',
          desc: 'The service call encountered an unrecoverable error during execution. The payment channel/authorization was not claimed by the seller.',
          color: 'text-[#B84040] bg-[#B84040]/10 border-[#B84040]/30'
        };
      default:
        return {
          title: 'Pending Reconciliation',
          desc: 'Transaction outcome is currently being reconciled against the testnet or seller logs.',
          color: 'text-[#7D292D] bg-[#7D292D]/10 border-[#7D292D]/30'
        };
    }
  };

  const statusInfo = getStatusExplanation(record.status);
  const explorerUrl = getBaseSepoliaExplorerUrl(record.tx_hash);

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#241B19]/50 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl bg-[#F7F4EE] border border-[#CFC7BB] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#CFC7BB] bg-[#DED8CD]/40">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#DED8CD] text-[#7D292D] border border-[#CFC7BB] flex items-center justify-center font-mono text-xs font-semibold">
              #
            </div>
            <div>
              <h2 className="text-sm font-semibold text-[#241B19]">Ledger Record Details</h2>
              <p className="text-[11px] text-[#82786F] font-mono">Request ID: {record.request_id}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 rounded text-[#82786F] hover:text-[#241B19] hover:bg-[#DED8CD] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs font-sans">
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
            <div className="bg-[#FFFFFF] p-3 rounded-lg border border-[#CFC7BB]">
              <span className="text-[#82786F] block text-[11px] mb-0.5 font-mono">Service Target</span>
              <span className="text-[#241B19] font-mono font-medium text-xs">{record.service_id}</span>
            </div>

            <div className="bg-[#FFFFFF] p-3 rounded-lg border border-[#CFC7BB]">
              <span className="text-[#82786F] block text-[11px] mb-0.5 font-mono">Amount Settled</span>
              <span className="text-[#241B19] font-mono font-bold text-xs">{record.amount_paid} USDC</span>
              <span className="text-[#82786F] font-mono text-[10px] block mt-0.5">Listed: {record.listed_price} USDC</span>
            </div>

            <div className="bg-[#FFFFFF] p-3 rounded-lg border border-[#CFC7BB]">
              <span className="text-[#82786F] block text-[11px] mb-0.5 font-mono">Buyer Wallet</span>
              <span className="text-[#241B19] truncate block text-[11px] font-mono">{record.buyer_id}</span>
            </div>

            <div className="bg-[#FFFFFF] p-3 rounded-lg border border-[#CFC7BB]">
              <span className="text-[#82786F] block text-[11px] mb-0.5 font-mono">Seller Payee</span>
              <span className="text-[#241B19] truncate block text-[11px] font-mono">{record.seller_id}</span>
            </div>
          </div>

          {/* Blockchain & Latency Details */}
          <div className="bg-[#FFFFFF] p-3.5 rounded-lg border border-[#CFC7BB] space-y-2 font-mono">
            <div className="flex items-center justify-between">
              <span className="text-[#82786F]">Timestamp:</span>
              <span className="text-[#241B19] text-[11px]">{new Date(record.timestamp).toLocaleString()}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[#82786F]">Execution Latency:</span>
              <span className="text-[#241B19] text-[11px]">{record.latency_ms > 0 ? `${record.latency_ms} ms` : '—'}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-[#82786F]">Testnet Network:</span>
              <span className="text-[#82786F] text-[11px]">Base Sepolia (eip155:84532)</span>
            </div>

            {explorerUrl ? (
              <div className="pt-2 border-t border-[#CFC7BB] flex items-center justify-between">
                <span className="text-[#82786F]">On-Chain Transaction (BaseScan):</span>
                <a
                  href={explorerUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#7D292D] hover:underline flex items-center gap-1 text-[11px]"
                >
                  <span className="truncate max-w-[200px]">{record.tx_hash}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            ) : record.tx_hash ? (
              <div className="pt-2 border-t border-[rgba(255, 255, 255,0.14)] flex items-center justify-between">
                <span className="text-[#A3A3A3]">
                  {record.tx_hash.startsWith('rec_') ? 'Facilitator Receipt ID:' : 'Settlement Proof:'}
                </span>
                <span className="font-mono text-[11px] text-[#FAFAFA] truncate max-w-[200px]">{record.tx_hash}</span>
              </div>
            ) : null}
          </div>

          {record.error_reason && (
            <div className="p-3 bg-[#B84040]/10 border border-[#B84040]/30 rounded-lg text-[#B84040]">
              <span className="font-medium block mb-0.5">Error Reason Recorded:</span>
              <span className="text-xs">{record.error_reason}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[#CFC7BB] bg-[#DED8CD]/40 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] text-xs font-medium transition-colors cursor-pointer shadow-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
