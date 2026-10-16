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
        className="w-full max-w-xl bg-[#101514] border border-[rgba(120,160,153,0.22)] rounded-xl shadow-2xl overflow-hidden flex flex-col relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-[rgba(120,160,153,0.16)] bg-[#0D1111] flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#141A19] text-[#36D6C8] border border-[rgba(54,214,200,0.25)] flex items-center justify-center">
            <Lock className="w-3.5 h-3.5 text-[#36D6C8]" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-[#F4F7F6]">
              Confirm Execution & Budget Reservation
            </h2>
            <p className="text-xs text-[#A0AAA7]">Review planned autonomous micropayments before execution</p>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 text-xs">
          {/* Objective Inset */}
          <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)]">
            <span className="text-[11px] text-[#A0AAA7] block mb-0.5">Prompt</span>
            <p className="text-[#F4F7F6] text-xs italic leading-relaxed">"{plan.prompt}"</p>
          </div>

          {/* Budget vs Cost */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)]">
              <span className="text-[11px] text-[#A0AAA7] block">Allocated Budget</span>
              <span className="text-[#F4F7F6] font-semibold font-mono text-base mt-0.5 block">{plan.budget_usdc} USDC</span>
            </div>

            <div className={`p-3 rounded-lg border ${
              plan.is_affordable 
                ? 'bg-[#0D1111] border-[rgba(120,160,153,0.16)]' 
                : 'bg-[rgba(225,109,109,0.08)] border-[rgba(225,109,109,0.25)]'
            }`}>
              <span className="text-[11px] text-[#A0AAA7] block">Estimated Cost</span>
              <span className={`font-semibold font-mono text-base mt-0.5 block ${
                plan.is_affordable ? 'text-[#36D6C8]' : 'text-[#E16D6D]'
              }`}>
                ~{plan.estimated_total_usdc} USDC
              </span>
            </div>
          </div>

          {/* Planned Sequence */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[#F4F7F6] font-medium text-xs">Required Service Sequence</span>
              <span className="text-[#A0AAA7] text-[11px]">{plan.steps.length} call{plan.steps.length > 1 ? 's' : ''} planned</span>
            </div>

            <div className="space-y-1.5">
              {plan.steps.map((step) => (
                <div
                  key={step.step_number}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-[#0D1111] border border-[rgba(120,160,153,0.14)]"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="w-5 h-5 rounded bg-[#141A19] text-[#36D6C8] text-[11px] flex items-center justify-center font-mono font-medium border border-[rgba(54,214,200,0.25)]">
                      {step.step_number}
                    </span>
                    <div>
                      <div className="text-[#F4F7F6] font-medium text-xs">{step.service_name || step.service_id}</div>
                      <span className="text-[11px] text-[#A0AAA7] capitalize">{step.category} microservice</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-[#F4F7F6] font-mono font-medium text-xs">{step.estimated_cost_usdc} USDC</span>
                    <span className="block text-[10px] text-[#A0AAA7]">x402 challenge</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Safety Notice */}
          <div className="p-3 rounded-lg bg-[#0D1111] border border-[rgba(120,160,153,0.16)] text-[#A0AAA7] text-xs space-y-1">
            <div className="flex items-center gap-1.5 font-medium text-[#42C995]">
              <ShieldCheck className="w-3.5 h-3.5 text-[#42C995]" />
              <span>Safety Guarantee</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              Payments are executed via signed EIP-712 authorizations on Base Sepolia. If an endpoint errors, funds are preserved and logged as failed-not-charged.
            </p>
          </div>

          {!plan.is_affordable && (
            <div className="p-3 rounded-lg bg-[rgba(225,109,109,0.08)] border border-[rgba(225,109,109,0.25)] text-[#E16D6D] text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>Estimated cost exceeds your allocated budget. Increase your budget before running this task.</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-[rgba(120,160,153,0.16)] bg-[#0D1111] flex items-center justify-end gap-2.5">
          <button
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-3.5 py-1.5 rounded-lg bg-[#141A19] hover:bg-[#1A2221] text-[#A0AAA7] hover:text-[#F4F7F6] text-xs font-medium transition-colors border border-[rgba(120,160,153,0.20)] cursor-pointer"
          >
            Cancel
          </button>

          <button
            onClick={onConfirm}
            disabled={isSubmitting || !plan.is_affordable}
            className="px-4 py-1.5 rounded-lg bg-[#36D6C8] hover:bg-[#53E3D6] disabled:opacity-50 disabled:cursor-not-allowed text-[#0B0D0D] text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            {isSubmitting ? (
              <>
                <div className="w-3 h-3 border-2 border-[#0B0D0D] border-t-transparent rounded-full animate-spin" />
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
