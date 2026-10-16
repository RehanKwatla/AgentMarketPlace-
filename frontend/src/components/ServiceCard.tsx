import React from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { ArrowUpRight, Activity } from 'lucide-react';

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
  const totalCalls = reputation?.total_calls ?? 0;
  const latency = reputation && reputation.median_latency_ms > 0 ? `${reputation.median_latency_ms.toFixed(0)}ms` : null;

  return (
    <div className="wallet-card rounded-lg p-4 flex flex-col justify-between border border-[rgba(120,160,153,0.18)] hover:border-[rgba(54,214,200,0.35)] transition-colors">
      <div>
        {/* Top: Category & Price */}
        <div className="flex items-center justify-between gap-2 mb-2.5">
          <span className="capitalize text-[11px] font-medium px-2 py-0.5 rounded bg-[#161B1A] text-[#9BA5A2] border border-[rgba(120,160,153,0.18)]">
            {service.category}
          </span>
          <span className="text-xs font-mono font-medium text-[#36D6C8]">
            {service.price_usdc} USDC
          </span>
        </div>

        {/* Title & Description */}
        <div className="mb-3">
          <h3 
            className="text-sm font-semibold text-[#F4F7F6] hover:text-[#36D6C8] transition-colors flex items-center gap-1 cursor-pointer"
            onClick={() => onViewDetail && onViewDetail(service)}
          >
            <span>{service.name}</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-[#9BA5A2]" />
          </h3>
          <p className="text-xs text-[#9BA5A2] mt-1 leading-relaxed line-clamp-2">
            {service.description || 'Verified microservice for autonomous x402 payment workflows.'}
          </p>
        </div>

        {/* Endpoint Info */}
        <div className="bg-[#0D1010] rounded p-2 border border-[rgba(120,160,153,0.14)] font-mono text-[11px] space-y-1 mb-3">
          <div className="flex items-center justify-between text-[#9BA5A2]">
            <span className="text-[#6B7673]">Route:</span>
            <span className="text-[#F4F7F6] truncate max-w-[180px]" title={service.endpoint_url}>
              {service.endpoint_url}
            </span>
          </div>
          <div className="flex items-center justify-between text-[#9BA5A2]">
            <span className="text-[#6B7673]">PayTo:</span>
            <span className="text-[#36D6C8] text-[10px]" title={service.pay_to}>
              {service.pay_to ? `${service.pay_to.slice(0, 6)}...${service.pay_to.slice(-4)}` : 'Auto'}
            </span>
          </div>
        </div>
      </div>

      {/* Footer Metrics & Actions */}
      <div className="pt-2.5 border-t border-[rgba(120,160,153,0.14)]">
        <div className="flex items-center justify-between text-xs mb-2.5">
          <div className="text-[#9BA5A2] text-[11px]">
            {totalCalls > 0 ? (
              <span className="flex items-center gap-1 text-[#F4F7F6] font-mono">
                <Activity className="w-3 h-3 text-[#42C995]" />
                {totalCalls} calls {latency && `(${latency})`}
              </span>
            ) : (
              <span className="text-[#6B7673]">Ready for calls</span>
            )}
          </div>
          <span className="text-[10px] font-mono text-[#9BA5A2]">Base Sepolia</span>
        </div>

        <div className="flex items-center gap-2">
          {onViewDetail && (
            <button
              onClick={() => onViewDetail(service)}
              className="flex-1 py-1 px-2.5 rounded bg-[#161B1A] hover:bg-[#1C2221] text-[#9BA5A2] hover:text-[#F4F7F6] text-xs font-medium border border-[rgba(120,160,153,0.2)] transition-colors cursor-pointer text-center"
            >
              Details
            </button>
          )}
          {onSelect && (
            <button
              onClick={() => onSelect(service)}
              className="flex-1 py-1 px-2.5 rounded bg-[#36D6C8] hover:bg-[#45DFD2] text-[#0B0D0D] text-xs font-medium transition-colors cursor-pointer text-center"
            >
              Use in Task
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
