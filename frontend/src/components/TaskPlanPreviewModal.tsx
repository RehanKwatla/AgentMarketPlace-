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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn"
      onClick={onCancel}
    >
      <div 
        className="w-full max-w-xl bg-[#111111] border border-[rgba(255, 255, 255,0.22)] rounded-xl shadow-2xl overflow-hidden flex flex-col relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-[rgba(255, 255, 255,0.16)] bg-[#0D0D0D] flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#141414] text-[#FFFFFF] border border-[rgba(255, 255, 255,0.25)] flex items-center justify-center">
            <Lock className="w-3.5 h-3.5 text-[#FFFFFF]" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-[#FAFAFA]">
              Confirm Execution & Budget Reservation
            </h2>
            <p className="text-xs text-[#A3A3A3]">Review planned autonomous micropayments before execution</p>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 text-xs">
          {/* Objective Inset */}
          <div className="bg-[#0D0D0D] p-3 rounded-lg border border-[rgba(255, 255, 255,0.16)]">
            <span className="text-[11px] text-[#A3A3A3] block mb-0.5">Prompt</span>
            <p className="text-[#FAFAFA] text-xs italic leading-relaxed">"{plan.prompt}"</p>
          </div>

          {/* Budget vs Cost */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#0D0D0D] p-3 rounded-lg border border-[rgba(255, 255, 255,0.16)]">
              <span className="text-[11px] text-[#A3A3A3] block">Allocated Budget</span>
              <span className="text-[#FAFAFA] font-semibold font-mono text-base mt-0.5 block">{plan.budget_usdc} USDC</span>
            </div>

            <div className={`p-3 rounded-lg border ${
              plan.is_affordable 
                ? 'bg-[#0D0D0D] border-[rgba(255, 255, 255,0.16)]' 
                : 'bg-[rgba(115, 115, 115,0.08)] border-[rgba(115, 115, 115,0.25)]'
            }`}>
              <span className="text-[11px] text-[#A3A3A3] block">Estimated Cost</span>
              <span className={`font-semibold font-mono text-base mt-0.5 block ${
                plan.is_affordable ? 'text-[#FFFFFF]' : 'text-[#737373]'
              }`}>
                ~{plan.estimated_total_usdc} USDC
              </span>
            </div>
          </div>

          {/* Planned Sequence */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[#FAFAFA] font-medium text-xs">Required Service Sequence</span>
              <span className="text-[#A3A3A3] text-[11px]">{plan.steps.length} call{plan.steps.length > 1 ? 's' : ''} planned</span>
            </div>

            <div className="space-y-1.5">
              {plan.steps.map((step) => (
                <div
                  key={step.step_number}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.14)]"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="w-5 h-5 rounded bg-[#141414] text-[#FFFFFF] text-[11px] flex items-center justify-center font-mono font-medium border border-[rgba(255, 255, 255,0.25)]">
                      {step.step_number}
                    </span>
                    <div>
                      <div className="text-[#FAFAFA] font-medium text-xs">{step.service_name || step.service_id}</div>
                      <span className="text-[11px] text-[#A3A3A3] capitalize">{step.category} microservice</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-[#FAFAFA] font-mono font-medium text-xs">{step.estimated_cost_usdc} USDC</span>
                    <span className="block text-[10px] text-[#A3A3A3]">x402 challenge</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Safety Notice */}
          <div className="p-3 rounded-lg bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.16)] text-[#A3A3A3] text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-medium text-[#A3A3A3]">
              <ShieldCheck className="w-3.5 h-3.5 text-[#A3A3A3]" />
              <span>Safety Guarantee</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              Payments are executed via signed EIP-712 authorizations on Base Sepolia. If an endpoint errors, funds are preserved and logged as failed-not-charged.
            </p>
          </div>

          {!plan.is_affordable && (
            <div className="p-3 rounded-lg bg-[rgba(115, 115, 115,0.08)] border border-[rgba(115, 115, 115,0.25)] text-[#737373] text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>Estimated cost exceeds your allocated budget. Increase your budget before running this task.</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[rgba(255, 255, 255,0.16)] bg-[#0D0D0D] flex items-center justify-end gap-2.5">
          <button
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-3.5 py-1.5 rounded-lg bg-[#141414] hover:bg-[#1A1A1A] text-[#A3A3A3] hover:text-[#FAFAFA] text-xs font-medium transition-colors border border-[rgba(255, 255, 255,0.20)] cursor-pointer"
          >
            Cancel
          </button>

          <button
            onClick={onConfirm}
            disabled={isSubmitting || !plan.is_affordable}
            className="px-4 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#D4D4D4] disabled:opacity-50 disabled:cursor-not-allowed text-[#0A0A0A] text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            {isSubmitting ? (
              <>
                <div className="w-3 h-3 border-2 border-[#0A0A0A] border-t-transparent rounded-full animate-spin" />
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
