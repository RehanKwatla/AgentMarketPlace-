import React from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { Database, Globe, Cpu, ArrowUpRight, Zap } from 'lucide-react';

interface ServiceCardProps {
  service: ServiceDefinition;
  reputation?: ReputationMetrics;
  onSelect?: (service: ServiceDefinition) => void;
  onViewDetail?: (service: ServiceDefinition) => void;
}

export const ServiceCard: React.FC<ServiceCardProps> = ({ 
  service, 
  reputation, 
  onSelect, 
  onViewDetail 
}) => {
  const getCategoryTheme = (category: string) => {
    switch (category) {
      case 'data':
        return {
          icon: Database,
          badgeBg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
          accent: 'text-cyan-400',
        };
      case 'scraping':
        return {
          icon: Globe,
          badgeBg: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
          accent: 'text-amber-300',
        };
      case 'inference':
        return {
          icon: Cpu,
          badgeBg: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
          accent: 'text-purple-400',
        };
      default:
        return {
          icon: Zap,
          badgeBg: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
          accent: 'text-blue-400',
        };
    }
  };

  const theme = getCategoryTheme(service.category);
  const CategoryIcon = theme.icon;

  const totalCalls = reputation?.total_calls ?? 0;
  const latency = reputation && reputation.median_latency_ms > 0 ? `${reputation.median_latency_ms.toFixed(0)}ms` : null;

  return (
    <div className="glass-card rounded-xl p-5 flex flex-col justify-between border border-slate-800/80 hover:border-slate-700 bg-slate-900/60 transition-all duration-200 group">
      <div>
        {/* Top Meta Line: Category Badge + Price */}
        <div className="flex items-center justify-between gap-2 mb-3.5">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 text-[11px] uppercase font-mono px-2.5 py-1 rounded-md border font-semibold tracking-wide ${theme.badgeBg}`}>
              <CategoryIcon className="w-3 h-3" />
              {service.category}
            </span>
            <span className="text-[10px] font-mono text-slate-500 px-1.5 py-0.5 rounded bg-slate-800/60 border border-slate-700/50">
              {service.service_id}
            </span>
          </div>

          <div className="text-right">
            <span className="text-sm font-mono text-emerald-400 font-bold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
              {service.price_usdc} USDC
            </span>
          </div>
        </div>

        {/* Title & Description */}
        <div className="mb-4">
          <h3 
            className="text-base font-semibold text-white group-hover:text-blue-400 transition-colors flex items-center gap-1 cursor-pointer"
            onClick={() => onViewDetail && onViewDetail(service)}
          >
            <span>{service.name}</span>
            <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-blue-400" />
          </h3>
          <p className="text-xs text-slate-400 mt-1.5 leading-relaxed line-clamp-2">
            {service.description || 'Microservice participating in autonomous x402 payment workflows.'}
          </p>
        </div>

        {/* Endpoint Info */}
        <div className="bg-slate-950/70 rounded-lg p-2.5 border border-slate-800/60 font-mono text-[11px] space-y-1 mb-4">
          <div className="flex items-center justify-between text-slate-400">
            <span>Route:</span>
            <span className="text-slate-200 truncate max-w-[200px]" title={service.endpoint_url}>
              {service.endpoint_url}
            </span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Payee:</span>
            <span className="text-slate-400 font-mono text-[10px]" title={service.pay_to}>
              {service.pay_to ? `${service.pay_to.slice(0, 6)}...${service.pay_to.slice(-4)}` : 'Auto'}
            </span>
          </div>
        </div>
      </div>

      {/* Footer Metrics & Actions */}
      <div className="pt-3 border-t border-slate-800/80">
        <div className="flex items-center justify-between text-xs font-mono mb-3">
          <div className="text-slate-400">
            {totalCalls > 0 ? (
              <span>
                <span className="text-white font-bold">{totalCalls}</span> calls
                {latency && <span className="text-slate-500 ml-1">({latency})</span>}
              </span>
            ) : (
              <span className="text-slate-500 text-[11px]">No calls yet</span>
            )}
          </div>

          <div>
            {reputation && totalCalls > 0 ? (
              <span className="text-blue-400 font-semibold text-xs">
                {reputation.reputation_score}% score
              </span>
            ) : (
              <span className="text-slate-500 text-[11px]">Unrated</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onViewDetail && (
            <button
              onClick={() => onViewDetail(service)}
              className="flex-1 py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors border border-slate-700"
            >
              Inspect Specs
            </button>
          )}
          {onSelect && (
            <button
              onClick={() => onSelect(service)}
              className="flex-1 py-1.5 px-3 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 text-xs font-semibold transition-colors"
            >
              Use in Task
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
