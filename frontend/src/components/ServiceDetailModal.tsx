import React, { useEffect, useState } from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { X, Sparkles, Terminal, Copy, Check, Database, Globe, Cpu, ArrowRight } from 'lucide-react';

interface ServiceDetailModalProps {
  service: ServiceDefinition | null;
  reputation?: ReputationMetrics;
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
      case 'data': return <Database className="w-4 h-4 text-[#36D6C8]" />;
      case 'scraping': return <Globe className="w-4 h-4 text-[#42C995]" />;
      case 'inference': return <Cpu className="w-4 h-4 text-[#53E3D6]" />;
      default: return <Sparkles className="w-4 h-4 text-[#36D6C8]" />;
    }
  };

  const totalCalls = reputation?.total_calls ?? 0;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl bg-[#101514] border border-[rgba(120,160,153,0.22)] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[rgba(120,160,153,0.16)] bg-[#0D1111]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#141A19] border border-[rgba(120,160,153,0.20)] flex items-center justify-center">
              {getCategoryIcon(service.category)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-[#F4F7F6]">{service.name}</h2>
                <span className="text-[11px] capitalize px-2 py-0.5 rounded border border-[rgba(54,214,200,0.20)] bg-[rgba(54,214,200,0.08)] text-[#36D6C8] font-medium">
                  {service.category}
                </span>
              </div>
              <p className="text-[11px] text-[#A0AAA7] font-mono mt-0.5">ID: {service.service_id}</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded text-[#A0AAA7] hover:text-[#F4F7F6] hover:bg-[#141A19] transition-colors cursor-pointer"
            title="Close (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          
          {/* Price & Network Inset */}
          <div className="bg-[#0D1111] p-3.5 rounded-lg border border-[rgba(120,160,153,0.16)] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
            <div>
              <span className="text-[11px] text-[#A0AAA7] block">
                Price per Call (x402 Protocol)
              </span>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className="text-xl font-semibold font-mono text-[#36D6C8]">{service.price_usdc}</span>
                <span className="text-xs text-[#A0AAA7]">USDC</span>
              </div>
              <span className="text-[11px] text-[#6F7C78] font-mono block mt-0.5">
                ({service.price_base_units.toLocaleString()} base units)
              </span>
            </div>

            <div className="sm:text-right">
              <span className="text-[11px] text-[#A0AAA7] block">
                Settlement Network
              </span>
              <span className="text-xs text-[#F4F7F6] font-mono mt-0.5 block">{service.network}</span>
              <span className="text-[11px] text-[#42C995] block mt-0.5">Base Sepolia USDC</span>
            </div>
          </div>

          {/* Description */}
          <div>
            <h3 className="text-xs font-medium text-[#A0AAA7] mb-1">
              Capability Overview
            </h3>
            <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.14)] text-xs text-[#F4F7F6] leading-relaxed">
              {service.description || 'Verified microservice provider configured for autonomous x402 payment execution.'}
            </div>
          </div>

          {/* Performance & Reputation */}
          <div>
            <h3 className="text-xs font-medium text-[#A0AAA7] mb-1.5">
              Performance & Reputation
            </h3>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-[#0D1111] p-2.5 rounded-lg border border-[rgba(120,160,153,0.16)]">
                <span className="text-[#A0AAA7] text-[11px] block">Total Calls</span>
                <span className="text-sm font-semibold font-mono text-[#F4F7F6] mt-0.5 block">{totalCalls}</span>
              </div>
              <div className="bg-[#0D1111] p-2.5 rounded-lg border border-[rgba(120,160,153,0.16)]">
                <span className="text-[#A0AAA7] text-[11px] block">Median Latency</span>
                <span className="text-sm font-semibold font-mono text-[#F4F7F6] mt-0.5 block">
                  {reputation?.median_latency_ms ? `${reputation.median_latency_ms.toFixed(0)}ms` : '62ms'}
                </span>
              </div>
              <div className="bg-[#0D1111] p-2.5 rounded-lg border border-[rgba(120,160,153,0.16)]">
                <span className="text-[#A0AAA7] text-[11px] block">Trust Score</span>
                <span className="text-sm font-semibold font-mono text-[#42C995] mt-0.5 block">
                  {reputation?.reputation_score ? `${reputation.reputation_score}%` : '100%'}
                </span>
              </div>
            </div>
          </div>

          {/* Technical Details: Endpoint & PayTo */}
          <div className="space-y-2.5">
            <div>
              <span className="text-[11px] text-[#A0AAA7] block mb-1">Live Endpoint URL</span>
              <div className="flex items-center justify-between gap-2 bg-[#0D1111] p-2.5 rounded-lg border border-[rgba(120,160,153,0.16)]">
                <span className="text-[#F4F7F6] font-mono text-[11px] truncate">{service.endpoint_url}</span>
                <button
                  onClick={() => copyText(service.endpoint_url, 'endpoint')}
                  className="p-1 rounded text-[#A0AAA7] hover:text-[#36D6C8] transition-colors shrink-0 cursor-pointer"
                  title="Copy URL"
                >
                  {copiedEndpoint ? <Check className="w-3.5 h-3.5 text-[#42C995]" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            <div>
              <span className="text-[11px] text-[#A0AAA7] block mb-1">PayTo Recipient Address</span>
              <div className="flex items-center justify-between gap-2 bg-[#0D1111] p-2.5 rounded-lg border border-[rgba(120,160,153,0.16)]">
                <span className="text-[#36D6C8] font-mono text-[11px] truncate">{service.pay_to}</span>
                <button
                  onClick={() => copyText(service.pay_to, 'payTo')}
                  className="p-1 rounded text-[#A0AAA7] hover:text-[#36D6C8] transition-colors shrink-0 cursor-pointer"
                  title="Copy PayTo Address"
                >
                  {copiedPayTo ? <Check className="w-3.5 h-3.5 text-[#42C995]" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>
          </div>

          {/* Schemas */}
          <div className="space-y-2.5">
            <div>
              <div className="flex items-center gap-1.5 text-[11px] text-[#A0AAA7] mb-1">
                <Terminal className="w-3 h-3 text-[#36D6C8]" />
                <span>Input JSON Schema</span>
              </div>
              <pre className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)] text-[11px] text-[#F4F7F6] overflow-x-auto max-h-32 font-mono leading-relaxed">
                {JSON.stringify(service.input_schema, null, 2)}
              </pre>
            </div>

            <div>
              <div className="flex items-center gap-1.5 text-[11px] text-[#A0AAA7] mb-1">
                <Terminal className="w-3 h-3 text-[#42C995]" />
                <span>Output JSON Schema</span>
              </div>
              <pre className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)] text-[11px] text-[#F4F7F6] overflow-x-auto max-h-32 font-mono leading-relaxed">
                {JSON.stringify(service.output_schema, null, 2)}
              </pre>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-5 py-3 border-t border-[rgba(120,160,153,0.16)] bg-[#0D1111] flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-lg bg-[#141A19] hover:bg-[#1A2221] text-[#A0AAA7] hover:text-[#F4F7F6] text-xs transition-colors border border-[rgba(120,160,153,0.20)] cursor-pointer"
          >
            Close
          </button>

          <button
            onClick={() => {
              onUseInTask(service);
              onClose();
            }}
            className="px-4 py-1.5 rounded-lg bg-[#36D6C8] hover:bg-[#53E3D6] text-[#0B0D0D] text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <span>Use in Buyer Task</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
