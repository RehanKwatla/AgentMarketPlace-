import React, { useEffect } from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { X, Sparkles, Terminal, Copy, Check, ShieldCheck, Database, Globe, Cpu } from 'lucide-react';

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
  const [copiedEndpoint, setCopiedEndpoint] = React.useState(false);
  const [copiedPayTo, setCopiedPayTo] = React.useState(false);

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
      case 'data': return <Database className="w-4 h-4 text-[#FF982E]" />;
      case 'scraping': return <Globe className="w-4 h-4 text-[#52758D]" />;
      case 'inference': return <Cpu className="w-4 h-4 text-[#58B779]" />;
      default: return <Sparkles className="w-4 h-4 text-[#FF982E]" />;
    }
  };

  const totalCalls = reputation?.total_calls ?? 0;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl bg-[#191A1C] border border-[#303133] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#303133] bg-[#171819]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#202123] border border-[#303133] flex items-center justify-center">
              {getCategoryIcon(service.category)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-[#F5F5F5] font-sans">{service.name}</h2>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-[#111214] border border-[#303133] text-[#A0A1A5]">
                  {service.category}
                </span>
              </div>
              <p className="text-[11px] text-[#777980] font-mono">ID: {service.service_id}</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#777980] hover:text-[#FF982E] hover:bg-[#202123] transition-colors"
            title="Close (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs font-mono">
          
          {/* Price & Network Inset */}
          <div className="bg-[#202123] p-4 rounded-lg border border-[#303133] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
              <span className="text-[10px] text-[#777980] uppercase block">Price per Call (x402 Protocol)</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-2xl font-bold font-mono text-[#FF982E]">{service.price_usdc}</span>
                <span className="text-xs text-[#A0A1A5] font-bold">USDC</span>
              </div>
              <span className="text-[10px] text-[#777980] block mt-0.5">
                ({service.price_base_units.toLocaleString()} integer base units)
              </span>
            </div>

            <div className="sm:text-right">
              <span className="text-[10px] text-[#777980] uppercase block">Settlement Network</span>
              <span className="text-xs text-[#F5F5F5] font-semibold mt-0.5 block">{service.network}</span>
              <span className="text-[10px] text-[#FF982E] block mt-0.5">Base Sepolia USDC</span>
            </div>
          </div>

          {/* Capability Overview */}
          <div>
            <h4 className="text-[11px] text-[#777980] uppercase font-semibold mb-1.5 font-mono">
              Capability Overview
            </h4>
            <div className="bg-[#111214] p-3.5 rounded-lg border border-[#303133] text-xs text-[#A0A1A5] leading-relaxed font-sans">
              {service.description || 'Microservice participating in autonomous x402 payment workflows.'}
            </div>
          </div>

          {/* Historical Reputation & Telemetry */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <h4 className="text-[11px] text-[#777980] uppercase font-semibold font-mono">
                Historical Telemetry & Reliability
              </h4>
              {totalCalls > 0 && reputation ? (
                <span className="text-[10px] text-[#58B779] font-mono flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" />
                  <span>{reputation.reputation_score}% Reliability Score</span>
                </span>
              ) : (
                <span className="text-[10px] text-[#777980] font-mono">Unrated / Staged</span>
              )}
            </div>

            {totalCalls > 0 && reputation ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="bg-[#202123] p-2.5 rounded-lg border border-[#303133] text-center">
                  <span className="text-[10px] text-[#777980] block uppercase">Total Calls</span>
                  <span className="text-sm font-bold text-[#F5F5F5] mt-0.5 block">{reputation.total_calls}</span>
                </div>
                <div className="bg-[#202123] p-2.5 rounded-lg border border-[#303133] text-center">
                  <span className="text-[10px] text-[#777980] block uppercase">Success Rate</span>
                  <span className="text-sm font-bold text-[#58B779] mt-0.5 block">{reputation.success_rate.toFixed(1)}%</span>
                </div>
                <div className="bg-[#202123] p-2.5 rounded-lg border border-[#303133] text-center">
                  <span className="text-[10px] text-[#777980] block uppercase">Median Latency</span>
                  <span className="text-sm font-bold text-[#A0A1A5] mt-0.5 block">{reputation.median_latency_ms.toFixed(0)} ms</span>
                </div>
                <div className="bg-[#202123] p-2.5 rounded-lg border border-[#303133] text-center">
                  <span className="text-[10px] text-[#777980] block uppercase">Failures</span>
                  <span className="text-sm font-bold text-[#E15D52] mt-0.5 block">{reputation.failure_counts}</span>
                </div>
              </div>
            ) : (
              <div className="bg-[#111214] p-3 rounded-lg border border-[#303133] text-[#777980] text-center text-[11px]">
                Not enough historical calls to establish reliability confidence.
              </div>
            )}
          </div>

          {/* Integration Specs */}
          <div className="space-y-3">
            <h4 className="text-[11px] text-[#777980] uppercase font-semibold font-mono">
              Integration Specifications
            </h4>
            
            <div className="bg-[#111214] p-3.5 rounded-lg border border-[#303133] space-y-2.5">
              <div className="flex items-center justify-between text-xs gap-2">
                <span className="text-[#777980] shrink-0">Endpoint URL:</span>
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="text-[#F5F5F5] font-mono truncate">{service.endpoint_url}</span>
                  <button
                    onClick={() => copyText(service.endpoint_url, 'endpoint')}
                    className="p-1 rounded text-[#777980] hover:text-[#FF982E] transition-colors shrink-0"
                    title="Copy URL"
                  >
                    {copiedEndpoint ? <Check className="w-3.5 h-3.5 text-[#58B779]" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs gap-2">
                <span className="text-[#777980] shrink-0">Recipient PayTo:</span>
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="text-[#FF982E] font-mono text-[11px] truncate">{service.pay_to}</span>
                  <button
                    onClick={() => copyText(service.pay_to, 'payTo')}
                    className="p-1 rounded text-[#777980] hover:text-[#FF982E] transition-colors shrink-0"
                    title="Copy PayTo Address"
                  >
                    {copiedPayTo ? <Check className="w-3.5 h-3.5 text-[#58B779]" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            </div>

            {/* Input Schema Viewer in Code-Editor Style */}
            <div>
              <span className="text-[10px] text-[#777980] uppercase block mb-1">Input Schema (JSON Schema):</span>
              <div className="bg-[#111214] border border-[#303133] rounded-lg overflow-hidden">
                <div className="flex items-center justify-between px-3 py-1.5 border-b border-[#303133] bg-[#171819] text-[10px] text-[#777980]">
                  <span className="flex items-center gap-1">
                    <Terminal className="w-3 h-3 text-[#FF982E]" />
                    <span>schema.json</span>
                  </span>
                  <span>JSON</span>
                </div>
                <pre className="p-3 text-[11px] font-mono text-[#E6E6E6] overflow-x-auto max-h-36 leading-relaxed select-text">
                  {JSON.stringify(service.input_schema || {}, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-5 py-3.5 border-t border-[#303133] bg-[#171819] flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-[#202123] hover:bg-[#303133] text-[#A0A1A5] hover:text-[#F5F5F5] text-xs font-semibold font-mono transition-colors border border-[#303133]"
          >
            Close
          </button>
          
          <button
            onClick={() => {
              onUseInTask(service);
              onClose();
            }}
            className="px-5 py-2 rounded-lg bg-[#FF982E] hover:bg-[#E98522] text-[#101112] text-xs font-bold font-mono uppercase tracking-wide transition-all shadow-sm shadow-[#FF982E]/30"
          >
            Use in Buyer Task →
          </button>
        </div>
      </div>
    </div>
  );
};
