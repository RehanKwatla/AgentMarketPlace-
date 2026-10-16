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
          badge: 'text-[#36D6C8] bg-[rgba(54,214,200,0.12)] border-[rgba(54,214,200,0.25)]',
          icon: <Database className="w-3.5 h-3.5 text-[#36D6C8]" />
        };
      case 'scraping':
        return {
          badge: 'text-[#42C995] bg-[rgba(66,201,149,0.12)] border-[rgba(66,201,149,0.25)]',
          icon: <Globe className="w-3.5 h-3.5 text-[#42C995]" />
        };
      case 'inference':
        return {
          badge: 'text-[#53E3D6] bg-[rgba(18,74,69,0.3)] border-[rgba(54,214,200,0.3)]',
          icon: <Cpu className="w-3.5 h-3.5 text-[#53E3D6]" />
        };
      default:
        return {
          badge: 'text-[#A0AAA7] bg-[#141A19] border-[rgba(120,160,153,0.2)]',
          icon: <Sparkles className="w-3.5 h-3.5 text-[#A0AAA7]" />
        };
    }
  };

  return (
    <div className="bg-[#101514] rounded-xl overflow-hidden flex flex-col h-full border border-[rgba(120,160,153,0.16)]">
      {/* Header */}
      <div className="p-3.5 border-b border-[rgba(120,160,153,0.14)] flex items-center justify-between bg-[#0D1111]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-[#141A19] border border-[rgba(54,214,200,0.25)] flex items-center justify-center text-[#36D6C8]">
            <Trophy className="w-3.5 h-3.5" />
          </div>
          <div>
            <h3 className="font-semibold text-xs text-[#F4F7F6]">Services Leaderboard</h3>
            <p className="text-[11px] text-[#A0AAA7]">Ranked by reputation and verified volume</p>
          </div>
        </div>
      </div>

      {/* Rows */}
      <div className="divide-y divide-[rgba(120,160,153,0.10)] overflow-y-auto max-h-[360px] text-xs">
        {sorted.length === 0 ? (
          <div className="p-8 text-center text-[#6F7C78]">
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
                className="px-3.5 py-3 flex items-center justify-between hover:bg-[#141A19] cursor-pointer transition-colors group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className={`font-mono text-xs w-4 text-center shrink-0 ${index === 0 ? 'text-[#36D6C8] font-bold' : 'text-[#6F7C78]'}`}>
                    {index + 1}
                  </span>

                  <div className="w-7 h-7 rounded bg-[#0D1111] border border-[rgba(120,160,153,0.18)] flex items-center justify-center shrink-0">
                    {theme.icon}
                  </div>

                  <div className="truncate">
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium text-[#F4F7F6] group-hover:text-[#36D6C8] transition-colors truncate">
                        {svc.name}
                      </span>
                      {hasCalls && (
                        <span title="Verified calls processed" className="inline-flex">
                          <CheckCircle2 className="w-3 h-3 text-[#42C995] shrink-0" />
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-[#A0AAA7] font-mono truncate block mt-0.5">
                      {svc.price_usdc} USDC · {svc.endpoint_url}
                    </span>
                  </div>
                </div>

                <div className="shrink-0 ml-2">
                  <span className="text-[11px] capitalize px-2 py-0.5 rounded border border-[rgba(54,214,200,0.20)] bg-[rgba(54,214,200,0.08)] text-[#36D6C8] font-medium">
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
