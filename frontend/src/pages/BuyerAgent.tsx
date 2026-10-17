import React, { useState, useId } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Cpu, 
  ShieldCheck, 
  Sparkles, 
  AlertCircle, 
  ArrowRight,
  Database,
  Globe,
  Layers,
  CheckCircle2,
  Info
} from 'lucide-react';
import { useMarketplace } from '../context/MarketplaceContext';
import { PageHeader } from '../components/ui/PageHeader';
import { toAtomicUnits, validateTaskPrompt, validateBudget, fromAtomicUnits } from '../utils/monetary';

export const BuyerAgent: React.FC = () => {
  const navigate = useNavigate();
  const promptInputId = useId();
  const budgetInputId = useId();

  const {
    taskPrompt,
    setTaskPrompt,
    budgetUsdc,
    setBudgetUsdc,
    isSubmitting,
    taskError,
    services,
    selectedService,
    handleExecuteConfirmedTask,
  } = useMarketplace();

  const [localError, setLocalError] = useState<string | null>(null);

  // Exact prompt example specified in prompt requirements
  const promptPresets = [
    {
      title: 'Full Pipeline (Recommended)',
      prompt: 'Look up relevant structured data, extract useful details from an approved source, and summarize the findings. Keep total spending below 0.08 USDC.',
      budget: '0.08',
    },
    {
      title: 'Market Intelligence',
      prompt: 'Collect real-time cryptocurrency asset prices for ETH, evaluate recent volume changes, and synthesize summary metrics.',
      budget: '0.05',
    },
    {
      title: 'Web Content Extraction',
      prompt: 'Fetch remote documentation, extract clean structural markdown, and generate a concise executive brief.',
      budget: '0.03',
    },
  ];

  const handleSelectPreset = (preset: typeof promptPresets[0]) => {
    setTaskPrompt(preset.prompt);
    setBudgetUsdc(preset.budget);
    setLocalError(null);
  };

  // Authoritative integer atomic units computation (USDC 6 decimals, zero float arithmetic)
  const atomicBudget = toAtomicUnits(budgetUsdc || '0');
  const formattedAtomicDisplay = atomicBudget.toLocaleString();

  // Calculate estimated minimum pipeline cost from registered services
  const minEstimatedAtomic = services.reduce((acc, s) => {
    return acc + (s.price_atomic || s.price_base_units || toAtomicUnits(s.price_usdc));
  }, 0);
  const minEstimatedUsdc = fromAtomicUnits(minEstimatedAtomic);

  // Form submission handler
  const handleSubmitTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return; // Prevent duplicate clicks

    setLocalError(null);

    // 1. Validate prompt
    const promptValidation = validateTaskPrompt(taskPrompt);
    if (!promptValidation.isValid) {
      setLocalError(promptValidation.error || 'Please provide a valid task prompt.');
      return;
    }

    // 2. Validate budget
    const budgetValidation = validateBudget(budgetUsdc);
    if (!budgetValidation.isValid) {
      setLocalError(budgetValidation.error || 'Please provide a valid USDC budget.');
      return;
    }

    try {
      const result = await handleExecuteConfirmedTask(taskPrompt, budgetUsdc);
      if (result && result.task_id) {
        // 7. Navigate directly to /execution/:taskId using real task ID returned by backend
        navigate(`/execution/${result.task_id}`);
      }
    } catch (err: any) {
      setLocalError(err.message || 'Task creation failed on the backend API.');
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'data': return <Database className="w-3.5 h-3.5 text-cyan-400" />;
      case 'scraping': return <Globe className="w-3.5 h-3.5 text-amber-400" />;
      case 'inference': return <Cpu className="w-3.5 h-3.5 text-purple-400" />;
      default: return <Layers className="w-3.5 h-3.5 text-[#A3A3A3]" />;
    }
  };

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-12">
      {/* 1. Page Header */}
      <PageHeader
        title="Buyer Console"
        description="Formulate natural-language objectives, allocate a cryptographic USDC spending allowance, and dispatch autonomous task execution on Base Sepolia."
        badge={
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#DED8CD]/60 border border-[#CFC7BB] text-[11px] font-mono text-[#82786F]">
            <span className="w-2 h-2 rounded-full bg-[#38865B] animate-pulse" />
            <span className="text-[#241B19] font-medium">Autonomous Orchestrator</span>
            <span className="text-[#CFC7BB]">•</span>
            <span className="text-[#7D292D] font-semibold">Protocol x402 v2</span>
          </div>
        }
        actions={
          <div className="flex items-center gap-2 text-xs font-mono">
            <div className="bg-[#FFFFFF] px-3 py-1.5 rounded-md border border-[#CFC7BB] flex items-center gap-1.5 shadow-xs">
              <ShieldCheck className="w-3.5 h-3.5 text-[#38865B]" />
              <span className="text-[#82786F]">Boundary:</span>
              <span className="text-[#241B19] font-semibold">Hard Spending Cap</span>
            </div>
          </div>
        }
      />

      {/* 2. Main Console Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Focused Task Composer (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-6 space-y-5">
            <div>
              <h2 className="text-base font-serif font-bold text-[#241B19] flex items-center gap-2">
                <span>Task Formulation</span>
                <span className="text-[10px] font-mono text-[#38865B] px-2 py-0.5 rounded bg-[#E4EFE8] border border-[#A8B3A1]/70 font-medium">
                  Automatic Planning Mode
                </span>
              </h2>
              <p className="text-xs text-[#82786F] mt-1 font-sans">
                Describe what you want the autonomous agent system to accomplish. The orchestrator plans, selects compliant sellers, and manages atomic escrow.
              </p>
            </div>

            {/* Example Task Presets */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-mono text-[#82786F] uppercase tracking-wider block font-semibold">
                Quick Preset Templates:
              </span>
              <div className="flex flex-wrap gap-2">
                {promptPresets.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSelectPreset(preset)}
                    className="px-2.5 py-1 rounded-md bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono border border-[#CFC7BB] transition-colors cursor-pointer text-left shadow-xs"
                  >
                    <span>{preset.title}</span>
                    <span className="text-[#7D292D] font-semibold ml-1.5">({preset.budget} USDC)</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Error Banner */}
            {(localError || taskError) && (
              <div className="p-3.5 rounded-lg bg-[#FDE8E8] border border-[#F8B4B4] text-[#7D292D] text-xs flex items-start gap-2.5 shadow-xs">
                <AlertCircle className="w-4 h-4 text-[#B84040] shrink-0 mt-0.5" />
                <div className="flex-1 space-y-0.5">
                  <div className="font-semibold font-sans">Validation or API Error</div>
                  <div className="text-[11px] text-[#7D292D]/90 leading-relaxed font-mono">
                    {localError || taskError}
                  </div>
                </div>
              </div>
            )}

            {/* Task Form */}
            <form onSubmit={handleSubmitTask} className="space-y-4">
              {/* Natural Language Task Textarea */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label 
                    htmlFor={promptInputId} 
                    className="text-xs font-mono font-semibold text-[#241B19]"
                  >
                    Natural-Language Objective Prompt
                  </label>
                  <span className="text-[10px] font-mono text-[#82786F]">
                    {taskPrompt.length} characters (min 3)
                  </span>
                </div>
                <textarea
                  id={promptInputId}
                  value={taskPrompt}
                  onChange={(e) => {
                    setTaskPrompt(e.target.value);
                    if (localError) setLocalError(null);
                  }}
                  placeholder="e.g. Look up relevant structured data, extract useful details from an approved source, and summarize the findings. Keep total spending below 0.08 USDC."
                  rows={4}
                  className="w-full bg-[#FFFFFF] border border-[#CFC7BB] focus:border-[#7D292D] focus:ring-1 focus:ring-[#7D292D] rounded-lg p-3 text-xs font-sans text-[#241B19] placeholder-[#82786F] focus:outline-none transition-colors leading-relaxed resize-none shadow-xs"
                  required
                />
              </div>

              {/* Budget Allowance Input (USDC) */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label 
                    htmlFor={budgetInputId} 
                    className="text-xs font-mono font-semibold text-[#241B19]"
                  >
                    Maximum Budget Cap (USDC)
                  </label>
                  <span className="text-[10px] font-mono text-[#82786F]">
                    Atomic: {formattedAtomicDisplay} base units
                  </span>
                </div>
                <div className="relative">
                  <input
                    id={budgetInputId}
                    type="text"
                    value={budgetUsdc}
                    onChange={(e) => {
                      setBudgetUsdc(e.target.value);
                      if (localError) setLocalError(null);
                    }}
                    placeholder="0.05"
                    className="w-full bg-[#FFFFFF] border border-[#CFC7BB] focus:border-[#7D292D] focus:ring-1 focus:ring-[#7D292D] rounded-lg pl-3 pr-16 py-2 text-xs font-mono text-[#241B19] focus:outline-none transition-colors shadow-xs"
                    required
                  />
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-mono text-[#82786F] pointer-events-none font-semibold">
                    USDC
                  </div>
                </div>

                {/* Quick Budget Chips */}
                <div className="flex items-center gap-1.5 pt-1">
                  <span className="text-[10px] font-mono text-[#82786F]">Presets:</span>
                  {['0.02', '0.05', '0.08', '0.10'].map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setBudgetUsdc(amt)}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors cursor-pointer ${
                        budgetUsdc === amt
                          ? 'bg-[#7D292D] text-[#F7F4EE] font-semibold shadow-xs'
                          : 'bg-[#FFFFFF] text-[#241B19] hover:bg-[#DED8CD]/60 border border-[#CFC7BB]'
                      }`}
                    >
                      {amt} USDC
                    </button>
                  ))}
                </div>
              </div>

              {/* Submission Controls */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting || !taskPrompt.trim() || atomicBudget <= 0}
                  className="w-full py-2.5 rounded-lg bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-semibold text-xs font-mono transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-[#F7F4EE] border-t-transparent rounded-full animate-spin" />
                      <span>Dispatching Task to Orchestrator...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Run Task</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
                <p className="text-[10px] font-mono text-[#82786F] text-center mt-2">
                  Atomic budget lock applied. No funds charged until service verification.
                </p>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column: Orchestration Summary & Estimated Costs (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Preselected Service from Marketplace (if any) */}
          {selectedService && (
            <div className="rounded-xl border border-[#A8B3A1] bg-[#E4EFE8] p-4 space-y-2 shadow-xs">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#38865B]" />
                <span className="text-xs font-mono font-semibold text-[#38865B]">
                  Marketplace Pre-Selection Active
                </span>
              </div>
              <p className="text-[11px] text-[#241B19] leading-relaxed">
                Selected <span className="font-semibold">{selectedService.name}</span> ({selectedService.category}). The orchestrator prioritizes this provider category for step execution.
              </p>
            </div>
          )}

          {/* Selected-Services & Capabilities Summary */}
          <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-5 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#CFC7BB]/60">
              <div>
                <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#82786F]">
                  Available Service Capabilities
                </h3>
                <p className="text-[10px] text-[#82786F] mt-0.5">
                  Microservices available in registry for autonomous execution
                </p>
              </div>
              <span className="text-[10px] font-mono text-[#38865B] font-semibold">
                {services.length} sellers online
              </span>
            </div>

            <div className="divide-y divide-[#CFC7BB]/60">
              {services.map((svc) => (
                <div key={svc.service_id} className="py-2.5 flex items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="p-1.5 rounded-md bg-[#DED8CD]/60 border border-[#CFC7BB] shrink-0 text-[#7D292D]">
                      {getCategoryIcon(svc.category)}
                    </div>
                    <div className="min-w-0">
                      <div className="font-semibold text-[#241B19] truncate text-xs font-sans">
                        {svc.name}
                      </div>
                      <div className="text-[10px] font-mono text-[#82786F] truncate">
                        {svc.service_id} • {svc.category}
                      </div>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="font-mono text-xs font-bold text-[#7D292D]">
                      {svc.price_usdc} USDC
                    </div>
                    <div className="text-[9px] font-mono text-[#82786F]">
                      {(svc.price_atomic || svc.price_base_units || 0).toLocaleString()} units
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Estimated Cost vs Actual Paid Amount */}
            <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-2 shadow-xs">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-[#82786F]">Minimum Estimated Pipeline:</span>
                <span className="font-bold text-[#241B19]">~{minEstimatedUsdc} USDC</span>
              </div>
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-[#82786F]">Your Allocated Budget Cap:</span>
                <span className="font-bold text-[#7D292D]">${budgetUsdc || '0.00'} USDC</span>
              </div>
              <div className="pt-2 border-t border-[#CFC7BB]/60 flex items-start gap-1.5 text-[10px] text-[#82786F] font-mono">
                <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-[#7D292D]" />
                <span>
                  Authoritative cost is determined dynamically during step execution upon cryptographically verified output validation.
                </span>
              </div>
            </div>
          </div>

          {/* Backend Policy & Orchestration Specification */}
          <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-4 space-y-2.5 font-mono text-xs">
            <div className="flex items-center gap-1.5 text-[#241B19] font-semibold text-xs">
              <ShieldCheck className="w-3.5 h-3.5 text-[#38865B]" />
              <span>Orchestration Architecture</span>
            </div>

            <div className="space-y-1.5 text-[11px] text-[#82786F]">
              <div className="flex justify-between py-1 border-b border-[#CFC7BB]/60">
                <span className="text-[#82786F]">Planning Engine</span>
                <span className="text-[#241B19] font-semibold">Autonomous Multi-Hop</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#CFC7BB]/60">
                <span className="text-[#82786F]">Endpoint Pinning</span>
                <span className="text-[#241B19]">Orchestrator Managed</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#CFC7BB]/60">
                <span className="text-[#82786F]">Pre-flight Plan API</span>
                <span className="text-[#A86E24] font-medium">Not Exposed by Backend</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#CFC7BB]/60">
                <span className="text-[#82786F]">Settlement Asset</span>
                <span className="text-[#7D292D] font-semibold">Base Sepolia USDC</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BuyerAgent;
