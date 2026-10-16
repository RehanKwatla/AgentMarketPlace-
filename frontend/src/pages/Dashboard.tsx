import React, { useState, useEffect, useMemo } from 'react';
import { Header } from '../components/Header';
import { PaymentTicker } from '../components/PaymentTicker';
import { PaymentsRace } from '../components/PaymentsRace';
import { ServicesLeaderboard } from '../components/ServicesLeaderboard';
import { MetricsStrip } from '../components/MetricsStrip';
import { IntegrationBanner } from '../components/IntegrationBanner';
import { ExploreServices } from '../components/ExploreServices';

import { LedgerDetailModal } from '../components/LedgerDetailModal';
import { ServiceDetailModal } from '../components/ServiceDetailModal';
import { TaskPlanPreviewModal } from '../components/TaskPlanPreviewModal';
import { TaskResultsView } from '../components/TaskResultsView';
import { SellerToolsView } from '../components/SellerToolsView';
import { AboutProtocolView } from '../components/AboutProtocolView';

import { 
  fetchHealth, 
  fetchServices, 
  fetchLedger, 
  fetchReputations, 
  submitBuyerTask, 
  fetchLedgerRecord 
} from '../api/client';

import { 
  ServiceDefinition, 
  LedgerRecord, 
  ReputationMetrics, 
  TaskResponse, 
  TaskPlanPreview, 
  PlannedStepEstimate 
} from '../types';

import { Send, ShieldCheck, Cpu } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('marketplace');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Backend Data State
  const [services, setServices] = useState<ServiceDefinition[]>([]);
  const [ledger, setLedger] = useState<LedgerRecord[]>([]);
  const [reputations, setReputations] = useState<Record<string, ReputationMetrics>>({});
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Buyer Task Console State
  const [taskPrompt, setTaskPrompt] = useState<string>('Collect market data on ETH and summarize key metrics');
  const [budgetUsdc, setBudgetUsdc] = useState<string>('0.05');
  const [isPlanning, setIsPlanning] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [taskPlan, setTaskPlan] = useState<TaskPlanPreview | null>(null);
  const [taskResult, setTaskResult] = useState<TaskResponse | null>(null);
  const [taskError, setTaskError] = useState<string | null>(null);

  // Modals
  const [selectedService, setSelectedService] = useState<ServiceDefinition | null>(null);
  const [selectedLedgerRecord, setSelectedLedgerRecord] = useState<LedgerRecord | null>(null);

  const loadData = async () => {
    setFetchError(null);
    try {
      const [, sData, lData, rData] = await Promise.all([
        fetchHealth().catch(() => ({ status: 'unreachable', version: 'unknown', network: 'eip155:84532' })),
        fetchServices().catch(() => ({ services: [], total: 0 })),
        fetchLedger().catch(() => ({ records: [], total: 0 })),
        fetchReputations().catch(() => ({}))
      ]);

      setServices(sData.services || []);
      setLedger(lData.records || []);
      setReputations(rData || {});
    } catch (err: any) {
      console.error('Failed to load marketplace data:', err);
      setFetchError(err.message || 'Error communicating with backend');
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(() => loadData(), 8000);
    return () => clearInterval(timer);
  }, []);

  const totalVolumeUsdc = useMemo(() => {
    return ledger
      .filter(r => r.status === 'paid' || r.status === 'paid output rejected')
      .reduce((sum, r) => sum + parseFloat(r.amount_paid || '0'), 0)
      .toFixed(4);
  }, [ledger]);

  const handlePreviewPlan = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskPrompt.trim()) return;

    setTaskError(null);
    setIsPlanning(true);

    try {
      const promptLower = taskPrompt.toLowerCase();
      const steps: PlannedStepEstimate[] = [];
      let stepCounter = 1;

      if (['market', 'price', 'eth', 'btc', 'financial', 'volume'].some(w => promptLower.includes(w))) {
        steps.push({
          step_number: stepCounter++,
          category: 'data',
          service_id: 'data_001',
          estimated_cost_usdc: '0.002',
          service_name: services.find(s => s.service_id === 'data_001')?.name || 'Alpha Financial Market Data'
        });
      }

      if (['scrape', 'web', 'article', 'url', 'extract'].some(w => promptLower.includes(w))) {
        steps.push({
          step_number: stepCounter++,
          category: 'scraping',
          service_id: 'scraping_001',
          estimated_cost_usdc: '0.003',
          service_name: services.find(s => s.service_id === 'scraping_001')?.name || 'Web Markdown & Content Extractor'
        });
      }

      if (['summarize', 'analyze', 'infer', 'synthesize', 'takeaway'].some(w => promptLower.includes(w)) || steps.length === 0) {
        steps.push({
          step_number: stepCounter++,
          category: 'inference',
          service_id: 'inference_001',
          estimated_cost_usdc: '0.004',
          service_name: services.find(s => s.service_id === 'inference_001')?.name || 'Agent Synthesis & Inference Engine'
        });
      }

      const totalEstimated = steps.reduce((acc, step) => acc + parseFloat(step.estimated_cost_usdc), 0);
      const budgetNum = parseFloat(budgetUsdc) || 0;

      setTaskPlan({
        prompt: taskPrompt,
        budget_usdc: budgetUsdc,
        steps,
        estimated_total_usdc: totalEstimated.toFixed(6),
        is_affordable: budgetNum >= totalEstimated
      });
    } catch (err: any) {
      setTaskError('Failed to generate task plan: ' + err.message);
    } finally {
      setIsPlanning(false);
    }
  };

  const handleExecuteConfirmedTask = async () => {
    if (!taskPrompt.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setTaskError(null);
    setTaskResult(null);

    try {
      const result = await submitBuyerTask(taskPrompt, budgetUsdc);
      setTaskResult(result);
      setTaskPlan(null);
      await loadData();
      if (activeTab !== 'task-console') {
        setActiveTab('task-console');
      }
    } catch (err: any) {
      setTaskError(err.message || 'Error executing task on server');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInspectLedgerRecord = async (requestId: string) => {
    try {
      const rec = ledger.find(r => r.request_id === requestId);
      if (rec) {
        setSelectedLedgerRecord(rec);
      } else {
        const fetched = await fetchLedgerRecord(requestId);
        setSelectedLedgerRecord(fetched);
      }
    } catch (err) {
      console.error('Failed to inspect ledger record:', err);
    }
  };

  const handleUseService = (service: ServiceDefinition) => {
    setTaskPrompt(`Query ${service.name} (${service.service_id}) and extract actionable insights`);
    setActiveTab('task-console');
  };

  return (
    <div className="min-h-screen bg-[#101112] text-[#F5F5F5] flex flex-col font-sans selection:bg-[#FF982E] selection:text-[#101112]">
      {/* 1. Header with #171819 Background and Orange Robot Logo */}
      <Header
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onGetStarted={() => setActiveTab('task-console')}
      />

      {/* 2. Horizontal Payment Ticker */}
      <PaymentTicker
        records={ledger}
        totalVolumeUsdc={totalVolumeUsdc}
      />

      {/* Main Workspace */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 py-5 space-y-5">
        
        {fetchError && (
          <div className="p-3 rounded-lg bg-[#E15D52]/10 border border-[#E15D52]/30 text-[#E15D52] text-xs font-mono flex items-center justify-between">
            <span>Backend Notice: {fetchError}. Check FastAPI server at http://localhost:8000</span>
            <button
              onClick={() => loadData()}
              className="px-2 py-0.5 bg-[#E15D52] text-[#101112] font-bold rounded text-[11px]"
            >
              Retry
            </button>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW A: EXACT MATCH FOR SCREENSHOT DASHBOARD */}
        {/* ========================================================================= */}
        {activeTab === 'marketplace' && (
          <div className="space-y-4">
            {/* Upper Two-Column Layout: Left (66%) Payments Race + Right (34%) Services Leaderboard */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-stretch">
              <div className="lg:col-span-8">
                <PaymentsRace
                  humanTxCount={1420}
                  agentTxCount={3891 + ledger.length}
                />
              </div>

              <div className="lg:col-span-4">
                <ServicesLeaderboard
                  services={services}
                  reputations={reputations}
                  onSelectService={(s) => setSelectedService(s)}
                />
              </div>
            </div>

            {/* Bottom 4 Metrics Strip */}
            <MetricsStrip
              totalVolumeUsdc={totalVolumeUsdc}
              totalTransactions={ledger.length}
              activeAgentsCount={services.length}
            />

            {/* Agent Integration Banner */}
            <IntegrationBanner />

            {/* BROWSE: Explore Services Table */}
            <div className="pt-2">
              <ExploreServices
                services={services}
                reputations={reputations}
                onSelectService={(s) => setSelectedService(s)}
                onRunService={handleUseService}
              />
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW B: BUYER TASK CONSOLE */}
        {/* ========================================================================= */}
        {activeTab === 'task-console' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-5 bg-[#171819] border border-[#303133] rounded-lg p-5 space-y-4 font-mono text-xs">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Send className="w-4 h-4 text-[#FF982E]" />
                    <h2 className="text-sm font-bold text-[#F5F5F5] font-sans">Autonomous Buyer Task Console</h2>
                  </div>
                  <p className="text-[11px] text-[#96989D] font-sans leading-relaxed">
                    Set a prompt and budget. The autonomous buyer agent calls x402 endpoints and writes settled proofs to the ledger.
                  </p>
                </div>

                <form onSubmit={handlePreviewPlan} className="space-y-3">
                  <div>
                    <label className="block text-[#96989D] uppercase text-[10px] mb-1">Objective Prompt</label>
                    <textarea
                      value={taskPrompt}
                      onChange={(e) => setTaskPrompt(e.target.value)}
                      className="w-full h-24 bg-[#101112] border border-[#303133] rounded p-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E] resize-none font-sans"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-[#96989D] uppercase text-[10px] mb-1">Spending Budget (USDC)</label>
                    <input
                      type="text"
                      value={budgetUsdc}
                      onChange={(e) => setBudgetUsdc(e.target.value)}
                      className="w-full bg-[#101112] border border-[#303133] rounded p-2 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E]"
                      required
                    />
                  </div>

                  {taskError && (
                    <div className="p-2.5 rounded bg-[#E15D52]/10 border border-[#E15D52]/30 text-[#E15D52]">
                      {taskError}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isPlanning || isSubmitting}
                    className="w-full py-2.5 rounded bg-[#FF982E] hover:bg-[#FF982E]/90 text-[#101112] font-bold text-xs uppercase tracking-wide transition-all shadow-md shadow-[#FF982E]/20"
                  >
                    {isPlanning ? 'Planning Execution...' : 'Plan & Preview Costs'}
                  </button>
                </form>

                <div className="pt-2 border-t border-[#303133] text-[10px] text-[#96989D] space-y-1">
                  <div className="text-[#F5F5F5] font-bold flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-[#58B779]" />
                    <span>Enforced Payment Safety Boundaries</span>
                  </div>
                  <p>Payments run strictly on Base Sepolia USDC. No charge on failure.</p>
                </div>
              </div>

              <div className="lg:col-span-7">
                {taskResult ? (
                  <TaskResultsView
                    taskResult={taskResult}
                    onViewLedgerRecord={handleInspectLedgerRecord}
                  />
                ) : (
                  <div className="bg-[#171819] border border-[#303133] rounded-lg p-10 min-h-[380px] flex flex-col items-center justify-center text-center font-mono text-xs text-[#96989D]">
                    {isSubmitting ? (
                      <div className="space-y-3">
                        <div className="w-8 h-8 border-2 border-[#FF982E] border-t-transparent rounded-full animate-spin mx-auto" />
                        <p className="text-[#F5F5F5] font-bold">Challenging seller endpoints via x402 v2...</p>
                      </div>
                    ) : (
                      <div className="space-y-2 max-w-sm">
                        <Cpu className="w-8 h-8 text-[#96989D] mx-auto" />
                        <p className="text-[#F5F5F5] font-bold">Awaiting Task Submission</p>
                        <p className="text-[11px] font-sans">Click "Plan & Preview Costs" to review the microservice pipeline before authorization.</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW C: SELLER TOOLS */}
        {/* ========================================================================= */}
        {activeTab === 'seller-tools' && (
          <div className="animate-fadeIn">
            <SellerToolsView />
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW D: ABOUT PROTOCOL */}
        {/* ========================================================================= */}
        {activeTab === 'about' && (
          <div className="animate-fadeIn">
            <AboutProtocolView
              onGoToConsole={() => setActiveTab('task-console')}
              onGoToMarketplace={() => setActiveTab('marketplace')}
            />
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-[#303133] bg-[#171819] py-6 text-xs text-[#96989D] font-mono mt-12">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF982E]" />
            <span className="text-[#F5F5F5] font-bold">Agentic Market</span>
            <span>—</span>
            <span>DISCOVER → PAY → GET RESULTS</span>
          </div>

          <div className="flex items-center gap-4 text-[#96989D] text-[11px]">
            <button onClick={() => setActiveTab('about')} className="hover:text-[#F5F5F5]">About</button>
            <span>•</span>
            <button onClick={() => setActiveTab('seller-tools')} className="hover:text-[#F5F5F5]">Seller Tools</button>
            <span>•</span>
            <span className="text-[#96989D]">Base Sepolia USDC</span>
          </div>
        </div>
      </footer>

      {/* Modals */}
      <ServiceDetailModal
        service={selectedService}
        reputation={selectedService ? reputations[selectedService.service_id] : undefined}
        onClose={() => setSelectedService(null)}
        onUseInTask={handleUseService}
      />

      <LedgerDetailModal
        record={selectedLedgerRecord}
        onClose={() => setSelectedLedgerRecord(null)}
      />

      <TaskPlanPreviewModal
        plan={taskPlan}
        onConfirm={handleExecuteConfirmedTask}
        onCancel={() => setTaskPlan(null)}
        isSubmitting={isSubmitting}
      />

    </div>
  );
};
