import React, { useState } from 'react';
import { LedgerRecord, getBaseSepoliaExplorerUrl } from '../types';
import { StatusBadge } from './ui/StatusBadge';
import { ExternalLink, Copy, Check, Clock, ShieldCheck, AlertTriangle } from 'lucide-react';
import { mapPaymentStatus } from '../utils/statusMapping';

interface LedgerTableProps {
  records: LedgerRecord[];
  onSelectRecord?: (record: LedgerRecord) => void;
  selectedRequestId?: string | null;
}

export const LedgerTable: React.FC<LedgerTableProps> = ({ 
  records, 
  onSelectRecord,
  selectedRequestId 
}) => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copyToClipboard = (text: string, key: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const getExplorerUrl = (txHash: string | null | undefined) => {
    return getBaseSepoliaExplorerUrl(txHash);
  };

  return (
    <div className="rounded-xl border border-[#CFC7BB] overflow-hidden bg-[#F7F4EE] font-mono text-xs shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#CFC7BB] bg-[#DED8CD]/50 text-[#82786F] text-[11px]">
              <th className="py-3 px-4 font-medium">Timestamp</th>
              <th className="py-3 px-4 font-medium">Request & Call Reference</th>
              <th className="py-3 px-4 font-medium">Service & Provider</th>
              <th className="py-3 px-4 font-medium">Listed Tariff</th>
              <th className="py-3 px-4 font-medium">Verified Paid</th>
              <th className="py-3 px-4 font-medium">Settlement State</th>
              <th className="py-3 px-4 font-medium hidden md:table-cell">Validation Status</th>
              <th className="py-3 px-4 font-medium hidden lg:table-cell">On-Chain Tx</th>
              <th className="py-3 px-4 font-medium text-right">Details</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-[#CFC7BB]/50 text-[#241B19]">
            {records.length === 0 ? (
              <tr>
                <td colSpan={9} className="text-center py-12 text-[#82786F] font-sans">
                  No audit ledger records match the current filter criteria.
                </td>
              </tr>
            ) : (
              records.map((record) => {
                const isSelected = selectedRequestId === record.request_id;
                const explorerUrl = getExplorerUrl(record.tx_hash);
                const statusInfo = mapPaymentStatus(record.status);
                const isPaid = record.status === 'paid';
                const isRejected = record.status === 'paid output rejected';

                // Extract task ID if available in record or embedded in request_id
                const taskId = record.task_id || (record.request_id.includes('_') ? record.request_id.split('_')[1] : null);

                return (
                  <tr
                    key={record.request_id}
                    onClick={() => onSelectRecord && onSelectRecord(record)}
                    className={`hover:bg-[#DED8CD]/30 cursor-pointer transition-colors ${
                      isSelected ? 'bg-[#DED8CD]/50 border-l-2 border-l-[#7D292D]' : ''
                    }`}
                  >
                    {/* 1. Timestamp */}
                    <td className="py-3 px-4 text-[#82786F] whitespace-nowrap">
                      <div className="flex items-center gap-1.5 text-[11px]">
                        <Clock className="w-3 h-3 text-[#82786F] shrink-0" />
                        <span title={new Date(record.timestamp).toLocaleString()}>
                          {new Date(record.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                      </div>
                      <span className="text-[10px] text-[#82786F] block mt-0.5">
                        {new Date(record.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                      </span>
                    </td>

                    {/* 2. Request & Call Reference */}
                    <td className="py-3 px-4">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-[#241B19] truncate max-w-[170px]" title={record.request_id}>
                            {record.request_id}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => copyToClipboard(record.request_id, record.request_id, e)}
                            className="text-[#82786F] hover:text-[#7D292D] transition-colors cursor-pointer"
                            title="Copy ID"
                            aria-label="Copy request ID"
                          >
                            {copiedKey === record.request_id ? (
                              <Check className="w-3 h-3 text-[#38865B]" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        </div>

                        {taskId && (
                          <span className="text-[10px] text-[#82786F] block truncate max-w-[160px]">
                            Task: {taskId}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* 3. Service & Provider */}
                    <td className="py-3 px-4">
                      <div className="space-y-0.5">
                        <span className="text-[#241B19] font-medium block">{record.service_id}</span>
                        <span className="text-[10px] text-[#82786F] block truncate max-w-[130px]" title={record.seller_id}>
                          {record.seller_id}
                        </span>
                      </div>
                    </td>

                    {/* 4. Listed Price */}
                    <td className="py-3 px-4 text-[#241B19] font-medium">
                      ${record.listed_price} <span className="text-[10px] text-[#82786F]">USDC</span>
                      {record.listed_price_units && (
                        <span className="text-[9px] text-[#82786F] block">{record.listed_price_units} units</span>
                      )}
                    </td>

                    {/* 5. Verified Paid */}
                    <td className="py-3 px-4">
                      <span className={`font-semibold ${
                        isPaid ? 'text-[#38865B]' : isRejected ? 'text-[#A86E24]' : 'text-[#82786F]'
                      }`}>
                        ${record.amount_paid} <span className="text-[10px] text-[#82786F]">USDC</span>
                      </span>
                      <span className="text-[9px] text-[#82786F] block">
                        {isPaid || isRejected ? 'Authoritative' : 'Zero charge'}
                      </span>
                    </td>

                    {/* 6. Settlement State */}
                    <td className="py-3 px-4">
                      <StatusBadge status={statusInfo.label} size="sm" />
                    </td>

                    {/* 7. Output Validation Status */}
                    <td className="py-3 px-4 hidden md:table-cell">
                      {isRejected ? (
                        <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-[#A86E24]/10 text-[#A86E24] border border-[#A86E24]/30">
                          <AlertTriangle className="w-3 h-3 text-[#A86E24]" />
                          <span>Schema Rejected</span>
                        </span>
                      ) : isPaid ? (
                        <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-[#38865B]/10 text-[#38865B] border border-[#38865B]/30">
                          <ShieldCheck className="w-3 h-3 text-[#38865B]" />
                          <span>Draft-7 Valid</span>
                        </span>
                      ) : (
                        <span className="text-[10px] text-[#82786F]">
                          Uncharged
                        </span>
                      )}
                    </td>

                    {/* 8. Transaction Hash & Explorer Link */}
                    <td className="py-3 px-4 hidden lg:table-cell">
                      {record.tx_hash ? (
                        explorerUrl ? (
                          <div className="flex items-center gap-1.5">
                            <a
                              href={explorerUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="text-[#7D292D] hover:underline flex items-center gap-1 text-[11px]"
                              title={record.tx_hash}
                            >
                              <span>{record.tx_hash.slice(0, 8)}...{record.tx_hash.slice(-4)}</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                            <button
                              type="button"
                              onClick={(e) => copyToClipboard(record.tx_hash as string, `tx_${record.request_id}`, e)}
                              className="text-[#82786F] hover:text-[#7D292D] transition-colors cursor-pointer"
                              title="Copy transaction hash"
                              aria-label="Copy transaction hash"
                            >
                              {copiedKey === `tx_${record.request_id}` ? (
                                <Check className="w-3 h-3 text-[#38865B]" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                        ) : record.tx_hash ? (
                          <span className="text-[#A3A3A3] font-mono text-[11px]" title={record.tx_hash}>
                            {record.tx_hash.startsWith('rec_') ? 'Receipt: ' : 'Proof: '}
                            {record.tx_hash.slice(0, 8)}...
                          </span>
                        ) : (
                          <span className="text-[11px] text-[#82786F] truncate max-w-[130px] block" title={record.tx_hash}>
                            {record.tx_hash.slice(0, 14)}...
                          </span>
                        )
                      ) : (
                        <span className="text-[10px] text-[#82786F]">
                          Local Auth / Uncharged
                        </span>
                      )}
                    </td>

                    {/* 9. Details Action */}
                    <td className="py-3 px-4 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectRecord && onSelectRecord(record);
                        }}
                        className="px-2.5 py-1 rounded bg-[#FFFFFF] hover:bg-[#7D292D] hover:text-[#F7F4EE] text-[#241B19] text-[11px] border border-[#CFC7BB] transition-colors cursor-pointer shadow-sm"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LedgerTable;
