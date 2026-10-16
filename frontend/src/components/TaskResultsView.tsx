import React, { useState } from 'react';
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
  Check
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
    <div className="wallet-card rounded-xl p-5 border border-[rgba(120,160,153,0.20)] space-y-5">
      {/* Top Banner: Status + Spend */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[rgba(120,160,153,0.18)]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-bold text-[#F4F7F6] font-sans">Autonomous Buyer Task Execution</h3>
            <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-full font-bold border ${
              isSuccess 
                ? 'bg-[rgba(66,201,149,0.15)] text-[#42C995] border-[rgba(66,201,149,0.3)]'
                : isRefused
                ? 'bg-[rgba(225,109,109,0.15)] text-[#E16D6D] border-[rgba(225,109,109,0.3)]'
                : 'bg-[rgba(54,214,200,0.15)] text-[#36D6C8] border-[rgba(54,214,200,0.3)]'
            }`}>
              {taskResult.status}
            </span>
          </div>
          <p className="text-[11px] text-[#A0AAA7] font-mono">Task ID: {taskResult.task_id}</p>
        </div>

        <div className="flex items-center gap-3 bg-[#141A19] px-3.5 py-2 rounded-xl border border-[rgba(120,160,153,0.22)] text-xs font-mono">
          <div>
            <span className="text-[#A0AAA7] text-[10px] block uppercase font-semibold">Total Cost</span>
            <span className="text-[#F4F7F6] font-bold text-sm">
              {taskResult.total_cost_usdc} <span className="text-[10px] text-[#36D6C8]">USDC</span>
            </span>
          </div>
          <div className="h-6 w-px bg-[rgba(120,160,153,0.20)]" />
          <div>
            <span className="text-[#A0AAA7] text-[10px] block uppercase font-semibold">Allocated Budget</span>
            <span className="text-[#F4F7F6] font-bold text-sm">{taskResult.budget_allocated_usdc} USDC</span>
          </div>
        </div>
      </div>

      {/* Cost Explanation */}
      {taskResult.cost_explanation && (
        <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.18)] font-mono text-xs flex items-center justify-between">
          <span className="text-[#A0AAA7]">Budget Reconciliation:</span>
          <span className="text-[#F4F7F6] font-medium">{taskResult.cost_explanation}</span>
        </div>
      )}

      {/* Final Synthesized Output */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-mono uppercase font-bold text-[#F4F7F6] flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-[#36D6C8]" />
            Synthesized Final Result
          </span>
          {taskResult.final_result && (
            <button
              onClick={handleCopyResult}
              className="flex items-center gap-1 text-[11px] font-mono text-[#A0AAA7] hover:text-[#36D6C8] px-2 py-0.5 rounded-md bg-[#141A19] border border-[rgba(120,160,153,0.22)] transition-colors cursor-pointer"
            >
              {copied ? <Check className="w-3 h-3 text-[#42C995]" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          )}
        </div>

        <div className="bg-[#0D1111] p-3.5 rounded-xl border border-[rgba(120,160,153,0.20)] text-xs font-sans text-[#F4F7F6] leading-relaxed whitespace-pre-wrap select-text shadow-inner">
          {taskResult.final_result || 'No aggregated output produced for this task.'}
        </div>
      </div>

      {/* Errors or Fallback notices */}
      {taskResult.errors_and_fallbacks && taskResult.errors_and_fallbacks.length > 0 && (
        <div className="p-3.5 rounded-lg bg-[rgba(225,109,109,0.10)] border border-[rgba(225,109,109,0.28)] text-[#E16D6D] text-xs font-mono space-y-1">
          <div className="flex items-center gap-1.5 font-bold text-[11px]">
            <AlertCircle className="w-4 h-4 text-[#E16D6D] shrink-0" />
            <span>Execution Warnings & Fallbacks:</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[#F4F7F6] font-sans text-[11px]">
            {taskResult.errors_and_fallbacks.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Step-by-Step Executions Breakdown */}
      <div>
        <h4 className="text-xs font-mono uppercase font-bold text-[#A0AAA7] mb-2.5 flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-[#36D6C8]" />
          Microservice Call Progression ({taskResult.executions.length} Step{taskResult.executions.length > 1 ? 's' : ''})
        </h4>

        {taskResult.executions.length === 0 ? (
          <div className="text-center py-6 bg-[#0D1111] rounded-xl border border-[rgba(120,160,153,0.18)] text-xs font-mono text-[#6F7C78]">
            No microservice calls were dispatched.
          </div>
        ) : (
          <div className="space-y-2">
            {taskResult.executions.map((exec) => {
              const isExpanded = expandedStep === exec.step;

              return (
                <div
                  key={exec.step}
                  className="rounded-xl border border-[rgba(120,160,153,0.18)] bg-[#141A19] overflow-hidden font-mono text-xs transition-all"
                >
                  <div 
                    className="p-3 flex flex-wrap items-center justify-between gap-3 cursor-pointer hover:bg-[#1A2221]"
                    onClick={() => setExpandedStep(isExpanded ? null : exec.step)}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="w-5 h-5 rounded-md bg-[#0D1111] text-[#36D6C8] text-xs flex items-center justify-center font-bold border border-[rgba(54,214,200,0.25)]">
                        {exec.step}
                      </span>
                      <div>
                        <div className="font-semibold text-[#F4F7F6] flex items-center gap-2">
                          <span>{exec.service_id}</span>
                          <span className="text-[10px] text-[#A0AAA7] font-normal">
                            (ID: {exec.request_id})
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-[#36D6C8] font-bold">{exec.price_paid_usdc} USDC</span>
                      <StatusBadge status={exec.status} />
                      <span className="text-[#A0AAA7] text-[11px]">{exec.latency_ms > 0 ? `${exec.latency_ms.toFixed(0)}ms` : '—'}</span>
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5 text-[#A0AAA7]" /> : <ChevronDown className="w-3.5 h-3.5 text-[#A0AAA7]" />}
                    </div>
                  </div>

                  {/* Expanded Step Inspection */}
                  {isExpanded && (
                    <div className="p-3.5 border-t border-[rgba(120,160,153,0.18)] bg-[#0D1111] space-y-3">
                      {exec.tx_hash && (
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-[#A0AAA7]">Base Sepolia Tx Hash:</span>
                          <a
                            href={`https://sepolia.basescan.org/tx/${exec.tx_hash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[#36D6C8] hover:underline"
                          >
                            <span>{exec.tx_hash}</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      )}

                      {exec.output && (
                        <div>
                          <span className="text-[#A0AAA7] text-[10px] block mb-1 uppercase font-semibold">Raw Microservice Output:</span>
                          <pre className="p-2.5 rounded-lg bg-[#0B0D0D] text-[#F4F7F6] text-[11px] overflow-x-auto max-h-40 border border-[rgba(120,160,153,0.18)]">
                            {JSON.stringify(exec.output, null, 2)}
                          </pre>
                        </div>
                      )}

                      {exec.error && (
                        <div className="p-2.5 rounded-lg bg-[rgba(225,109,109,0.12)] border border-[rgba(225,109,109,0.3)] text-[#E16D6D] text-[11px]">
                          <span className="font-bold block">Error details:</span>
                          <span>{exec.error}</span>
                        </div>
                      )}

                      {onViewLedgerRecord && (
                        <div className="pt-1 flex justify-end">
                          <button
                            onClick={() => onViewLedgerRecord(exec.request_id)}
                            className="text-xs text-[#36D6C8] hover:underline flex items-center gap-1 font-mono cursor-pointer"
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
      </div>
    </div>
  );
};
