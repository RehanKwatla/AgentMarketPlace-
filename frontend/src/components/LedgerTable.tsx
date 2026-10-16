import React from 'react';
import { LedgerRecord } from '../types';
import { StatusBadge } from './ReputationBadge';

interface LedgerTableProps {
  records: LedgerRecord[];
}

export const LedgerTable: React.FC<LedgerTableProps> = ({ records }) => {
  if (records.length === 0) {
    return (
      <div className="text-center py-12 glass-panel rounded-xl text-slate-500 font-mono text-sm">
        No payment transactions recorded yet. Submit a task to execute calls.
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-xl overflow-hidden border border-slate-800">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/90 text-slate-400 font-mono border-b border-slate-800 uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Request ID</th>
              <th className="px-4 py-3">Service</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Latency</th>
              <th className="px-4 py-3">Tx Hash</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {records.map((r) => (
              <tr key={r.request_id} className="hover:bg-slate-900/40 transition-colors">
                <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                  {new Date(r.timestamp).toLocaleTimeString()}
                </td>
                <td className="px-4 py-3 text-slate-300 font-semibold">{r.request_id}</td>
                <td className="px-4 py-3 text-blue-400">{r.service_id}</td>
                <td className="px-4 py-3 text-emerald-400">{r.amount_paid} USDC</td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <StatusBadge status={r.status} />
                </td>
                <td className="px-4 py-3 text-slate-400">{r.latency_ms.toFixed(1)} ms</td>
                <td className="px-4 py-3 text-slate-400">
                  {r.tx_hash ? (
                    <span className="text-blue-400 underline cursor-pointer" title={r.tx_hash}>
                      {r.tx_hash.slice(0, 10)}...
                    </span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
