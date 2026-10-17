import React from 'react';
import { Search, Layers, ShieldCheck, PlayCircle, FileText } from 'lucide-react';

interface LifecycleStage {
  step: number;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

/**
 * Static explanation of the x402 per-call flow.
 *
 * This is an illustrative reference only. It is NOT a claim that any specific
 * task completed these stages, so no per-task state is derived from it.
 */
const STAGES: LifecycleStage[] = [
  {
    step: 1,
    title: 'Discover',
    description: 'Search the registry for a service whose declared capability matches the task intent.',
    icon: Search,
  },
  {
    step: 2,
    title: 'Select',
    description: 'Rank candidates on capability, recorded reliability, price, and observed latency.',
    icon: Layers,
  },
  {
    step: 3,
    title: 'Pay / Verify',
    description: 'Settle or validate the x402 authorization for the listed price before execution.',
    icon: ShieldCheck,
  },
  {
    step: 4,
    title: 'Execute',
    description: 'The seller runs the service and returns an output payload signed to the request.',
    icon: PlayCircle,
  },
  {
    step: 5,
    title: 'Record Result',
    description: 'The ledger commits the receipt, amount, status, and settlement evidence.',
    icon: FileText,
  },
];

export const ExecutionLifecycle: React.FC = () => {
  return (
    <section
      aria-label="Illustrative execution lifecycle"
      className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-5 space-y-4 animate-rise"
    >
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
        <div>
          <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#82786F]">
            Execution Lifecycle
          </h2>
          <p className="text-[11px] text-[#82786F] mt-0.5">
            How every pay-per-call invocation is expected to move from discovery to an audit record.
          </p>
        </div>
        <span className="text-[10px] font-mono text-[#82786F] px-2 py-0.5 rounded bg-[#DED8CD]/60 border border-[#CFC7BB] self-start sm:self-auto">
          Illustrative reference — not a per-task trace
        </span>
      </div>

      <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {STAGES.map((stage) => {
          const Icon = stage.icon;
          return (
            <li
              key={stage.step}
              className="relative rounded-lg border border-[#CFC7BB] bg-[#FFFFFF] p-3.5 space-y-2 card-lift"
            >
              <div className="flex items-center justify-between">
                <span className="w-5 h-5 rounded-md bg-[#7D292D] text-[#F7F4EE] text-[10px] font-mono font-bold flex items-center justify-center">
                  {stage.step}
                </span>
                <Icon className="w-4 h-4 text-[#7D292D]" />
              </div>
              <h3 className="text-xs font-semibold text-[#241B19] font-sans">{stage.title}</h3>
              <p className="text-[11px] text-[#82786F] leading-relaxed">{stage.description}</p>
            </li>
          );
        })}
      </ol>

      <p className="text-[10px] font-mono text-[#82786F] pt-2 border-t border-[#CFC7BB]/60">
        Task completion and payment settlement are recorded as separate states — a completed call does not by itself prove an on-chain settlement.
      </p>
    </section>
  );
};

export default ExecutionLifecycle;
