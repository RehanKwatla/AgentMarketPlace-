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
    <div className="wallet-card rounded-lg p-4 flex flex-col justify-between border border-[rgba(255, 255, 255,0.18)] hover:border-[rgba(255, 255, 255,0.35)] transition-colors">
      <div>
        {/* Top: Category & Price */}
        <div className="flex items-center justify-between gap-2 mb-2.5">
          <span className="capitalize text-[11px] font-medium px-2 py-0.5 rounded bg-[#171717] text-[#A3A3A3] border border-[rgba(255, 255, 255,0.18)]">
            {service.category}
          </span>
          <span className="text-xs font-mono font-medium text-[#FFFFFF]">
            {service.price_usdc} USDC
          </span>
        </div>

        {/* Title & Description */}
        <div className="mb-3">
          <h3 
            className="text-sm font-semibold text-[#FAFAFA] hover:text-[#FFFFFF] transition-colors flex items-center gap-1 cursor-pointer"
            onClick={() => onViewDetail && onViewDetail(service)}
          >
            <span>{service.name}</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-[#A3A3A3]" />
          </h3>
          <p className="text-xs text-[#A3A3A3] mt-1 leading-relaxed line-clamp-2">
            {service.description || 'Verified microservice for autonomous x402 payment workflows.'}
          </p>
        </div>

        {/* Endpoint Info */}
        <div className="bg-[#0D0D0D] rounded p-2 border border-[rgba(255, 255, 255,0.14)] font-mono text-[11px] space-y-1 mb-3">
          <div className="flex items-center justify-between text-[#A3A3A3]">
            <span className="text-[#737373]">Route:</span>
            <span className="text-[#FAFAFA] truncate max-w-[180px]" title={service.endpoint_url}>
              {service.endpoint_url}
            </span>
          </div>
          <div className="flex items-center justify-between text-[#A3A3A3]">
            <span className="text-[#737373]">PayTo:</span>
            <span className="text-[#FFFFFF] text-[10px]" title={service.pay_to}>
              {service.pay_to ? `${service.pay_to.slice(0, 6)}...${service.pay_to.slice(-4)}` : 'Auto'}
            </span>
          </div>
        </div>
      </div>

      {/* Footer Metrics & Actions */}
      <div className="pt-2.5 border-t border-[rgba(255, 255, 255,0.14)]">
        <div className="flex items-center justify-between text-xs mb-2.5">
          <div className="text-[#A3A3A3] text-[11px]">
            {totalCalls > 0 ? (
              <span className="flex items-center gap-1 text-[#FAFAFA] font-mono">
                <Activity className="w-3 h-3 text-[#A3A3A3]" />
                {totalCalls} calls {latency && `(${latency})`}
              </span>
            ) : (
              <span className="text-[#737373]">Ready for calls</span>
            )}
          </div>
          <span className="text-[10px] font-mono text-[#A3A3A3]">Base Sepolia</span>
        </div>

        <div className="flex items-center gap-2">
          {onViewDetail && (
            <button
              onClick={() => onViewDetail(service)}
              className="flex-1 py-1 px-2.5 rounded bg-[#171717] hover:bg-[#1C1C1C] text-[#A3A3A3] hover:text-[#FAFAFA] text-xs font-medium border border-[rgba(255, 255, 255,0.2)] transition-colors cursor-pointer text-center"
            >
              Details
            </button>
          )}
          {onSelect && (
            <button
              onClick={() => onSelect(service)}
              className="flex-1 py-1 px-2.5 rounded bg-[#FFFFFF] hover:bg-[#E5E5E5] text-[#0A0A0A] text-xs font-medium transition-colors cursor-pointer text-center"
            >
              Use in Task
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
