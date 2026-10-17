import React, { useEffect, useState } from 'react';
import { ServiceDefinition, ReputationMetrics, ServiceReputation } from '../types';
import { 
  X, 
  Terminal, 
  Copy, 
  Check, 
  Database, 
  Globe, 
  Cpu, 
  ArrowRight,
  Layers
} from 'lucide-react';

interface ServiceDetailModalProps {
  service: ServiceDefinition | null;
  reputation?: ServiceReputation | ReputationMetrics;
  onClose: () => void;
  onUseInTask: (service: ServiceDefinition) => void;
}

export const ServiceDetailModal: React.FC<ServiceDetailModalProps> = ({
  service,
  reputation,
  onClose,
  onUseInTask,
}) => {
  const [copiedEndpoint, setCopiedEndpoint] = useState(false);
  const [copiedPayTo, setCopiedPayTo] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!service) return null;

  const copyText = (text: string, type: 'endpoint' | 'payTo') => {
    navigator.clipboard.writeText(text);
    if (type === 'endpoint') {
      setCopiedEndpoint(true);
      setTimeout(() => setCopiedEndpoint(false), 2000);
    } else {
      setCopiedPayTo(true);
      setTimeout(() => setCopiedPayTo(false), 2000);
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'data': return <Database className="w-4 h-4 text-cyan-400" />;
      case 'scraping': return <Globe className="w-4 h-4 text-amber-400" />;
      case 'inference': return <Cpu className="w-4 h-4 text-purple-400" />;
      default: return <Layers className="w-4 h-4 text-[#A3A3A3]" />;
    }
  };

  const effectiveRep = service.reputation || reputation;
  const totalCalls = effectiveRep?.total_calls ?? 0;
  const hasTelemetry = totalCalls > 0;
  const isEnabled = service.is_active && (service.enabled !== false);

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#241B19]/60 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl bg-[#F7F4EE] border border-[#CFC7BB] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] relative text-[#241B19]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#CFC7BB] bg-[#F7F4EE]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#DED8CD]/60 border border-[#CFC7BB] flex items-center justify-center text-[#7D292D]">
              {getCategoryIcon(service.category)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-serif font-bold text-[#241B19]">{service.name}</h2>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded border border-[#CFC7BB] bg-[#DED8CD]/60 text-[#586452] font-semibold">
                  {service.category}
                </span>
                <span className={`inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded border ${
                  isEnabled 
                    ? 'bg-[#E4EFE8] text-[#38865B] border-[#A8B3A1]/70' 
                    : 'bg-[#F4ECEB] text-[#7D292D] border-[#CFC7BB]'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${isEnabled ? 'bg-[#38865B]' : 'bg-[#7D292D]'}`} />
                  <span>{isEnabled ? 'Enabled' : 'Disabled'}</span>
                </span>
              </div>
              <p className="text-[11px] text-[#82786F] font-mono mt-0.5">ID: {service.service_id}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-md text-[#82786F] hover:text-[#241B19] hover:bg-[#DED8CD]/60 transition-colors cursor-pointer"
            title="Close (Esc)"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs">
          
          {/* Price & Network Specs */}
          <div className="bg-[#FFFFFF] p-4 rounded-lg border border-[#CFC7BB] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shadow-xs">
            <div>
              <span className="text-[11px] font-mono text-[#82786F] block uppercase tracking-wider font-semibold">
                Price per Call (x402 Protocol)
              </span>
              <div className="flex items-baseline gap-1.5 mt-1">
                <span className="text-2xl font-bold font-mono text-[#7D292D]">{service.price_usdc}</span>
                <span className="text-xs font-mono text-[#82786F]">USDC</span>
              </div>
              <span className="text-[11px] text-[#82786F] font-mono block mt-0.5">
                ({(service.price_atomic || service.price_base_units || 0).toLocaleString()} atomic base units)
              </span>
            </div>

            <div className="sm:text-right space-y-1">
              <span className="text-[11px] font-mono text-[#82786F] block uppercase tracking-wider font-semibold">
                Settlement Network
              </span>
              <div className="text-xs font-mono text-[#241B19] font-semibold">{service.network}</div>
              <div className="text-[11px] font-mono text-[#82786F]">Base Sepolia (eip155:84532)</div>
            </div>
          </div>

          {/* Description */}
          <div>
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#82786F] mb-1.5">
              Service Overview
            </h3>
            <div className="bg-[#FFFFFF] p-3.5 rounded-lg border border-[#CFC7BB] text-xs text-[#241B19] leading-relaxed shadow-xs">
              {service.description || 'Verified microservice provider configured for autonomous x402 payment execution.'}
            </div>
          </div>

          {/* Capabilities */}
          {service.capabilities && service.capabilities.length > 0 && (
            <div>
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#82786F] mb-1.5">
                Advertised Capabilities
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {service.capabilities.map((cap, i) => (
                  <span 
                    key={i}
                    className="px-2 py-0.5 rounded bg-[#DED8CD]/60 border border-[#CFC7BB] text-[11px] font-mono text-[#241B19]"
                  >
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Performance & Reputation */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#82786F]">
                Telemetry & Reputation
              </h3>
              <span className="text-[10px] font-mono text-[#82786F]">
                {hasTelemetry ? 'Real records indexed' : 'Awaiting execution calls'}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="bg-[#FFFFFF] p-3 rounded-lg border border-[#CFC7BB] shadow-xs">
                <span className="text-[#82786F] text-[10px] font-mono uppercase tracking-wider block">Total Recorded Calls</span>
                <span className="text-sm font-semibold font-mono text-[#241B19] mt-1 block">
                  {totalCalls}
                </span>
                <span className="text-[10px] text-[#82786F] font-mono">
                  {effectiveRep?.successful_calls ?? 0} successful
                </span>
              </div>

              <div className="bg-[#FFFFFF] p-3 rounded-lg border border-[#CFC7BB] shadow-xs">
                <span className="text-[#82786F] text-[10px] font-mono uppercase tracking-wider block">Median Latency</span>
                <span className="text-sm font-semibold font-mono text-[#241B19] mt-1 block">
                  {hasTelemetry && effectiveRep?.median_latency_ms 
                    ? `${effectiveRep.median_latency_ms.toFixed(0)}ms` 
                    : '—'}
                </span>
                <span className="text-[10px] text-[#82786F] font-mono">
                  {hasTelemetry && effectiveRep?.latency_p95_ms ? `p95: ${effectiveRep.latency_p95_ms}ms` : 'No telemetry yet'}
                </span>
              </div>

              <div className="bg-[#FFFFFF] p-3 rounded-lg border border-[#CFC7BB] shadow-xs">
                <span className="text-[#82786F] text-[10px] font-mono uppercase tracking-wider block">Reputation Score</span>
                <span className="text-sm font-semibold font-mono mt-1 block">
                  {hasTelemetry && effectiveRep?.reputation_score !== undefined
                    ? <span className="text-[#38865B]">{effectiveRep.reputation_score}%</span>
                    : <span className="text-[#82786F]">Unavailable</span>}
                </span>
                <span className="text-[10px] text-[#82786F] font-mono">
                  {hasTelemetry && effectiveRep?.success_rate !== undefined 
                    ? `${(effectiveRep.success_rate * 100).toFixed(0)}% success rate` 
                    : 'Requires calls'}
                </span>
              </div>
            </div>
          </div>

          {/* Technical Details: Endpoint & PayTo */}
          <div className="space-y-3">
            <div>
              <span className="text-[11px] font-mono text-[#82786F] uppercase tracking-wider block mb-1">
                Microservice Endpoint Route
              </span>
              <div className="flex items-center justify-between gap-2 bg-[#FFFFFF] p-2.5 rounded-lg border border-[#CFC7BB] shadow-xs">
                <span className="text-[#241B19] font-mono text-[11px] truncate">{service.endpoint_url}</span>
                <button
                  onClick={() => copyText(service.endpoint_url, 'endpoint')}
                  className="p-1.5 rounded text-[#82786F] hover:text-[#7D292D] hover:bg-[#DED8CD]/60 transition-colors shrink-0 cursor-pointer"
                  title="Copy URL"
                >
                  {copiedEndpoint ? <Check className="w-3.5 h-3.5 text-[#38865B]" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            <div>
              <span className="text-[11px] font-mono text-[#82786F] uppercase tracking-wider block mb-1">
                PayTo Recipient Address (ERC-20 Settlement)
              </span>
              <div className="flex items-center justify-between gap-2 bg-[#FFFFFF] p-2.5 rounded-lg border border-[#CFC7BB] shadow-xs">
                <span className="text-[#241B19] font-mono text-[11px] truncate">{service.pay_to}</span>
                <button
                  onClick={() => copyText(service.pay_to, 'payTo')}
                  className="p-1.5 rounded text-[#82786F] hover:text-[#7D292D] hover:bg-[#DED8CD]/60 transition-colors shrink-0 cursor-pointer"
                  title="Copy PayTo Address"
                >
                  {copiedPayTo ? <Check className="w-3.5 h-3.5 text-[#38865B]" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>
          </div>

          {/* Schemas */}
          <div className="space-y-3">
            <div>
              <div className="flex items-center gap-1.5 text-[11px] font-mono text-[#82786F] mb-1">
                <Terminal className="w-3 h-3 text-[#241B19]" />
                <span>Input JSON Schema</span>
              </div>
              <pre className="bg-[#241B19] text-[#F7F4EE] p-3 rounded-lg border border-[#CFC7BB] text-[11px] overflow-x-auto max-h-36 font-mono leading-relaxed">
                {JSON.stringify(service.input_schema, null, 2)}
              </pre>
            </div>

            <div>
              <div className="flex items-center gap-1.5 text-[11px] font-mono text-[#82786F] mb-1">
                <Terminal className="w-3 h-3 text-[#241B19]" />
                <span>Output JSON Schema</span>
              </div>
              <pre className="bg-[#241B19] text-[#F7F4EE] p-3 rounded-lg border border-[#CFC7BB] text-[11px] overflow-x-auto max-h-36 font-mono leading-relaxed">
                {JSON.stringify(service.output_schema, null, 2)}
              </pre>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-[#CFC7BB] bg-[#F7F4EE] flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-md bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono transition-colors border border-[#CFC7BB] cursor-pointer shadow-xs"
          >
            Close
          </button>

          <button
            type="button"
            onClick={() => {
              onUseInTask(service);
              onClose();
            }}
            className="px-4 py-2 rounded-md bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-semibold text-xs font-mono transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm"
          >
            <span>Use in Buyer Task</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
