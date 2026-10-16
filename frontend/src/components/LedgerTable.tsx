import React, { useState } from 'react';
import { LedgerRecord } from '../types';
import { StatusBadge } from './ReputationBadge';
import { ExternalLink, Filter } from 'lucide-react';

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
    <div className="space-y-3">
      {/* Filtering Toolbar */}
      <div className="flex flex-col sm:flex-row gap-2.5 items-stretch sm:items-center justify-between wallet-card p-2.5 rounded-lg text-xs font-sans">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 text-[#9BA5A2]">
            <Filter className="w-3.5 h-3.5 text-[#36D6C8]" />
            <span>Filter:</span>
          </div>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-[#0D1010] border border-[rgba(120,160,153,0.18)] rounded-md px-2.5 py-1 text-[#F4F7F6] focus:outline-none focus:border-[#36D6C8]"
          >
            <option value="all">All Statuses ({records.length})</option>
            <option value="paid">Settled</option>
            <option value="paid output rejected">Output Rejected</option>
            <option value="refused">Refused</option>
            <option value="failed and not charged">Failed (No Charge)</option>
          </select>

          <select
            value={filterService}
            onChange={(e) => setFilterService(e.target.value)}
            className="bg-[#0D1010] border border-[rgba(120,160,153,0.18)] rounded-md px-2.5 py-1 text-[#F4F7F6] focus:outline-none focus:border-[#36D6C8]"
          >
            <option value="all">All Services</option>
            {uniqueServices.map(sid => (
              <option key={sid} value={sid}>{sid}</option>
            ))}
          </select>
        </div>

        <div>
          <input
            type="text"
            placeholder="Search ID or Tx hash..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full sm:w-56 bg-[#0D1010] border border-[rgba(120,160,153,0.18)] rounded-md px-2.5 py-1 text-[#F4F7F6] placeholder-[#6B7673] focus:outline-none focus:border-[#36D6C8]"
          />
        </div>
      </div>

      {/* Ledger Records Table */}
      <div className="wallet-card rounded-lg border border-[rgba(120,160,153,0.18)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[rgba(120,160,153,0.16)] bg-[#0E1212] text-[#9BA5A2]">
                <th className="py-2.5 px-4 font-medium">Request ID</th>
                <th className="py-2.5 px-4 font-medium">Service</th>
                <th className="py-2.5 px-4 font-medium">Status</th>
                <th className="py-2.5 px-4 font-medium">Amount</th>
                <th className="py-2.5 px-4 font-medium hidden md:table-cell">Latency</th>
                <th className="py-2.5 px-4 font-medium hidden lg:table-cell">On-Chain Tx</th>
                <th className="py-2.5 px-4 font-medium text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(120,160,153,0.12)] text-[#F4F7F6]">
              {filteredRecords.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-10 text-[#6B7673]">
                    No settlement records found in the current filter.
                  </td>
                </tr>
              ) : (
                filteredRecords.map((record) => {
                  const isSelected = selectedRequestId === record.request_id;
                  const explorerUrl = getExplorerUrl(record.tx_hash);

                  return (
                    <tr
                      key={record.request_id}
                      onClick={() => onSelectRecord && onSelectRecord(record)}
                      className={`hover:bg-[#151A1A] cursor-pointer transition-colors ${
                        isSelected ? 'bg-[rgba(54,214,200,0.06)] border-l-2 border-l-[#36D6C8]' : ''
                      }`}
                    >
                      <td className="py-2.5 px-4 font-mono font-medium text-[#F4F7F6]">
                        {record.request_id}
                      </td>

                      <td className="py-2.5 px-4 font-mono text-[#36D6C8]">
                        {record.service_id}
                      </td>

                      <td className="py-2.5 px-4">
                        <StatusBadge status={record.status} />
                      </td>

                      <td className="py-2.5 px-4 font-mono font-medium">
                        {record.amount_paid} <span className="text-[11px] text-[#9BA5A2]">USDC</span>
                      </td>

                      <td className="py-2.5 px-4 font-mono text-[#9BA5A2] hidden md:table-cell">
                        {record.latency_ms > 0 ? `${record.latency_ms} ms` : '—'}
                      </td>

                      <td className="py-2.5 px-4 hidden lg:table-cell">
                        {explorerUrl ? (
                          <a
                            href={explorerUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-[#36D6C8] hover:underline flex items-center gap-1 font-mono text-[11px]"
                          >
                            <span>{record.tx_hash?.slice(0, 10)}...</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : (
                          <span className="text-[#6B7673] font-mono text-[11px]">Testnet Proof</span>
                        )}
                      </td>

                      <td className="py-2.5 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectRecord && onSelectRecord(record);
                          }}
                          className="px-2 py-0.5 rounded bg-[#161B1A] hover:bg-[#1F2524] text-[#9BA5A2] hover:text-[#F4F7F6] text-xs border border-[rgba(120,160,153,0.2)] transition-colors cursor-pointer"
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
    </div>
  );
};
