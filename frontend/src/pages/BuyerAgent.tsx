import React, { useState } from 'react';
import { useMarketplace } from '../context/MarketplaceContext';
import { TaskResultsView } from '../components/TaskResultsView';
import { 
  ShieldCheck, 
  Cpu, 
  Sparkles 
} from 'lucide-react';

export const BuyerAgent: React.FC = () => {
  const {
    taskPrompt,
    setTaskPrompt,
    budgetUsdc,
    setBudgetUsdc,
    isPlanning,
    isSubmitting,
    taskResult,
    taskError,
    handlePreviewPlan,
    inspectLedgerRecord
  } = useMarketplace();

  const [activePreset, setActivePreset] = useState<string | null>(null);

  const presets = [
    {
      title: 'Market Intelligence',
      prompt: 'Collect market data on ETH and BTC, extract latest news, and summarize key trends',
      budget: '0.05'
    },
    {
      title: 'Web Content Extraction',
      prompt: 'Scrape markdown content from target URLs and synthesize structured data',
      budget: '0.03'
    },
    {
      title: 'Autonomous Synthesis',
      prompt: 'Query inference engine to generate a risk-managed DeFi investment thesis',
      budget: '0.02'
    }
  ];

  const handleSelectPreset = (p: typeof presets[0]) => {
    setActivePreset(p.title);
    setTaskPrompt(p.prompt);
    setBudgetUsdc(p.budget);
  };

  const stages = [
    { step: 1, title: 'Understand' },
    { step: 2, title: 'Discover' },
    { step: 3, title: 'Verify' },
    { step: 4, title: 'Budget Lock' },
    { step: 5, title: 'x402 Payment' },
    { step: 6, title: 'Output Validation' },
    { step: 7, title: 'Complete' }
  ];

  const getCurrentStage = () => {
    if (!isSubmitting && !taskResult) return 0;
    if (isSubmitting) return 5;
    if (taskResult?.status === 'completed' || taskResult?.status === 'success') return 7;
    return 6;
  };

  const currentStage = getCurrentStage();

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[rgba(255, 255, 255,0.16)] pb-4">
        <div>
          <h1 className="text-2xl font-semibold text-[#FAFAFA]">
            Buyer Agent Console
          </h1>
          <p className="text-xs text-[#A3A3A3] mt-0.5">
            Orchestrate multi-step AI tasks with automated service discovery and x402 payment execution.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <div className="bg-[#121212] px-3 py-1.5 rounded-md border border-[rgba(255, 255, 255,0.18)]">
            <span className="text-[#A3A3A3] text-[11px] mr-1.5">Budget:</span>
            <span className="font-mono font-medium text-[#FFFFFF]">{budgetUsdc} USDC</span>
          </div>
          <div className="bg-[#121212] px-3 py-1.5 rounded-md border border-[rgba(255, 255, 255,0.18)] text-[#A3A3A3] flex items-center gap-1 font-mono text-[11px]">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Boundary Active</span>
          </div>
        </div>
      </div>

      {/* Clean 7-Stage Progression Bar */}
      <div className="wallet-card p-3 rounded-lg border border-[rgba(255, 255, 255,0.18)]">
        <div className="flex items-center justify-between gap-1 overflow-x-auto text-[11px]">
          {stages.map((st) => {
            const isCompleted = currentStage >= st.step;
            const isCurrent = isSubmitting && st.step === 5;

            return (
              <div 
                key={st.step}
                className={`flex-1 min-w-[90px] py-1.5 px-2 rounded text-center transition-colors ${
                  isCurrent
                    ? 'bg-[rgba(255, 255, 255,0.15)] text-[#FFFFFF] font-medium border border-[rgba(255, 255, 255,0.3)]'
                    : isCompleted
                    ? 'bg-[#151515] text-[#A3A3A3] font-medium'
                    : 'text-[#737373]'
                }`}
              >
                <span>{st.step}. {st.title}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Console Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Form: Task prompt & Budget */}
        <div className="lg:col-span-5 wallet-card border border-[rgba(255, 255, 255,0.18)] rounded-lg p-4 space-y-4 text-xs font-sans">
          <div>
            <h2 className="text-sm font-semibold text-[#FAFAFA]">Task Definition</h2>
            <p className="text-xs text-[#A3A3A3] mt-0.5">
              Specify your objective and max USDC spending allowance.
            </p>
          </div>

          {/* Quick Presets */}
          <div className="space-y-1">
            <span className="text-[11px] text-[#737373] block">Example Prompts:</span>
            <div className="flex flex-wrap gap-1.5">
              {presets.map((pr) => (
                <button
                  key={pr.title}
                  type="button"
                  onClick={() => handleSelectPreset(pr)}
                  className={`px-2 py-0.5 rounded text-[11px] transition-colors cursor-pointer ${
                    activePreset === pr.title
                      ? 'bg-[rgba(255, 255, 255,0.12)] text-[#FFFFFF] border border-[rgba(255, 255, 255,0.3)] font-medium'
                      : 'bg-[#171717] text-[#A3A3A3] hover:text-[#FAFAFA]'
                  }`}
                >
                  {pr.title}
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={(e) => { e.preventDefault(); handlePreviewPlan(); }} className="space-y-3.5">
            <div>
              <label className="block text-[#A3A3A3] text-[11px] mb-1 font-medium">Objective Prompt</label>
              <textarea
                value={taskPrompt}
                onChange={(e) => setTaskPrompt(e.target.value)}
                placeholder="Describe your research, extraction, or inference goal..."
                className="w-full h-24 bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.18)] rounded-md p-2.5 text-[#FAFAFA] placeholder-[#737373] focus:outline-none focus:border-[#FFFFFF] resize-none text-xs leading-relaxed font-sans"
                required
              />
            </div>

            <div>
              <label className="block text-[#A3A3A3] text-[11px] mb-1 font-medium">Budget Allowance (USDC)</label>
              <input
                type="text"
                value={budgetUsdc}
                onChange={(e) => setBudgetUsdc(e.target.value)}
                placeholder="0.05"
                className="w-full bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.18)] rounded-md p-2 text-[#FAFAFA] focus:outline-none focus:border-[#FFFFFF] font-mono text-xs"
                required
              />
            </div>

            {taskError && (
              <div className="p-2.5 rounded-md bg-[rgba(115, 115, 115,0.1)] border border-[rgba(115, 115, 115,0.25)] text-[#737373] text-xs">
                {taskError}
              </div>
            )}

            <button
              type="submit"
              disabled={isPlanning || isSubmitting}
              className="w-full py-2 rounded-md bg-[#FFFFFF] hover:bg-[#E5E5E5] text-[#0A0A0A] font-medium text-xs transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              {isPlanning ? (
                <span>Planning Pipeline...</span>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Plan & Preview Costs</span>
                </>
              )}
            </button>
          </form>

          <div className="pt-2 border-t border-[rgba(255, 255, 255,0.12)] text-[11px] text-[#A3A3A3] space-y-0.5">
            <span className="text-[#FAFAFA] font-medium">Budget Protection:</span>
            <p>
              Costs are reserved atomically before execution. Zero charges occur if an endpoint fails or exceeds budget.
            </p>
          </div>
        </div>

        {/* Right Output: Execution Results or Status */}
        <div className="lg:col-span-7">
          {taskResult ? (
            <TaskResultsView
              taskResult={taskResult}
              onViewLedgerRecord={inspectLedgerRecord}
            />
          ) : (
            <div className="wallet-card border border-[rgba(255, 255, 255,0.18)] rounded-lg p-8 min-h-[360px] flex flex-col items-center justify-center text-center text-xs text-[#A3A3A3]">
              {isSubmitting ? (
                <div className="space-y-3 max-w-xs">
                  <div className="w-8 h-8 border-2 border-[#FFFFFF] border-t-transparent rounded-full animate-spin mx-auto" />
                  <div>
                    <p className="text-[#FAFAFA] font-medium text-sm">Executing x402 calls...</p>
                    <p className="text-[11px] text-[#737373] mt-0.5">
                      Submitting EIP-712 authorizations and committing settlement proofs.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-2 max-w-sm">
                  <Cpu className="w-6 h-6 text-[#FFFFFF] mx-auto opacity-70" />
                  <h3 className="text-sm font-medium text-[#FAFAFA]">Ready for Execution</h3>
                  <p className="text-[11px] text-[#A3A3A3] leading-relaxed">
                    Enter an objective prompt on the left and click <span className="text-[#FFFFFF]">Plan & Preview Costs</span> to inspect the estimated sequence before cryptographic execution.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
