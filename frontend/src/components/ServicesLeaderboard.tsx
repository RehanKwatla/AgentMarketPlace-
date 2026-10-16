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

  const getCategoryTheme = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'data':
        return {
          badge: 'text-[#FFFFFF] bg-[rgba(255, 255, 255,0.12)] border-[rgba(255, 255, 255,0.25)]',
          icon: <Database className="w-3.5 h-3.5 text-[#FFFFFF]" />
        };
      case 'scraping':
        return {
          badge: 'text-[#A3A3A3] bg-[rgba(163, 163, 163,0.12)] border-[rgba(163, 163, 163,0.25)]',
          icon: <Globe className="w-3.5 h-3.5 text-[#A3A3A3]" />
        };
      case 'inference':
        return {
          badge: 'text-[#D4D4D4] bg-[rgba(38, 38, 38,0.3)] border-[rgba(255, 255, 255,0.3)]',
          icon: <Cpu className="w-3.5 h-3.5 text-[#D4D4D4]" />
        };
      default:
        return {
          badge: 'text-[#A3A3A3] bg-[#141414] border-[rgba(255, 255, 255,0.2)]',
          icon: <Sparkles className="w-3.5 h-3.5 text-[#A3A3A3]" />
        };
    }
  };

  return (
    <div className="bg-[#111111] rounded-xl overflow-hidden flex flex-col h-full border border-[rgba(255, 255, 255,0.16)]">
      {/* Header */}
      <div className="p-3.5 border-b border-[rgba(255, 255, 255,0.14)] flex items-center justify-between bg-[#0D0D0D]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-[#141414] border border-[rgba(255, 255, 255,0.25)] flex items-center justify-center text-[#FFFFFF]">
            <Trophy className="w-3.5 h-3.5" />
          </div>
          <div>
            <h3 className="font-semibold text-xs text-[#FAFAFA]">Services Leaderboard</h3>
            <p className="text-[11px] text-[#A3A3A3]">Ranked by reputation and verified volume</p>
          </div>
        </div>
      </div>

      {/* Rows */}
      <div className="divide-y divide-[rgba(255, 255, 255,0.10)] overflow-y-auto max-h-[360px] text-xs">
        {sorted.length === 0 ? (
          <div className="p-8 text-center text-[#737373]">
            No services registered yet.
          </div>
        ) : (
          sorted.map((svc, index) => {
            const rep = reputations[svc.service_id];
            const hasCalls = (rep?.total_calls || 0) > 0;
            const theme = getCategoryTheme(svc.category);

            return (
              <div
                key={svc.service_id}
                onClick={() => onSelectService(svc)}
                className="px-3.5 py-3 flex items-center justify-between hover:bg-[#141414] cursor-pointer transition-colors group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className={`font-mono text-xs w-4 text-center shrink-0 ${index === 0 ? 'text-[#FFFFFF] font-bold' : 'text-[#737373]'}`}>
                    {index + 1}
                  </span>

                  <div className="w-7 h-7 rounded bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.18)] flex items-center justify-center shrink-0">
                    {theme.icon}
                  </div>

                  <div className="truncate">
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium text-[#FAFAFA] group-hover:text-[#FFFFFF] transition-colors truncate">
                        {svc.name}
                      </span>
                      {hasCalls && (
                        <span title="Verified calls processed" className="inline-flex">
                          <CheckCircle2 className="w-3 h-3 text-[#A3A3A3] shrink-0" />
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-[#A3A3A3] font-mono truncate block mt-0.5">
                      {svc.price_usdc} USDC · {svc.endpoint_url}
                    </span>
                  </div>
                </div>

                <div className="shrink-0 ml-2">
                  <span className="text-[11px] capitalize px-2 py-0.5 rounded border border-[rgba(255, 255, 255,0.20)] bg-[rgba(255, 255, 255,0.08)] text-[#FFFFFF] font-medium">
                    {svc.category}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
