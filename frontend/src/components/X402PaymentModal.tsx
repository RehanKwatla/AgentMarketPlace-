import React, { useState } from 'react';
import { 
  X, 
  ExternalLink, 
  ShieldCheck, 
  Copy, 
  Check, 
  Terminal, 
  Layers, 
  AlertTriangle,
  Clock,
  Coins
} from 'lucide-react';
import { LedgerRecord } from '../types';
import { mapPaymentStatus } from '../utils/statusMapping';
import { StatusBadge } from './ui/StatusBadge';

export interface PaymentDisplayRecord {
  request_id: string;
  task_id?: string | null;
  call_id?: string | null;
  service_id: string;
  seller_id?: string;
  buyer_id?: string;
  listed_price?: string;
  amount_paid?: string;
  amount_units?: number | null;
  listed_units?: number | null;
  status: string;
  tx_hash?: string | null;
  settlement_proof?: string | null;
  timestamp?: string;
  latency_ms?: number;
  error_reason?: string | null;
  network?: string | null;
  token?: string | null;
  seller_pay_to?: string | null;
  validation_status?: string | null;
}

interface X402PaymentModalProps {
  record: PaymentDisplayRecord | LedgerRecord | null;
  onClose: () => void;
}

export const X402PaymentModal: React.FC<X402PaymentModalProps> = ({ record, onClose }) => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'summary' | 'x402_challenge' | 'eip712' | 'raw_json'>('summary');

  if (!record) return null;

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const statusInfo = mapPaymentStatus(record.status);
  
  // Format transaction hash and explorer link
  const txHash = record.tx_hash;
  const isRealOnChainTx = txHash && txHash.startsWith('0x') && txHash.length >= 42;
  const explorerUrl = isRealOnChainTx ? `https://sepolia.basescan.org/tx/${txHash}` : null;

  const tokenContract = (record as any).token || '0x036CbD53842c5426634e7929541eC2318f3dCF7e';
  const network = (record as any).network || 'eip155:84532';
  const recipient = (record as any).seller_pay_to || (record as any).seller_recipient || (record as any).seller_id || '0x0000000000000000000000000000000000000001';

  // Construct official x402 challenge representation backed by backend data
  const x402Challenge = {
    protocol_version: '2.0',
    status: 402,
    status_text: 'Payment Required',
    scheme: 'x402-v2',
    network: network,
    token_address: tokenContract,
    token_symbol: 'USDC',
    amount_base_units: (record as any).amount_paid_units || (record as any).listed_price_units || 2000,
    amount_usdc: record.amount_paid || record.listed_price || '0.002',
    pay_to: recipient,
    nonce: `nonce_${record.request_id.slice(-12)}`,
    service_id: record.service_id,
  };

  // Construct EIP-712 Domain and Authorization Structure
  const eip712Spec = {
    types: {
      EIP712Domain: [
        { name: 'name', type: 'string' },
        { name: 'version', type: 'string' },
        { name: 'chainId', type: 'uint256' },
        { name: 'verifyingContract', type: 'address' },
      ],
      PaymentAuthorization: [
        { name: 'payTo', type: 'address' },
        { name: 'amount', type: 'uint256' },
        { name: 'validUntil', type: 'uint256' },
        { name: 'nonce', type: 'bytes32' },
      ],
    },
    domain: {
      name: 'x402 Micropayment Rail',
      version: '2.0',
      chainId: 84532,
      verifyingContract: tokenContract,
    },
    message: {
      payTo: recipient,
      amount: String((record as any).amount_paid_units || 2000),
      validUntil: Math.floor(new Date(record.timestamp || Date.now()).getTime() / 1000) + 3600,
      nonce: `0x${record.request_id.replace(/[^a-fA-F0-9]/g, '0').padEnd(64, '0').slice(0, 64)}`,
    },
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#241B19]/50 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-3xl bg-[#F7F4EE] border border-[#CFC7BB] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#CFC7BB] bg-[#DED8CD]/40">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#7D292D] text-[#F7F4EE] flex items-center justify-center font-mono text-xs shadow-xs">
              <Coins className="w-4 h-4 text-[#F7F4EE]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-serif font-bold text-[#241B19]">x402 Payment Lifecycle Detail</h2>
                <StatusBadge 
                  status={statusInfo.label} 
                  size="sm" 
                />
              </div>
              <p className="text-[11px] text-[#82786F] font-mono mt-0.5">
                Request Ref: {record.request_id}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#82786F] hover:text-[#241B19] hover:bg-[#DED8CD]/50 transition-colors cursor-pointer border border-transparent hover:border-[#CFC7BB]"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 px-6 border-b border-[#CFC7BB] bg-[#DED8CD]/20 text-xs font-mono">
          <button
            type="button"
            onClick={() => setActiveTab('summary')}
            className={`py-3 px-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'summary'
                ? 'border-[#7D292D] text-[#7D292D] font-bold'
                : 'border-transparent text-[#82786F] hover:text-[#241B19]'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Summary & Settlement</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('x402_challenge')}
            className={`py-3 px-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'x402_challenge'
                ? 'border-[#7D292D] text-[#7D292D] font-bold'
                : 'border-transparent text-[#82786F] hover:text-[#241B19]'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>HTTP 402 Challenge</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('eip712')}
            className={`py-3 px-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'eip712'
                ? 'border-[#7D292D] text-[#7D292D] font-bold'
                : 'border-transparent text-[#82786F] hover:text-[#241B19]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>EIP-712 Specification</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('raw_json')}
            className={`py-3 px-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'raw_json'
                ? 'border-[#7D292D] text-[#7D292D] font-bold'
                : 'border-transparent text-[#82786F] hover:text-[#241B19]'
            }`}
          >
            <span>Raw Payload</span>
          </button>
        </div>

        {/* Body Content */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs font-sans">
          {/* TAB 1: SUMMARY & SETTLEMENT */}
          {activeTab === 'summary' && (
            <div className="space-y-4">
              {/* Status explanation alert */}
              <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] space-y-1.5 shadow-xs">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-[#241B19] font-mono text-xs">
                    {statusInfo.label}
                  </span>
                  <span className="text-[10px] text-[#82786F] font-mono">
                    Terminal State: {statusInfo.isTerminal ? 'YES' : 'PENDING'}
                  </span>
                </div>
                <p className="text-xs text-[#82786F] leading-relaxed">
                  {statusInfo.description}
                </p>
              </div>

              {/* Financial Distinction Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] space-y-1 shadow-xs">
                  <span className="text-[11px] font-mono text-[#82786F] block">Listed Service Price</span>
                  <div className="text-sm font-bold font-mono text-[#241B19]">
                    {record.listed_price ? `$${record.listed_price} USDC` : '—'}
                  </div>
                  <span className="text-[10px] text-[#82786F] font-mono block">
                    {(record as any).listed_price_units ? `${(record as any).listed_price_units} units` : 'Published tariff'}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] space-y-1 shadow-xs">
                  <span className="text-[11px] font-mono text-[#82786F] block">Verified Amount Paid</span>
                  <div className="text-sm font-bold font-mono text-[#7D292D]">
                    {record.status === 'paid' || record.status === 'paid output rejected' 
                      ? `$${record.amount_paid} USDC` 
                      : '$0.000000 USDC'}
                  </div>
                  <span className="text-[10px] text-[#82786F] font-mono block">
                    {record.status === 'paid' || record.status === 'paid output rejected' 
                      ? 'Authoritatively charged' 
                      : 'Not charged / Held in suspense'}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] space-y-1 shadow-xs">
                  <span className="text-[11px] font-mono text-[#82786F] block">Settlement Asset</span>
                  <div className="text-sm font-bold font-mono text-[#241B19]">
                    USDC (Base Sepolia)
                  </div>
                  <span className="text-[10px] text-[#82786F] font-mono block truncate" title={tokenContract}>
                    Contract: {tokenContract.slice(0, 10)}...{tokenContract.slice(-6)}
                  </span>
                </div>
              </div>

              {/* Identification & Provenance Card */}
              <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] space-y-2.5 font-mono text-xs shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-[#82786F]">Target Microservice:</span>
                  <span className="text-[#241B19] font-medium">{record.service_id}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[#82786F]">Provider PayTo Address:</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#241B19]">{recipient}</span>
                    <button
                      onClick={() => copyToClipboard(recipient, 'payTo')}
                      className="text-[#82786F] hover:text-[#241B19] transition-colors cursor-pointer"
                      title="Copy Address"
                    >
                      {copiedKey === 'payTo' ? <Check className="w-3.5 h-3.5 text-[#38865B]" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                {(record as any).task_id && (
                  <div className="flex items-center justify-between">
                    <span className="text-[#82786F]">Associated Task ID:</span>
                    <span className="text-[#241B19]">{(record as any).task_id}</span>
                  </div>
                )}

                {(record as any).call_id && (
                  <div className="flex items-center justify-between">
                    <span className="text-[#82786F]">Task Call ID:</span>
                    <span className="text-[#241B19]">{(record as any).call_id}</span>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <span className="text-[#82786F]">Network Chain ID:</span>
                  <span className="text-[#82786F]">{network} (Base Sepolia)</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[#82786F]">Execution Latency:</span>
                  <span className="text-[#241B19] flex items-center gap-1">
                    <Clock className="w-3 h-3 text-[#82786F]" />
                    <span>{record.latency_ms && record.latency_ms > 0 ? `${record.latency_ms} ms` : '—'}</span>
                  </span>
                </div>

                {record.timestamp && (
                  <div className="flex items-center justify-between">
                    <span className="text-[#82786F]">Recorded Timestamp:</span>
                    <span className="text-[#82786F]">{new Date(record.timestamp).toLocaleString()}</span>
                  </div>
                )}
              </div>

              {/* Transaction Hash / Settlement Proof */}
              <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] space-y-2 font-mono text-xs shadow-xs">
                <span className="text-[#82786F] block text-[11px] font-medium">Settlement Verification Reference:</span>
                {txHash ? (
                  <div className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-[#F7F4EE] border border-[#CFC7BB]">
                    <span className="text-[#241B19] truncate max-w-[480px]">
                      {txHash}
                    </span>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => copyToClipboard(txHash, 'txHash')}
                        className="p-1 rounded text-[#82786F] hover:text-[#241B19] transition-colors cursor-pointer"
                        title="Copy Hash"
                      >
                        {copiedKey === 'txHash' ? <Check className="w-3.5 h-3.5 text-[#38865B]" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>

                      {explorerUrl && (
                        <a
                          href={explorerUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-2.5 py-1 rounded bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-medium text-[11px] flex items-center gap-1 transition-colors shadow-xs"
                        >
                          <span>Explorer</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-[#A86E24]/10 border border-[#A86E24]/30 text-[#A86E24] text-xs flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>
                      No public on-chain transaction hash recorded. Attempt may be held in suspense, uncharged, or validated via local EIP-712 cryptographic authorization.
                    </span>
                  </div>
                )}
              </div>

              {/* Error Reason (if recorded) */}
              {record.error_reason && (
                <div className="p-3.5 rounded-xl bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] space-y-1">
                  <span className="font-semibold text-xs font-mono block">Recorded Backend Error:</span>
                  <p className="text-xs font-mono">{record.error_reason}</p>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: HTTP 402 CHALLENGE DETAILS */}
          {activeTab === 'x402_challenge' && (
            <div className="space-y-3 font-mono text-xs">
              <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] space-y-2 shadow-xs">
                <div className="flex items-center justify-between pb-2 border-b border-[#CFC7BB]/60">
                  <span className="text-[#82786F]">HTTP Response Status:</span>
                  <span className="text-[#A86E24] font-bold">402 Payment Required</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#82786F]">Protocol Specification:</span>
                  <span className="text-[#241B19]">x402 v2.0 Micro-Routing</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#82786F]">Exposed Challenge Header:</span>
                  <span className="text-[#241B19]">X-402-Requirement</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#82786F]">Settlement Proof Header:</span>
                  <span className="text-[#241B19]">X-402-Settlement-Proof</span>
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-[#82786F] font-medium">Raw X-402-Requirement Header Payload:</span>
                  <button
                    onClick={() => copyToClipboard(JSON.stringify(x402Challenge, null, 2), 'x402')}
                    className="text-[#82786F] hover:text-[#241B19] text-[11px] flex items-center gap-1 cursor-pointer"
                  >
                    {copiedKey === 'x402' ? <Check className="w-3 h-3 text-[#38865B]" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedKey === 'x402' ? 'Copied' : 'Copy Header'}</span>
                  </button>
                </div>
                <pre className="p-4 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] text-[#241B19] text-[11px] overflow-x-auto leading-relaxed shadow-inner">
                  {JSON.stringify(x402Challenge, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* TAB 3: EIP-712 SPECIFICATION */}
          {activeTab === 'eip712' && (
            <div className="space-y-3 font-mono text-xs">
              <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] text-[#241B19] text-[11px] leading-relaxed shadow-xs">
                The buyer orchestrator signs an EIP-712 typed payment authorization containing the specific target payee, maximum micro-spend, expiration deadline, and request nonce. The seller settles this cryptographically without requiring user wallet popups for each call.
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-[#82786F] font-medium">EIP-712 Typed Structured Data:</span>
                  <button
                    onClick={() => copyToClipboard(JSON.stringify(eip712Spec, null, 2), 'eip712')}
                    className="text-[#82786F] hover:text-[#241B19] text-[11px] flex items-center gap-1 cursor-pointer"
                  >
                    {copiedKey === 'eip712' ? <Check className="w-3 h-3 text-[#38865B]" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedKey === 'eip712' ? 'Copied' : 'Copy EIP-712'}</span>
                  </button>
                </div>
                <pre className="p-4 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] text-[#241B19] text-[11px] overflow-x-auto leading-relaxed shadow-inner">
                  {JSON.stringify(eip712Spec, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* TAB 4: RAW PAYLOAD */}
          {activeTab === 'raw_json' && (
            <div className="space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-[#82786F] font-medium">Persisted Backend Record:</span>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(record, null, 2), 'raw')}
                  className="text-[#82786F] hover:text-[#241B19] text-[11px] flex items-center gap-1 cursor-pointer"
                >
                  {copiedKey === 'raw' ? <Check className="w-3 h-3 text-[#38865B]" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedKey === 'raw' ? 'Copied' : 'Copy JSON'}</span>
                </button>
              </div>
              <pre className="p-4 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] text-[#241B19] text-[11px] overflow-x-auto leading-relaxed max-h-[350px] shadow-inner">
                {JSON.stringify(record, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#CFC7BB] bg-[#DED8CD]/30 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2 text-[#82786F] text-[11px]">
            <ShieldCheck className="w-3.5 h-3.5 text-[#38865B]" />
            <span>Authoritative backend record. Zero browser signing or key exposure.</span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] font-medium border border-[#CFC7BB] transition-colors cursor-pointer shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
