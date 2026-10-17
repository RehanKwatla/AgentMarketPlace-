import React from 'react';
import { ServiceDefinition, ReputationMetrics, ServiceReputation } from '../types';
import { 
  ArrowUpRight, 
  Activity, 
  Database, 
  Globe, 
  Cpu, 
  Layers,
  ArrowRight
} from 'lucide-react';

interface ServiceCardProps {
  service: ServiceDefinition;
  reputation?: ServiceReputation | ReputationMetrics;
  onSelect?: (service: ServiceDefinition) => void;
  onViewDetail?: (service: ServiceDefinition) => void;
}

export const ServiceCard: React.FC<ServiceCardProps> = ({ 
  service, 
  reputation, 
  onSelect, 
  onViewDetail 
}) => {
  const effectiveRep = service.reputation || reputation;
  const totalCalls = effectiveRep?.total_calls ?? 0;
  const hasTelemetry = totalCalls > 0;
  const isEnabled = service.is_active && (service.enabled !== false);

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'data': return <Database className="w-3.5 h-3.5 text-[#586452]" />;
      case 'scraping': return <Globe className="w-3.5 h-3.5 text-[#A86E24]" />;
      case 'inference': return <Cpu className="w-3.5 h-3.5 text-[#7D292D]" />;
      default: return <Layers className="w-3.5 h-3.5 text-[#82786F]" />;
    }
  };

  // Truncate address helper
  const truncateAddress = (addr?: string) => {
    if (!addr) return 'Unknown Provider';
    if (addr.length <= 12) return addr;
    return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
  };

  // Extract top schema property names
  const inputProps = service.input_schema?.properties 
    ? Object.keys(service.input_schema.properties) 
    : [];
  const outputProps = service.output_schema?.properties 
    ? Object.keys(service.output_schema.properties) 
    : [];

  return (
    <div className="group relative rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] hover:border-[#7D292D]/50 hover:bg-[#FFFFFF] shadow-sm p-5 flex flex-col justify-between transition-all duration-200 space-y-4">
      {/* Top Header: Category, Status, Price */}
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#DED8CD]/60 border border-[#CFC7BB] text-[10px] uppercase font-mono tracking-wider text-[#586452] font-semibold">
              {getCategoryIcon(service.category)}
              <span>{service.category}</span>
            </span>

            <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border ${
              isEnabled 
                ? 'bg-[#E4EFE8] text-[#38865B] border-[#A8B3A1]/70' 
                : 'bg-[#F4ECEB] text-[#7D292D] border-[#CFC7BB]'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isEnabled ? 'bg-[#38865B]' : 'bg-[#7D292D]'}`} />
              <span>{isEnabled ? 'Active' : 'Disabled'}</span>
            </span>
          </div>

          <div className="text-right">
            <div className="flex items-baseline gap-1">
              <span className="text-sm font-bold font-mono text-[#7D292D]">
                {service.price_usdc}
              </span>
              <span className="text-[10px] font-mono text-[#82786F]">USDC</span>
            </div>
            <span className="text-[9px] font-mono text-[#82786F] block">per call</span>
          </div>
        </div>

        {/* Title & Description */}
        <div>
          <h3 
            onClick={() => onViewDetail && onViewDetail(service)}
            className="text-sm font-semibold text-[#241B19] group-hover:text-[#7D292D] transition-colors flex items-center gap-1 cursor-pointer font-sans"
          >
            <span className="truncate">{service.name}</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-[#82786F] group-hover:text-[#7D292D] transition-colors shrink-0" />
          </h3>
          <p className="text-xs text-[#82786F] mt-1 line-clamp-2 leading-relaxed font-sans">
            {service.description || 'Verified pay-per-call microservice endpoint on Base Sepolia.'}
          </p>
        </div>

        {/* Capabilities Badges */}
        {service.capabilities && service.capabilities.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {service.capabilities.slice(0, 3).map((cap, idx) => (
              <span 
                key={idx}
                className="px-1.5 py-0.5 rounded bg-[#DED8CD]/60 border border-[#CFC7BB] text-[10px] font-mono text-[#241B19]"
              >
                {cap}
              </span>
            ))}
            {service.capabilities.length > 3 && (
              <span className="text-[10px] font-mono text-[#82786F] self-center">
                +{service.capabilities.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Schema Summary */}
        {(inputProps.length > 0 || outputProps.length > 0) && (
          <div className="p-2.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] font-mono text-[10px] space-y-1">
            {inputProps.length > 0 && (
              <div className="flex items-center gap-1.5 text-[#82786F]">
                <span className="text-[#241B19] uppercase font-semibold">In:</span>
                <span className="truncate text-[#82786F]">{inputProps.join(', ')}</span>
              </div>
            )}
            {outputProps.length > 0 && (
              <div className="flex items-center gap-1.5 text-[#82786F]">
                <span className="text-[#241B19] uppercase font-semibold">Out:</span>
                <span className="truncate text-[#82786F]">{outputProps.join(', ')}</span>
              </div>
            )}
          </div>
        )}

        {/* Provider & Network Info */}
        <div className="pt-2 border-t border-[#CFC7BB]/60 flex items-center justify-between text-[10px] font-mono text-[#82786F]">
          <div>
            <span>Provider: </span>
            <span className="text-[#241B19]" title={service.pay_to}>
              {truncateAddress(service.pay_to)}
            </span>
          </div>
          <div>
            <span>ID: </span>
            <span className="text-[#241B19]">{service.service_id}</span>
          </div>
        </div>
      </div>

      {/* Footer: Telemetry & Actions */}
      <div className="space-y-3 pt-2">
        {/* Telemetry row */}
        <div className="flex items-center justify-between text-[11px] font-mono">
          {hasTelemetry ? (
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1 text-[#241B19]">
                <Activity className="w-3 h-3 text-[#38865B]" />
                <span>{effectiveRep?.total_calls} calls</span>
              </span>
              {effectiveRep?.median_latency_ms && (
                <span className="text-[#82786F]">
                  • {effectiveRep.median_latency_ms.toFixed(0)}ms
                </span>
              )}
            </div>
          ) : (
            <span className="text-[#82786F]">No call history yet</span>
          )}

          {hasTelemetry && effectiveRep?.reputation_score !== undefined ? (
            <span className="text-[#38865B] font-semibold">
              {effectiveRep.reputation_score}% score
            </span>
          ) : (
            <span className="text-[10px] text-[#82786F]">Base Sepolia</span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {onViewDetail && (
            <button
              type="button"
              onClick={() => onViewDetail(service)}
              className="flex-1 py-1.5 px-3 rounded-md bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono border border-[#CFC7BB] transition-colors cursor-pointer text-center shadow-xs"
            >
              View Details
            </button>
          )}

          {onSelect && (
            <button
              type="button"
              onClick={() => onSelect(service)}
              className="flex-1 py-1.5 px-3 rounded-md bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-semibold text-xs font-mono transition-colors flex items-center justify-center gap-1 cursor-pointer shadow-sm"
            >
              <span>Use Service</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
