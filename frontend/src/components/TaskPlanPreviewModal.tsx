import React from 'react';
import { TaskPlanPreview } from '../types';
import { ShieldCheck, AlertTriangle, ArrowRight, Lock } from 'lucide-react';

interface TaskPlanPreviewModalProps {
  plan: TaskPlanPreview | null;
  onConfirm: () => void;
  onCancel: () => void;
  isSubmitting: boolean;
}

export const TaskPlanPreviewModal: React.FC<TaskPlanPreviewModalProps> = ({
  plan,
  onConfirm,
  onCancel,
  isSubmitting,
}) => {
  if (!plan) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel w-full max-w-xl rounded-2xl border border-slate-800 shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center">
              <Lock className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
                Confirm Execution & Budget Reservation
              </h2>
              <p className="text-xs text-slate-400">Review planned autonomous micropayments before execution</p>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 text-xs font-mono">
          {/* Objective Recap */}
          <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase font-bold block mb-1">Target Prompt</span>
            <p className="text-slate-200 font-sans text-xs italic">"{plan.prompt}"</p>
          </div>

          {/* Budget vs Estimated Cost Comparison */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase block">Allocated Budget</span>
              <span className="text-white font-bold text-base mt-0.5 block">{plan.budget_usdc} USDC</span>
            </div>

            <div className={`p-3 rounded-xl border ${
              plan.is_affordable 
                ? 'bg-emerald-950/20 border-emerald-500/30' 
                : 'bg-rose-950/20 border-rose-500/30'
            }`}>
              <span className="text-[10px] text-slate-400 uppercase block">Estimated Execution Cost</span>
              <span className={`font-bold text-base mt-0.5 block ${
                plan.is_affordable ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                ~{plan.estimated_total_usdc} USDC
              </span>
            </div>
          </div>

          {/* Planned Calls Sequence */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-300 font-semibold font-sans">Required Service Sequence</span>
              <span className="text-slate-500 text-[11px]">{plan.steps.length} call{plan.steps.length > 1 ? 's' : ''} planned</span>
            </div>

            <div className="space-y-2">
              {plan.steps.map((step) => (
                <div
                  key={step.step_number}
                  className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800/80"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 text-[11px] flex items-center justify-center font-bold">
                      {step.step_number}
                    </span>
                    <div>
                      <div className="text-slate-200 font-semibold">{step.service_name || step.service_id}</div>
                      <span className="text-[10px] text-blue-400 uppercase font-mono">{step.category} microservice</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-emerald-400 font-bold">{step.estimated_cost_usdc} USDC</span>
                    <span className="block text-[10px] text-slate-500">x402 challenge</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Safety Notice */}
          <div className="p-3.5 rounded-xl bg-blue-950/20 border border-blue-500/30 text-blue-200 font-sans text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-blue-300">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>Cryptographic Safety Guarantee</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              Payments are executed via signed EIP-712 authorizations on Base Sepolia. Your private keys never leave the server. If an endpoint errors, funds are preserved and logged as failed-not-charged.
            </p>
          </div>

          {!plan.is_affordable && (
            <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>Warning: Estimated cost exceeds your allocated budget. Task will be refused unless budget is increased.</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/90 flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold font-mono transition-colors"
          >
            Cancel
          </button>

          <button
            onClick={onConfirm}
            disabled={isSubmitting || !plan.is_affordable}
            className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold font-mono uppercase tracking-wide transition-all shadow-lg shadow-blue-500/20 flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Executing Calls...</span>
              </>
            ) : (
              <>
                <span>Authorize & Execute Task</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
