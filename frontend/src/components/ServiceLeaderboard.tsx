import React, { useState } from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { Trophy } from 'lucide-react';

interface ServiceLeaderboardProps {
  services: ServiceDefinition[];
  reputations: Record<string, ReputationMetrics>;
  onSelectService: (service: ServiceDefinition) => void;
}

export const ServiceLeaderboard: React.FC<ServiceLeaderboardProps> = ({
  services,
  reputations,
  onSelectService,
}) => {
  const [sortKey, setSortKey] = useState<'featured' | 'price' | 'latency' | 'success'>('featured');

  const sortedServices = [...services].sort((a, b) => {
    const repA = reputations[a.service_id];
    const repB = reputations[b.service_id];

    if (sortKey === 'price') {
      return parseFloat(a.price_usdc) - parseFloat(b.price_usdc);
    } else if (sortKey === 'latency') {
      const latA = repA?.median_latency_ms || 99999;
      const latB = repB?.median_latency_ms || 99999;
      return latA - latB;
    } else if (sortKey === 'success') {
      const succA = repA?.success_rate || 0;
      const succB = repB?.success_rate || 0;
      return succB - succA;
    }
    // Featured default: based on total calls then score
    const scoreA = (repA?.total_calls || 0) * 10 + (repA?.reputation_score || 0);
    const scoreB = (repB?.total_calls || 0) * 10 + (repB?.reputation_score || 0);
    return scoreB - scoreA;
  });

  return (
    <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center justify-center">
            <Trophy className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white font-sans">Service Leaderboard</h2>
            <p className="text-xs text-slate-400">Ranked performance across real registered x402 microservices</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 p-0.5 rounded-lg text-xs font-mono">
          <span className="text-slate-500 px-2 text-[11px]">Sort:</span>
          {(['featured', 'price', 'latency', 'success'] as const).map((key) => (
            <button
              key={key}
              onClick={() => setSortKey(key)}
              className={`px-2.5 py-1 rounded-md capitalize transition-colors ${
                sortKey === key 
                  ? 'bg-blue-600 text-white font-bold' 
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {key === 'price' ? 'Lowest Price' : key === 'latency' ? 'Fastest' : key === 'success' ? 'Success Rate' : 'Featured'}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[11px]">
            <tr>
              <th className="px-4 py-3 text-center w-12">Rank</th>
              <th className="px-4 py-3">Service Name & Endpoint</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Price / Call</th>
              <th className="px-4 py-3">Network</th>
              <th className="px-4 py-3">Reliability</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {sortedServices.map((svc, index) => {
              const rep = reputations[svc.service_id];
              const totalCalls = rep?.total_calls ?? 0;

              return (
                <tr key={svc.service_id} className="hover:bg-slate-900/50 transition-colors">
                  <td className="px-4 py-3.5 text-center">
                    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full font-bold ${
                      index === 0 
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' 
                        : index === 1
                        ? 'bg-slate-300/20 text-slate-200 border border-slate-400/40'
                        : index === 2
                        ? 'bg-amber-700/20 text-amber-500 border border-amber-700/40'
                        : 'text-slate-500'
                    }`}>
                      #{index + 1}
                    </span>
                  </td>

                  <td className="px-4 py-3.5">
                    <div className="font-bold text-white font-sans">{svc.name}</div>
                    <span className="text-[11px] text-slate-400 font-mono">{svc.endpoint_url}</span>
                  </td>

                  <td className="px-4 py-3.5">
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {svc.category}
                    </span>
                  </td>

                  <td className="px-4 py-3.5 text-emerald-400 font-bold">
                    {svc.price_usdc} USDC
                  </td>

                  <td className="px-4 py-3.5 text-slate-300">
                    <span className="text-[11px]">Base Sepolia</span>
                  </td>

                  <td className="px-4 py-3.5">
                    {totalCalls > 0 && rep ? (
                      <div>
                        <span className="text-emerald-400 font-semibold">{rep.success_rate.toFixed(0)}%</span>
                        {rep.median_latency_ms > 0 && (
                          <span className="text-slate-500 ml-1.5">({rep.median_latency_ms.toFixed(0)}ms)</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-slate-500 text-[11px]">Limited data</span>
                    )}
                  </td>

                  <td className="px-4 py-3.5 text-right">
                    <button
                      onClick={() => onSelectService(svc)}
                      className="px-3 py-1 rounded bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 font-semibold transition-colors"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
