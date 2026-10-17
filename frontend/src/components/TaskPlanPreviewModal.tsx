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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#241B19]/50 backdrop-blur-sm animate-fadeIn"
      onClick={onCancel}
    >
      <div 
        className="w-full max-w-xl bg-[#F7F4EE] border border-[#CFC7BB] rounded-xl shadow-2xl overflow-hidden flex flex-col relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#CFC7BB] bg-[#DED8CD]/40 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#7D292D] text-[#F7F4EE] flex items-center justify-center shadow-xs">
            <Lock className="w-4 h-4 text-[#F7F4EE]" />
          </div>
          <div>
            <h2 className="text-base font-serif font-bold text-[#241B19]">
              Confirm Execution & Budget Reservation
            </h2>
            <p className="text-xs text-[#82786F]">Review planned autonomous micropayments before execution</p>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 text-xs">
          {/* Objective Inset */}
          <div className="bg-[#FFFFFF] p-3.5 rounded-lg border border-[#CFC7BB]">
            <span className="text-[11px] font-medium text-[#82786F] block mb-1">Prompt</span>
            <p className="text-[#241B19] text-xs italic leading-relaxed">"{plan.prompt}"</p>
          </div>

          {/* Budget vs Cost */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#FFFFFF] p-3.5 rounded-lg border border-[#CFC7BB]">
              <span className="text-[11px] font-medium text-[#82786F] block">Allocated Budget</span>
              <span className="text-[#241B19] font-bold font-mono text-base mt-0.5 block">{plan.budget_usdc} USDC</span>
            </div>

            <div className={`p-3.5 rounded-lg border ${
              plan.is_affordable 
                ? 'bg-[#FFFFFF] border-[#CFC7BB]' 
                : 'bg-[#B84040]/10 border-[#B84040]/30'
            }`}>
              <span className="text-[11px] font-medium text-[#82786F] block">Estimated Cost</span>
              <span className={`font-bold font-mono text-base mt-0.5 block ${
                plan.is_affordable ? 'text-[#7D292D]' : 'text-[#B84040]'
              }`}>
                ~{plan.estimated_total_usdc} USDC
              </span>
            </div>
          </div>

          {/* Planned Sequence */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[#241B19] font-semibold text-xs">Required Service Sequence</span>
              <span className="text-[#82786F] text-[11px]">{plan.steps.length} call{plan.steps.length > 1 ? 's' : ''} planned</span>
            </div>

            <div className="space-y-2">
              {plan.steps.map((step) => (
                <div
                  key={step.step_number}
                  className="flex items-center justify-between p-3 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB]"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-5 h-5 rounded bg-[#DED8CD] text-[#241B19] text-[11px] flex items-center justify-center font-mono font-semibold border border-[#CFC7BB]">
                      {step.step_number}
                    </span>
                    <div>
                      <div className="text-[#241B19] font-medium text-xs">{step.service_name || step.service_id}</div>
                      <span className="text-[11px] text-[#82786F] capitalize">{step.category} microservice</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-[#241B19] font-mono font-medium text-xs">{step.estimated_cost_usdc} USDC</span>
                    <span className="block text-[10px] text-[#82786F]">x402 challenge</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Safety Notice */}
          <div className="p-3.5 rounded-lg bg-[#A8B3A1]/15 border border-[#A8B3A1]/40 text-[#241B19] text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-medium text-[#241B19]">
              <ShieldCheck className="w-3.5 h-3.5 text-[#38865B]" />
              <span>Safety Guarantee</span>
            </div>
            <p className="text-[11px] text-[#82786F] leading-relaxed">
              Payments are executed via signed EIP-712 authorizations on Base Sepolia. If an endpoint errors, funds are preserved and logged as failed-not-charged.
            </p>
          </div>

          {!plan.is_affordable && (
            <div className="p-3 rounded-lg bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>Estimated cost exceeds your allocated budget. Increase your budget before running this task.</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 border-t border-[#CFC7BB] bg-[#DED8CD]/30 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-medium transition-colors border border-[#CFC7BB] cursor-pointer"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={onConfirm}
            disabled={isSubmitting || !plan.is_affordable}
            className="px-4 py-2 rounded-lg bg-[#7D292D] hover:bg-[#612024] disabled:opacity-50 disabled:cursor-not-allowed text-[#F7F4EE] text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
          >
            {isSubmitting ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-[#F7F4EE] border-t-transparent rounded-full animate-spin" />
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
