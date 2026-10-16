import React, { useEffect } from 'react';
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
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSubmitting) onCancel();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onCancel, isSubmitting]);

  if (!plan) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn"
      onClick={onCancel}
    >
      <div 
        className="w-full max-w-xl bg-[#191A1C] border border-[#303133] rounded-xl shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#303133] bg-[#171819] flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#202123] text-[#FF982E] border border-[#303133] flex items-center justify-center">
            <Lock className="w-4 h-4 text-[#FF982E]" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-[#F5F5F5] font-mono uppercase tracking-wide">
              Confirm Execution & Budget Reservation
            </h2>
            <p className="text-xs text-[#777980]">Review planned autonomous micropayments before execution</p>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 text-xs font-mono">
          {/* Objective Inset */}
          <div className="bg-[#111214] p-3.5 rounded-lg border border-[#303133]">
            <span className="text-[10px] text-[#777980] uppercase font-bold block mb-1">Target Prompt</span>
            <p className="text-[#F5F5F5] font-sans text-xs italic">"{plan.prompt}"</p>
          </div>

          {/* Budget vs Cost */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#202123] p-3 rounded-lg border border-[#303133]">
              <span className="text-[10px] text-[#777980] uppercase block">Allocated Budget</span>
              <span className="text-[#F5F5F5] font-bold text-base mt-0.5 block">{plan.budget_usdc} USDC</span>
            </div>

            <div className={`p-3 rounded-lg border ${
              plan.is_affordable 
                ? 'bg-[#202123] border-[#303133]' 
                : 'bg-[#E15D52]/10 border-[#E15D52]/30'
            }`}>
              <span className="text-[10px] text-[#777980] uppercase block">Estimated Execution Cost</span>
              <span className={`font-bold text-base mt-0.5 block ${
                plan.is_affordable ? 'text-[#FF982E]' : 'text-[#E15D52]'
              }`}>
                ~{plan.estimated_total_usdc} USDC
              </span>
            </div>
          </div>

          {/* Planned Sequence */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[#A0A1A5] font-semibold font-sans">Required Service Sequence</span>
              <span className="text-[#777980] text-[11px]">{plan.steps.length} call{plan.steps.length > 1 ? 's' : ''} planned</span>
            </div>

            <div className="space-y-2">
              {plan.steps.map((step) => (
                <div
                  key={step.step_number}
                  className="flex items-center justify-between p-2.5 rounded bg-[#111214] border border-[#303133]"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="w-5 h-5 rounded bg-[#202123] text-[#A0A1A5] text-[11px] flex items-center justify-center font-bold">
                      {step.step_number}
                    </span>
                    <div>
                      <div className="text-[#F5F5F5] font-semibold">{step.service_name || step.service_id}</div>
                      <span className="text-[10px] text-[#FF982E] uppercase font-mono">{step.category} microservice</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-[#F5F5F5] font-bold">{step.estimated_cost_usdc} USDC</span>
                    <span className="block text-[10px] text-[#777980]">x402 challenge</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Safety Notice */}
          <div className="p-3 rounded-lg bg-[#202123] border border-[#303133] text-[#A0A1A5] font-sans text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-[#FF982E]">
              <ShieldCheck className="w-3.5 h-3.5 text-[#58B779]" />
              <span>Cryptographic Safety Guarantee</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              Payments are executed via signed EIP-712 authorizations on Base Sepolia. Your private keys never leave the server. If an endpoint errors, funds are preserved and logged as failed-not-charged.
            </p>
          </div>

          {!plan.is_affordable && (
            <div className="p-3 rounded-lg bg-[#E15D52]/10 border border-[#E15D52]/30 text-[#E15D52] text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>Warning: Estimated cost exceeds your allocated budget. Task will be refused unless budget is increased.</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 border-t border-[#303133] bg-[#171819] flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-lg bg-[#202123] hover:bg-[#303133] text-[#A0A1A5] hover:text-[#F5F5F5] text-xs font-semibold font-mono transition-colors border border-[#303133]"
          >
            Cancel
          </button>

          <button
            onClick={onConfirm}
            disabled={isSubmitting || !plan.is_affordable}
            className="px-5 py-2 rounded-lg bg-[#FF982E] hover:bg-[#E98522] disabled:opacity-50 disabled:cursor-not-allowed text-[#101112] text-xs font-bold font-mono uppercase tracking-wide transition-all shadow-sm shadow-[#FF982E]/30 flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-3 h-3 border-2 border-[#101112] border-t-transparent rounded-full animate-spin" />
                <span>Executing Calls...</span>
              </>
            ) : (
              <>
                <span>Authorize & Execute Task</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
