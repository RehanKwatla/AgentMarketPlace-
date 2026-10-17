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
    <div className="p-6 rounded-2xl border border-[#CFC7BB] bg-[#F7F4EE] space-y-5 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#7D292D] text-[#F7F4EE] flex items-center justify-center">
            <Trophy className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-[#241B19] font-serif">Service Leaderboard</h2>
            <p className="text-xs text-[#82786F]">Ranked performance across real registered x402 microservices</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 bg-[#DED8CD]/50 border border-[#CFC7BB] p-0.5 rounded-lg text-xs font-mono">
          <span className="text-[#82786F] px-2 text-[11px]">Sort:</span>
          {(['featured', 'price', 'latency', 'success'] as const).map((key) => (
            <button
              key={key}
              onClick={() => setSortKey(key)}
              className={`px-2.5 py-1 rounded-md capitalize transition-colors cursor-pointer ${
                sortKey === key 
                  ? 'bg-[#7D292D] text-[#F7F4EE] font-bold shadow-sm' 
                  : 'text-[#82786F] hover:text-[#241B19]'
              }`}
            >
              {key === 'price' ? 'Lowest Price' : key === 'latency' ? 'Fastest' : key === 'success' ? 'Success Rate' : 'Featured'}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-[#DED8CD]/40 text-[#82786F] border-b border-[#CFC7BB] uppercase tracking-wider text-[11px]">
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
          <tbody className="divide-y divide-[#CFC7BB]/50 text-[#241B19]">
            {sortedServices.map((svc, index) => {
              const rep = reputations[svc.service_id];
              const totalCalls = rep?.total_calls ?? 0;

              return (
                <tr key={svc.service_id} className="hover:bg-[#DED8CD]/20 transition-colors">
                  <td className="px-4 py-3.5 text-center">
                    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full font-bold text-xs ${
                      index === 0 
                        ? 'bg-[#7D292D] text-[#F7F4EE]' 
                        : index === 1
                        ? 'bg-[#DED8CD] text-[#241B19] border border-[#CFC7BB]'
                        : index === 2
                        ? 'bg-[#A8B3A1]/30 text-[#241B19] border border-[#A8B3A1]/50'
                        : 'text-[#82786F]'
                    }`}>
                      #{index + 1}
                    </span>
                  </td>

                  <td className="px-4 py-3.5">
                    <div className="font-bold text-[#241B19] font-sans">{svc.name}</div>
                    <span className="text-[11px] text-[#82786F] font-mono">{svc.endpoint_url}</span>
                  </td>

                  <td className="px-4 py-3.5">
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-[#DED8CD] text-[#241B19] border border-[#CFC7BB]">
                      {svc.category}
                    </span>
                  </td>

                  <td className="px-4 py-3.5 text-[#7D292D] font-bold">
                    {svc.price_usdc} USDC
                  </td>

                  <td className="px-4 py-3.5 text-[#82786F]">
                    <span className="text-[11px]">Base Sepolia</span>
                  </td>

                  <td className="px-4 py-3.5">
                    {totalCalls > 0 && rep ? (
                      <div>
                        <span className="text-[#38865B] font-semibold">{rep.success_rate.toFixed(0)}%</span>
                        {rep.median_latency_ms > 0 && (
                          <span className="text-[#82786F] ml-1.5">({rep.median_latency_ms.toFixed(0)}ms)</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-[#82786F] text-[11px]">Limited data</span>
                    )}
                  </td>

                  <td className="px-4 py-3.5 text-right">
                    <button
                      onClick={() => onSelectService(svc)}
                      className="px-3 py-1 rounded bg-[#FFFFFF] hover:bg-[#7D292D] hover:text-[#F7F4EE] text-[#241B19] border border-[#CFC7BB] font-medium transition-colors shadow-sm cursor-pointer"
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
