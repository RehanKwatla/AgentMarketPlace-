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
    <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-6">
      {/* Top Banner: Status + Spend */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-base font-bold text-white font-sans">Autonomous Buyer Task Execution</h3>
            <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold border ${
              isSuccess 
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30'
                : isRefused
                ? 'bg-rose-950/40 text-rose-400 border-rose-500/30'
                : 'bg-amber-950/40 text-amber-300 border-amber-500/30'
            }`}>
              {taskResult.status}
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">Task ID: {taskResult.task_id}</p>
        </div>

        <div className="flex items-center gap-3 bg-slate-900/90 px-4 py-2.5 rounded-xl border border-slate-800 text-xs font-mono">
          <div>
            <span className="text-slate-400 text-[10px] block uppercase">Total Cost</span>
            <span className="text-emerald-400 font-bold text-sm">{taskResult.total_cost_usdc} USDC</span>
          </div>
          <div className="h-6 w-px bg-slate-800" />
          <div>
            <span className="text-slate-400 text-[10px] block uppercase">Allocated Budget</span>
            <span className="text-slate-200 font-bold text-sm">{taskResult.budget_allocated_usdc} USDC</span>
          </div>
        </div>
      </div>

      {/* Cost Explanation */}
      {taskResult.cost_explanation && (
        <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80 font-mono text-xs flex items-center justify-between">
          <span className="text-slate-400">Budget Reconciliation:</span>
          <span className="text-slate-200 font-medium">{taskResult.cost_explanation}</span>
        </div>
      )}

      {/* Final Synthesized Output */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-mono uppercase font-bold text-slate-300 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-blue-400" />
            Synthesized Final Result
          </span>
          {taskResult.final_result && (
            <button
              onClick={handleCopyResult}
              className="flex items-center gap-1 text-[11px] font-mono text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800/60 border border-slate-700/60 transition-colors"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy Result'}</span>
            </button>
          )}
        </div>

        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80 text-xs font-sans text-slate-200 leading-relaxed whitespace-pre-wrap select-text">
          {taskResult.final_result || 'No aggregated output produced for this task.'}
        </div>
      </div>

      {/* Errors or Fallback notices */}
      {taskResult.errors_and_fallbacks && taskResult.errors_and_fallbacks.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 text-amber-300 text-xs font-mono space-y-1.5">
          <div className="flex items-center gap-2 font-bold text-[11px]">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>Execution Warnings & Fallbacks:</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-slate-300 font-sans text-[11px]">
            {taskResult.errors_and_fallbacks.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Step-by-Step Executions Breakdown */}
      <div>
        <h4 className="text-xs font-mono uppercase font-bold text-slate-300 mb-3 flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-400" />
          Microservice Call Progression ({taskResult.executions.length} Step{taskResult.executions.length > 1 ? 's' : ''})
        </h4>

        {taskResult.executions.length === 0 ? (
          <div className="text-center py-6 bg-slate-950/60 rounded-xl border border-slate-800 text-xs font-mono text-slate-500">
            No microservice calls were dispatched.
          </div>
        ) : (
          <div className="space-y-3">
            {taskResult.executions.map((exec) => {
              const isExpanded = expandedStep === exec.step;

              return (
                <div
                  key={exec.step}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden font-mono text-xs transition-all"
                >
                  <div 
                    className="p-3.5 flex flex-wrap items-center justify-between gap-3 cursor-pointer hover:bg-slate-900/90"
                    onClick={() => setExpandedStep(isExpanded ? null : exec.step)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-200 text-xs flex items-center justify-center font-bold">
                        {exec.step}
                      </span>
                      <div>
                        <div className="font-semibold text-white flex items-center gap-2">
                          <span>{exec.service_id}</span>
                          <span className="text-[10px] text-slate-500 font-normal">
                            (ID: {exec.request_id})
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-emerald-400 font-bold">{exec.price_paid_usdc} USDC</span>
                      <StatusBadge status={exec.status} />
                      <span className="text-slate-400 text-[11px]">{exec.latency_ms > 0 ? `${exec.latency_ms.toFixed(0)}ms` : '—'}</span>
                      {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </div>
                  </div>

                  {/* Expanded Step Inspection */}
                  {isExpanded && (
                    <div className="p-4 border-t border-slate-800 bg-slate-950/80 space-y-3">
                      {exec.tx_hash && (
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-400">Base Sepolia Tx Hash:</span>
                          <a
                            href={`https://sepolia.basescan.org/tx/${exec.tx_hash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 underline"
                          >
                            <span>{exec.tx_hash}</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      )}

                      {exec.output && (
                        <div>
                          <span className="text-slate-400 text-[11px] block mb-1">Raw Microservice Output:</span>
                          <pre className="p-2.5 rounded-lg bg-slate-900 text-slate-300 text-[11px] overflow-x-auto max-h-40 border border-slate-800">
                            {JSON.stringify(exec.output, null, 2)}
                          </pre>
                        </div>
                      )}

                      {exec.error && (
                        <div className="p-2.5 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-300 text-[11px]">
                          <span className="font-bold block">Error details:</span>
                          <span>{exec.error}</span>
                        </div>
                      )}

                      {onViewLedgerRecord && (
                        <div className="pt-2 flex justify-end">
                          <button
                            onClick={() => onViewLedgerRecord(exec.request_id)}
                            className="text-xs text-blue-400 hover:underline flex items-center gap-1 font-mono"
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
