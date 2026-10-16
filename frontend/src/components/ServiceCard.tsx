import React from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { Database, Globe, Cpu, ArrowUpRight, Zap, Clock, Activity } from 'lucide-react';

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
          badgeBg: 'bg-[#52758D]/15 text-[#52758D] border-[#52758D]/30',
          accent: 'text-[#52758D]',
        };
      case 'scraping':
        return {
          icon: Globe,
          badgeBg: 'bg-[#FF982E]/10 text-[#FF982E] border-[#FF982E]/20',
          accent: 'text-[#FF982E]',
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
          badgeBg: 'bg-[#FF982E]/10 text-[#FF982E] border-[#FF982E]/20',
          accent: 'text-[#FF982E]',
        };
    }
  };

  const theme = getCategoryTheme(service.category);
  const CategoryIcon = theme.icon;

  const totalCalls = reputation?.total_calls ?? 0;
  const latency = reputation && reputation.median_latency_ms > 0 ? `${reputation.median_latency_ms.toFixed(0)}ms` : null;

  return (
    <div className="rounded-xl p-5 flex flex-col justify-between border border-[#303133] hover:border-[#FF982E]/50 bg-[#191A1C] transition-all duration-200 group">
      <div>
        {/* Top Meta Line: Category Badge + Price */}
        <div className="flex items-center justify-between gap-2 mb-3.5">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1.5 text-[11px] uppercase font-mono px-2.5 py-1 rounded-md border font-semibold tracking-wide ${theme.badgeBg}`}>
              <CategoryIcon className="w-3 h-3" />
              {service.category}
            </span>
            <span className="text-[10px] font-mono text-[#777980] px-1.5 py-0.5 rounded bg-[#111214] border border-[#303133]">
              {service.service_id}
            </span>
          </div>

          <div className="text-right">
            <span className="text-sm font-mono text-[#FF982E] font-bold bg-[#FF982E]/10 px-2 py-0.5 rounded border border-[#FF982E]/20">
              {service.price_usdc} USDC
            </span>
          </div>
        </div>

        {/* Title & Description */}
        <div className="mb-4">
          <h3 
            className="text-base font-semibold text-[#F5F5F5] group-hover:text-[#FF982E] transition-colors flex items-center gap-1 cursor-pointer"
            onClick={() => onViewDetail && onViewDetail(service)}
          >
            <span>{service.name}</span>
            <ArrowUpRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-[#FF982E]" />
          </h3>
          <p className="text-xs text-[#A0A1A5] mt-1.5 leading-relaxed line-clamp-2">
            {service.description || 'Microservice participating in autonomous x402 payment workflows.'}
          </p>
        </div>

        {/* Endpoint Info */}
        <div className="bg-[#111214] rounded-lg p-2.5 border border-[#303133] font-mono text-[11px] space-y-1 mb-4">
          <div className="flex items-center justify-between text-[#A0A1A5]">
            <span>Route:</span>
            <span className="text-[#F5F5F5] truncate max-w-[200px]" title={service.endpoint_url}>
              {service.endpoint_url}
            </span>
          </div>
          <div className="flex items-center justify-between text-[#A0A1A5]">
            <span>Payee:</span>
            <span className="text-[#777980] font-mono text-[10px]" title={service.pay_to}>
              {service.pay_to ? `${service.pay_to.slice(0, 6)}...${service.pay_to.slice(-4)}` : 'Auto'}
            </span>
          </div>
        </div>
      </div>

      {/* Footer Metrics & Actions */}
      <div className="pt-3 border-t border-[#303133]">
        <div className="flex items-center justify-between text-xs font-mono mb-3">
          <div className="text-[#A0A1A5]">
            {totalCalls > 0 ? (
              <span className="flex items-center gap-1 text-[#F5F5F5]">
                <Activity className="w-3 h-3 text-[#777980]" />
                {totalCalls} calls
                {latency && <span className="text-[#777980] ml-1 font-mono">({latency})</span>}
              </span>
            ) : (
              <span className="text-[#777980] text-[11px]">No calls yet</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {latency && (
              <span className="flex items-center gap-1 text-[#777980] text-[11px]">
                <Clock className="w-3 h-3" />
                {latency}
              </span>
            )}
            {reputation && (
              <span className="text-[#58B779] font-bold text-xs">
                {reputation.reputation_score}%
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onViewDetail && (
            <button
              onClick={() => onViewDetail(service)}
              className="flex-1 py-1.5 px-3 rounded-lg bg-[#202123] hover:bg-[#303133] text-[#F5F5F5] text-xs font-medium transition-colors border border-[#303133]"
            >
              Inspect Specs
            </button>
          )}
          {onSelect && (
            <button
              onClick={() => onSelect(service)}
              className="flex-1 py-1.5 px-3 rounded-lg bg-[#FF982E] hover:bg-[#E98522] text-[#101112] text-xs font-bold transition-colors shadow-sm"
            >
              Use in Task
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
