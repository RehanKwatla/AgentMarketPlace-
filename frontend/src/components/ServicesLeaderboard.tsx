import React from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { Trophy, CheckCircle2, Sparkles, Database, Globe, Cpu } from 'lucide-react';

interface ServicesLeaderboardProps {
  services: ServiceDefinition[];
  reputations: Record<string, ReputationMetrics>;
  onSelectService: (service: ServiceDefinition) => void;
}

export const ServicesLeaderboard: React.FC<ServicesLeaderboardProps> = ({
  services,
  reputations,
  onSelectService
}) => {
  const sorted = [...services].sort((a, b) => {
    const repA = reputations[a.service_id]?.reputation_score || 0;
    const repB = reputations[b.service_id]?.reputation_score || 0;
    return repB - repA;
  });

  const getCategoryColor = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'data':
        return 'text-[#FF982E] bg-[#FF982E]/10 border-[#FF982E]/20';
      case 'scraping':
        return 'text-[#52758D] bg-[#52758D]/10 border-[#52758D]/20';
      case 'inference':
        return 'text-[#58B779] bg-[#58B779]/10 border-[#58B779]/20';
      default:
        return 'text-[#96989D] bg-[#1D1E20] border-[#303133]';
    }
  };

  const getCategoryIcon = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'data': return <Database className="w-3.5 h-3.5 text-[#FF982E]" />;
      case 'scraping': return <Globe className="w-3.5 h-3.5 text-[#52758D]" />;
      case 'inference': return <Cpu className="w-3.5 h-3.5 text-[#58B779]" />;
      default: return <Sparkles className="w-3.5 h-3.5 text-[#96989D]" />;
    }
  };

  return (
    <div className="bg-[#171819] border border-[#303133] rounded-lg overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="p-3.5 border-b border-[#303133] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-[#FF982E]" />
          <div>
            <h3 className="font-bold text-sm text-[#F5F5F5] font-sans">Services Leaderboard</h3>
            <p className="text-[11px] text-[#96989D] font-mono leading-none mt-0.5">Explore high-performing services</p>
          </div>
        </div>
      </div>

      {/* Rows */}
      <div className="divide-y divide-[#303133] overflow-y-auto max-h-[360px] text-xs font-mono">
        {sorted.map((svc, index) => {
          const rep = reputations[svc.service_id];
          const hasCalls = (rep?.total_calls || 0) > 0;

          return (
            <div
              key={svc.service_id}
              onClick={() => onSelectService(svc)}
              className="px-3.5 py-2.5 flex items-center justify-between hover:bg-[#1D1E20] cursor-pointer transition-colors group"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-[#96989D] font-bold w-4 text-center shrink-0">
                  {index + 1}
                </span>

                <div className="w-6 h-6 rounded bg-[#101112] border border-[#303133] flex items-center justify-center shrink-0">
                  {getCategoryIcon(svc.category)}
                </div>

                <div className="truncate">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-[#F5F5F5] group-hover:text-[#FF982E] transition-colors truncate">
                      {svc.name}
                    </span>
                    {hasCalls && (
                      <span title="Verified Calls" className="inline-flex">
                        <CheckCircle2 className="w-3 h-3 text-[#58B779] shrink-0" />
                      </span>
                    )}
                    {index === 0 && (
                      <span className="text-[9px] px-1 py-0.2 rounded bg-[#FF982E]/20 text-[#FF982E] font-bold">
                        TOP
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-[#96989D] truncate block">
                    {svc.price_usdc} USDC · {svc.endpoint_url}
                  </span>
                </div>
              </div>

              <div className="shrink-0 ml-2">
                <span className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded border ${getCategoryColor(svc.category)}`}>
                  {svc.category}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
