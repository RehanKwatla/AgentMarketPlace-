import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { TaskResponse } from '../types';
import { StatusBadge } from './ReputationBadge';
import { 
  AlertCircle, 
  ExternalLink, 
  Layers, 
  ChevronDown, 
  ChevronUp, 
  FileText,
  Terminal,
  Copy,
  Check,
  ArrowRight
} from 'lucide-react';


interface TaskResultsViewProps {
  taskResult: TaskResponse;
  onViewLedgerRecord?: (requestId: string) => void;
}

export const TaskResultsView: React.FC<TaskResultsViewProps> = ({ 
  taskResult, 
  onViewLedgerRecord 
}) => {
  const [copied, setCopied] = useState(false);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  const handleCopyResult = () => {
    if (taskResult.final_result) {
      navigator.clipboard.writeText(taskResult.final_result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isSuccess = taskResult.status === 'completed' || taskResult.status === 'success';
  const isRefused = taskResult.status === 'refused';

  return (
    <div className="rounded-xl p-6 border border-[#CFC7BB] bg-[#F7F4EE] shadow-xs space-y-5">
      {/* Top Banner: Status + Spend */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#CFC7BB]/60">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-base font-serif font-bold text-[#241B19]">Autonomous Buyer Task Execution</h3>
            <span className={`text-[10px] font-mono uppercase px-2.5 py-0.5 rounded-full font-semibold border ${
              isSuccess 
                ? 'bg-[#A8B3A1]/20 text-[#38865B] border-[#A8B3A1]/50'
                : isRefused
                ? 'bg-[#B84040]/15 text-[#B84040] border-[#B84040]/30'
                : 'bg-[#DED8CD] text-[#241B19] border-[#CFC7BB]'
            }`}>
              {taskResult.status}
            </span>
          </div>
          <p className="text-[11px] text-[#82786F] font-mono">Task ID: {taskResult.task_id}</p>
        </div>

        <div className="flex items-center gap-3 bg-[#FFFFFF] px-4 py-2.5 rounded-xl border border-[#CFC7BB] text-xs font-mono shadow-xs">
          <div>
            <span className="text-[#82786F] text-[10px] block uppercase font-semibold">Total Cost</span>
            <span className="text-[#7D292D] font-bold text-sm">
              {taskResult.total_cost_usdc} <span className="text-[10px] text-[#82786F]">USDC</span>
            </span>
          </div>
          <div className="h-6 w-px bg-[#CFC7BB]" />
          <div>
            <span className="text-[#82786F] text-[10px] block uppercase font-semibold">Allocated Budget</span>
            <span className="text-[#241B19] font-bold text-sm">{taskResult.budget_allocated_usdc} USDC</span>
          </div>
        </div>
      </div>

      {/* Cost Explanation */}
      {taskResult.cost_explanation && (
        <div className="bg-[#FFFFFF] p-3.5 rounded-lg border border-[#CFC7BB] font-mono text-xs flex items-center justify-between">
          <span className="text-[#82786F]">Budget Reconciliation:</span>
          <span className="text-[#241B19] font-medium">{taskResult.cost_explanation}</span>
        </div>
      )}

      {/* Final Synthesized Output */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-mono uppercase font-bold text-[#241B19] flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-[#7D292D]" />
            Synthesized Final Result
          </span>
          {taskResult.final_result && (
            <button
              onClick={handleCopyResult}
              className="flex items-center gap-1 text-[11px] font-mono text-[#82786F] hover:text-[#241B19] px-2.5 py-1 rounded-md bg-[#FFFFFF] border border-[#CFC7BB] transition-colors cursor-pointer shadow-xs"
            >
              {copied ? <Check className="w-3 h-3 text-[#38865B]" /> : <Copy className="w-3 h-3 text-[#82786F]" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          )}
        </div>

        <div className="bg-[#FFFFFF] p-4 rounded-xl border border-[#CFC7BB] text-xs font-sans text-[#241B19] leading-relaxed whitespace-pre-wrap select-text shadow-inner">
          {taskResult.final_result || 'No aggregated output produced for this task.'}
        </div>
      </div>

      {/* Errors or Fallback notices */}
      {taskResult.errors_and_fallbacks && taskResult.errors_and_fallbacks.length > 0 && (
        <div className="p-3.5 rounded-lg bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] text-xs font-mono space-y-1">
          <div className="flex items-center gap-1.5 font-bold text-[11px]">
            <AlertCircle className="w-4 h-4 text-[#B84040] shrink-0" />
            <span>Execution Warnings & Fallbacks:</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[#241B19] font-sans text-[11px]">
            {taskResult.errors_and_fallbacks.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Step-by-Step Executions Breakdown */}
      <div>
        <h4 className="text-xs font-mono uppercase font-bold text-[#82786F] mb-2.5 flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-[#7D292D]" />
          Microservice Call Progression ({taskResult.executions.length} Step{taskResult.executions.length > 1 ? 's' : ''})
        </h4>

        {taskResult.executions.length === 0 ? (
          <div className="text-center py-6 bg-[#FFFFFF] rounded-xl border border-[#CFC7BB] text-xs font-mono text-[#82786F]">
            No microservice calls were dispatched.
          </div>
        ) : (
          <div className="space-y-2">
            {taskResult.executions.map((exec) => {
              const isExpanded = expandedStep === exec.step;

              return (
                <div
                  key={exec.step}
                  className="rounded-xl border border-[#CFC7BB] bg-[#FFFFFF] overflow-hidden font-mono text-xs transition-all shadow-xs"
                >
                  <div 
                    className="p-3 flex flex-wrap items-center justify-between gap-3 cursor-pointer hover:bg-[#DED8CD]/20"
                    onClick={() => setExpandedStep(isExpanded ? null : exec.step)}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="w-5 h-5 rounded-md bg-[#DED8CD] text-[#241B19] text-xs flex items-center justify-center font-bold border border-[#CFC7BB]">
                        {exec.step}
                      </span>
                      <div>
                        <div className="font-semibold text-[#241B19] flex items-center gap-2">
                          <span>{exec.service_id}</span>
                          <span className="text-[10px] text-[#82786F] font-normal">
                            (ID: {exec.request_id})
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-[#7D292D] font-bold">{exec.price_paid_usdc} USDC</span>
                      <StatusBadge status={exec.status} />
                      <span className="text-[#82786F] text-[11px]">{exec.latency_ms > 0 ? `${exec.latency_ms.toFixed(0)}ms` : '—'}</span>
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5 text-[#82786F]" /> : <ChevronDown className="w-3.5 h-3.5 text-[#82786F]" />}
                    </div>
                  </div>

                  {/* Expanded Step Inspection */}
                  {isExpanded && (
                    <div className="p-3.5 border-t border-[#CFC7BB]/60 bg-[#F7F4EE] space-y-3">
                      {exec.tx_hash && (
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-[#82786F]">Base Sepolia Tx Hash:</span>
                          <a
                            href={`https://sepolia.basescan.org/tx/${exec.tx_hash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[#7D292D] hover:underline font-medium"
                          >
                            <span>{exec.tx_hash}</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      )}

                      {exec.output && (
                        <div>
                          <span className="text-[#82786F] text-[10px] block mb-1 uppercase font-semibold">Raw Microservice Output:</span>
                          <pre className="p-2.5 rounded-lg bg-[#FFFFFF] text-[#241B19] text-[11px] overflow-x-auto max-h-40 border border-[#CFC7BB] shadow-inner">
                            {JSON.stringify(exec.output, null, 2)}
                          </pre>
                        </div>
                      )}

                      {exec.error && (
                        <div className="p-2.5 rounded-lg bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] text-[11px]">
                          <span className="font-bold block">Error details:</span>
                          <span>{exec.error}</span>
                        </div>
                      )}

                      {onViewLedgerRecord && (
                        <div className="pt-1 flex justify-end">
                          <button
                            onClick={() => onViewLedgerRecord(exec.request_id)}
                            className="text-xs text-[#7D292D] hover:underline flex items-center gap-1 font-mono cursor-pointer font-medium"
                          >
                            <FileText className="w-3 h-3" />
                            <span>Inspect Full Ledger Record #{exec.request_id}</span>
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Dedicated View Links */}
        <div className="pt-3 border-t border-[#CFC7BB]/60 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
          <NavLink
            to="/execution"
            className="px-3.5 py-2 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB] flex items-center gap-1.5 transition-colors shadow-xs"
          >
            <span>Open in Agent Execution</span>
            <ArrowRight className="w-3.5 h-3.5 text-[#82786F]" />
          </NavLink>

          <NavLink
            to="/results"
            className="px-4 py-2 rounded-lg bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-medium flex items-center gap-1.5 transition-colors shadow-xs"
          >
            <span>Open in Results & Provenance</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </NavLink>
        </div>
      </div>
    </div>
  );
};

