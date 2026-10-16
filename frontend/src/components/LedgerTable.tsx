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

  // Extract distinct services from records
  const uniqueServices = Array.from(new Set(records.map(r => r.service_id)));

  // Filter records
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
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-slate-900/60 p-3 rounded-xl border border-slate-800 text-xs font-mono">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <span>Filter:</span>
          </div>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200 focus:outline-none focus:border-blue-500"
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
            className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200 focus:outline-none focus:border-blue-500"
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
            className="bg-slate-950 border border-slate-800 rounded px-3 py-1 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 w-full sm:w-48"
          />
        </div>
      </div>

      {/* Main Table */}
      {filteredRecords.length === 0 ? (
        <div className="text-center py-12 glass-panel rounded-xl text-slate-400 font-mono text-xs border border-slate-800/80 p-8 space-y-2">
          <Clock className="w-8 h-8 text-slate-600 mx-auto" />
          <p className="text-slate-300 font-semibold">No ledger records match the selected criteria</p>
          <p className="text-slate-500">
            {records.length === 0 
              ? 'Execute a buyer task in the Buyer Console to trigger genuine x402 micropayments.'
              : 'Try clearing your active filters to view all audit entries.'}
          </p>
        </div>
      ) : (
        <div className="glass-panel rounded-xl overflow-hidden border border-slate-800/90 shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-4 py-3.5">Timestamp</th>
                  <th className="px-4 py-3.5">Request ID</th>
                  <th className="px-4 py-3.5">Service</th>
                  <th className="px-4 py-3.5">Amount</th>
                  <th className="px-4 py-3.5">Protocol Settlement</th>
                  <th className="px-4 py-3.5">Latency</th>
                  <th className="px-4 py-3.5">Base Sepolia Tx</th>
                  <th className="px-3 py-3.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredRecords.map((r) => {
                  const isSelected = selectedRequestId === r.request_id;
                  const explorerLink = getExplorerUrl(r.tx_hash);

                  return (
                    <tr 
                      key={r.request_id} 
                      onClick={() => onSelectRecord && onSelectRecord(r)}
                      className={`hover:bg-slate-900/60 transition-colors cursor-pointer ${
                        isSelected ? 'bg-blue-900/20 border-l-2 border-l-blue-500' : ''
                      }`}
                    >
                      <td className="px-4 py-3.5 text-slate-400 whitespace-nowrap">
                        {new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>
                      <td className="px-4 py-3.5 font-semibold text-slate-200">
                        <span className="bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                          {r.request_id}
                        </span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="text-blue-400 hover:underline">{r.service_id}</span>
                      </td>
                      <td className="px-4 py-3.5 text-emerald-400 font-bold whitespace-nowrap">
                        {r.amount_paid} USDC
                      </td>
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="px-4 py-3.5 text-slate-400 whitespace-nowrap">
                        {r.latency_ms > 0 ? `${r.latency_ms.toFixed(1)} ms` : '—'}
                      </td>
                      <td className="px-4 py-3.5 text-slate-400 whitespace-nowrap">
                        {r.tx_hash ? (
                          <a
                            href={explorerLink || '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 underline font-mono text-[11px]"
                            title={r.tx_hash}
                          >
                            <span>{r.tx_hash.slice(0, 8)}...{r.tx_hash.slice(-6)}</span>
                            <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="px-3 py-3.5 text-right">
                        <ChevronRight className="w-4 h-4 text-slate-500 inline-block" />
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
