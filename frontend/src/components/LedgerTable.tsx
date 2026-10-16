import React, { useState } from 'react';
import { LedgerRecord } from '../types';
import { StatusBadge } from './ReputationBadge';
import { ExternalLink, Filter, ChevronRight, Clock } from 'lucide-react';

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
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterService, setFilterService] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const uniqueServices = Array.from(new Set(records.map(r => r.service_id)));

  const filteredRecords = records.filter(r => {
    if (filterStatus !== 'all' && r.status !== filterStatus) return false;
    if (filterService !== 'all' && r.service_id !== filterService) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return (
        r.request_id.toLowerCase().includes(q) ||
        r.service_id.toLowerCase().includes(q) ||
        (r.tx_hash && r.tx_hash.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const getExplorerUrl = (txHash: string | null) => {
    if (!txHash) return null;
    return `https://sepolia.basescan.org/tx/${txHash}`;
  };

  return (
    <div className="space-y-4">
      {/* Filtering Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-[#171819] p-3 rounded-lg border border-[#303133] text-xs font-mono">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 text-[#777980]">
            <Filter className="w-3.5 h-3.5" />
            <span>Filter:</span>
          </div>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-[#101112] border border-[#303133] rounded px-2.5 py-1 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E]"
          >
            <option value="all">All Statuses ({records.length})</option>
            <option value="paid">Verified Paid</option>
            <option value="paid output rejected">Output Rejected</option>
            <option value="refused">Refused Before Payment</option>
            <option value="failed and not charged">Failed (No Charge)</option>
          </select>

          <select
            value={filterService}
            onChange={(e) => setFilterService(e.target.value)}
            className="bg-[#101112] border border-[#303133] rounded px-2.5 py-1 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E]"
          >
            <option value="all">All Services</option>
            {uniqueServices.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        <div className="relative">
          <input
            type="text"
            placeholder="Search Request ID or Tx..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-[#101112] border border-[#303133] rounded px-3 py-1 text-[#F5F5F5] placeholder-[#777980] focus:outline-none focus:border-[#FF982E] w-full sm:w-48"
          />
        </div>
      </div>

      {/* Main Table */}
      {filteredRecords.length === 0 ? (
        <div className="text-center py-12 bg-[#171819] rounded-lg text-[#777980] font-mono text-xs border border-[#303133] p-8 space-y-2">
          <Clock className="w-8 h-8 text-[#777980] mx-auto" />
          <p className="text-[#F5F5F5] font-semibold">No ledger records match the selected criteria</p>
          <p className="text-[#777980]">
            {records.length === 0 
              ? 'Execute a buyer task in the Buyer Console to trigger genuine x402 micropayments.'
              : 'Try clearing your active filters to view all audit entries.'}
          </p>
        </div>
      ) : (
        <div className="bg-[#171819] rounded-lg overflow-hidden border border-[#303133]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#1D1E20] text-[#96989D] border-b border-[#303133] uppercase text-[11px]">
                <tr>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Request ID</th>
                  <th className="px-4 py-3">Service</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Protocol Settlement</th>
                  <th className="px-4 py-3">Latency</th>
                  <th className="px-4 py-3">Base Sepolia Tx</th>
                  <th className="px-3 py-3 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#303133]">
                {filteredRecords.map((r) => {
                  const isSelected = selectedRequestId === r.request_id;
                  const explorerLink = getExplorerUrl(r.tx_hash);

                  return (
                    <tr 
                      key={r.request_id} 
                      onClick={() => onSelectRecord && onSelectRecord(r)}
                      className={`hover:bg-[#1D1E20] transition-colors cursor-pointer ${
                        isSelected ? 'bg-[#202123] border-l-2 border-l-[#FF982E]' : ''
                      }`}
                    >
                      <td className="px-4 py-3 text-[#A0A1A5] whitespace-nowrap">
                        {new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>
                      <td className="px-4 py-3 font-semibold text-[#F5F5F5]">
                        <span className="bg-[#111214] px-1.5 py-0.5 rounded border border-[#303133]">
                          {r.request_id}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[#FF982E] hover:underline">{r.service_id}</span>
                      </td>
                      <td className="px-4 py-3 text-[#F5F5F5] font-bold whitespace-nowrap">
                        {r.amount_paid} <span className="text-[10px] text-[#FF982E]">USDC</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="px-4 py-3 text-[#A0A1A5] whitespace-nowrap">
                        {r.latency_ms > 0 ? `${r.latency_ms.toFixed(1)} ms` : '—'}
                      </td>
                      <td className="px-4 py-3 text-[#A0A1A5] whitespace-nowrap">
                        {r.tx_hash ? (
                          <a
                            href={explorerLink || '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-[#FF982E] hover:underline font-mono text-[11px]"
                            title={r.tx_hash}
                          >
                            <span>{r.tx_hash.slice(0, 8)}...{r.tx_hash.slice(-6)}</span>
                            <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        ) : (
                          <span className="text-[#777980]">—</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-right">
                        <ChevronRight className="w-4 h-4 text-[#777980] inline-block" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
