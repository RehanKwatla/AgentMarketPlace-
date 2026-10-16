import React from 'react';
import { ReputationMetrics, ServiceDefinition } from '../types';

interface ReputationDashboardViewProps {
  reputations: Record<string, ReputationMetrics>;
  services: ServiceDefinition[];
  onSelectService?: (service: ServiceDefinition) => void;
}

export const ReputationDashboardView: React.FC<ReputationDashboardViewProps> = ({
  reputations,
  services,
  onSelectService,
}) => {
  const repList = Object.values(reputations);

  const totalCallsAcrossAll = repList.reduce((acc, r) => acc + (r.total_calls || 0), 0);
  const avgSuccessRate = repList.length > 0 
    ? (repList.reduce((acc, r) => acc + (r.success_rate || 0), 0) / repList.length).toFixed(1)
    : '0.0';

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <span className="text-slate-400 text-xs font-mono uppercase block">Active Sellers Monitored</span>
          <span className="text-2xl font-bold text-white font-mono mt-1 block">{services.length}</span>
          <span className="text-slate-500 text-[11px] font-mono mt-1 block">Data, Scraping & Inference</span>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <span className="text-slate-400 text-xs font-mono uppercase block">Total Autonomous Calls</span>
          <span className="text-2xl font-bold text-blue-400 font-mono mt-1 block">{totalCallsAcrossAll}</span>
          <span className="text-slate-500 text-[11px] font-mono mt-1 block">Live telemetry from ledger</span>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <span className="text-slate-400 text-xs font-mono uppercase block">Platform Health Score</span>
          <span className="text-2xl font-bold text-emerald-400 font-mono mt-1 block">{avgSuccessRate}%</span>
          <span className="text-slate-500 text-[11px] font-mono mt-1 block">Deterministic settlement rate</span>
        </div>
      </div>

      {/* Service Reputations Table */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-white">Seller Agent Reputation Directory</h3>
            <p className="text-xs text-slate-400">Metrics aggregated dynamically from persisted audit ledger transactions</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-4 py-3">Service Slug</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Price / Call</th>
                <th className="px-4 py-3">Total Calls</th>
                <th className="px-4 py-3">Success Rate</th>
                <th className="px-4 py-3">Median Latency</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {services.map((svc) => {
                const rep = reputations[svc.service_id];
                const totalCalls = rep?.total_calls ?? 0;
                const score = rep ? rep.reputation_score : 100;

                return (
                  <tr key={svc.service_id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="px-4 py-3.5 font-bold text-white">
                      <div>{svc.name}</div>
                      <span className="text-[10px] text-slate-500 font-normal">{svc.service_id}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {svc.category}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-emerald-400 font-bold">
                      {svc.price_usdc} USDC
                    </td>
                    <td className="px-4 py-3.5 text-slate-200">
                      {totalCalls}
                    </td>
                    <td className="px-4 py-3.5">
                      {totalCalls > 0 && rep ? (
                        <span className={`font-semibold ${rep.success_rate >= 90 ? 'text-emerald-400' : 'text-amber-400'}`}>
                          {rep.success_rate.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-slate-500 text-[11px]">No data yet</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-slate-300">
                      {totalCalls > 0 && rep && rep.median_latency_ms > 0 ? (
                        `${rep.median_latency_ms.toFixed(1)} ms`
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              score >= 80 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-rose-500'
                            }`}
                            style={{ width: `${Math.min(score, 100)}%` }}
                          />
                        </div>
                        <span className="font-bold text-slate-200">{score}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      {onSelectService && (
                        <button
                          onClick={() => onSelectService(svc)}
                          className="px-2.5 py-1 rounded bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 text-[11px] font-semibold transition-colors"
                        >
                          Details
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
