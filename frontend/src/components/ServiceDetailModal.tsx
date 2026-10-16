import React from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { X, Zap } from 'lucide-react';

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
  if (!service) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-2xl rounded-2xl border border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center font-bold">
              <Zap className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white font-sans">{service.name}</h2>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  {service.category}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">ID: {service.service_id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs font-mono">
          {/* Summary & Price */}
          <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
              <span className="text-slate-400 text-[11px] block">Price per Call (x402 protocol)</span>
              <span className="text-emerald-400 font-bold text-xl">{service.price_usdc} USDC</span>
              <span className="text-slate-500 text-[10px] block mt-0.5">({service.price_base_units} integer base units)</span>
            </div>
            <div className="text-right">
              <span className="text-slate-400 text-[11px] block">Settlement Network</span>
              <span className="text-blue-400 font-semibold text-xs">{service.network}</span>
              <span className="text-slate-500 text-[10px] block mt-0.5">Base Sepolia USDC</span>
            </div>
          </div>

          {/* Description */}
          <div>
            <h4 className="text-slate-300 font-semibold font-sans mb-1 text-sm">Capability Overview</h4>
            <p className="text-slate-400 font-sans text-xs leading-relaxed bg-slate-900/40 p-3 rounded-lg border border-slate-800/80">
              {service.description || 'No description registered for this seller agent.'}
            </p>
          </div>

          {/* Reputation & Telemetry */}
          <div>
            <h4 className="text-slate-300 font-semibold font-sans mb-2 text-sm flex items-center justify-between">
              <span>Historical Reputation & Telemetry</span>
              {reputation && reputation.total_calls > 0 ? (
                <span className="text-blue-400 text-xs font-mono">
                  {reputation.reputation_score}% Score
                </span>
              ) : (
                <span className="text-slate-500 text-xs font-mono">New Service</span>
              )}
            </h4>

            {reputation && reputation.total_calls > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-800 text-center">
                  <span className="text-slate-500 text-[10px] block uppercase">Total Calls</span>
                  <span className="text-white font-bold text-sm mt-0.5 block">{reputation.total_calls}</span>
                </div>
                <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-800 text-center">
                  <span className="text-slate-500 text-[10px] block uppercase">Success Rate</span>
                  <span className="text-emerald-400 font-bold text-sm mt-0.5 block">{reputation.success_rate.toFixed(1)}%</span>
                </div>
                <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-800 text-center">
                  <span className="text-slate-500 text-[10px] block uppercase">Median Latency</span>
                  <span className="text-blue-400 font-bold text-sm mt-0.5 block">{reputation.median_latency_ms.toFixed(0)} ms</span>
                </div>
                <div className="bg-slate-900/70 p-3 rounded-lg border border-slate-800 text-center">
                  <span className="text-slate-500 text-[10px] block uppercase">Failures</span>
                  <span className="text-rose-400 font-bold text-sm mt-0.5 block">{reputation.failure_counts}</span>
                </div>
              </div>
            ) : (
              <div className="bg-slate-900/30 p-3 rounded-lg border border-slate-800 text-slate-500 text-center text-[11px]">
                Not enough historical calls yet to display confidence intervals.
              </div>
            )}
          </div>

          {/* Technical Interface */}
          <div className="space-y-3">
            <h4 className="text-slate-300 font-semibold font-sans text-sm">Integration Specs</h4>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-slate-400">Endpoint URL:</span>
                <span className="text-slate-200">{service.endpoint_url}</span>
              </div>
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-slate-400">Registered PayTo Address:</span>
                <span className="text-blue-400 font-mono text-[10px]">{service.pay_to}</span>
              </div>
            </div>

            {/* Input Schema Preview */}
            <div>
              <span className="text-slate-400 text-[11px] block mb-1">Input Schema (JSON Schema):</span>
              <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-slate-300 text-[11px] overflow-x-auto max-h-32">
                {JSON.stringify(service.input_schema || {}, null, 2)}
              </pre>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold font-mono transition-colors"
          >
            Close
          </button>
          <button
            onClick={() => {
              onUseInTask(service);
              onClose();
            }}
            className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold font-mono uppercase tracking-wide transition-colors shadow-lg shadow-blue-500/20"
          >
            Use In Buyer Task →
          </button>
        </div>
      </div>
    </div>
  );
};
