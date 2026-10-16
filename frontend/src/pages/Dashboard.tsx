import React, { useState, useEffect, useMemo } from 'react';
import { Navbar } from '../components/Navbar';
import { ServiceCard } from '../components/ServiceCard';
import { LedgerTable } from '../components/LedgerTable';
import { LedgerDetailModal } from '../components/LedgerDetailModal';
import { ServiceDetailModal } from '../components/ServiceDetailModal';
import { TaskPlanPreviewModal } from '../components/TaskPlanPreviewModal';
import { TaskResultsView } from '../components/TaskResultsView';
import { ReputationDashboardView } from '../components/ReputationDashboardView';
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
  PlannedStepEstimate,
  HealthInfo 
} from '../types';

import { 
  ArrowRight, 
  Layers, 
  Send, 
  FileText, 
  ShieldCheck, 
  AlertCircle, 
  RefreshCw,
  Cpu
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  // Navigation & View State
  const [activeTab, setActiveTab] = useState<string>('marketplace');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'price_asc' | 'price_desc' | 'name' | 'reputation'>('price_asc');

  // Backend Data State
  const [healthInfo, setHealthInfo] = useState<HealthInfo | null>(null);
  const [isHealthy, setIsHealthy] = useState<boolean>(false);
  const [services, setServices] = useState<ServiceDefinition[]>([]);
  const [ledger, setLedger] = useState<LedgerRecord[]>([]);
  const [reputations, setReputations] = useState<Record<string, ReputationMetrics>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Buyer Task Console State
  const [taskPrompt, setTaskPrompt] = useState<string>('Collect market data on ETH and summarize key metrics');
  const [budgetUsdc, setBudgetUsdc] = useState<string>('0.05');
  const [isPlanning, setIsPlanning] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [taskPlan, setTaskPlan] = useState<TaskPlanPreview | null>(null);
  const [taskResult, setTaskResult] = useState<TaskResponse | null>(null);
  const [taskError, setTaskError] = useState<string | null>(null);

  // Inspection Modals
  const [selectedService, setSelectedService] = useState<ServiceDefinition | null>(null);
  const [selectedLedgerRecord, setSelectedLedgerRecord] = useState<LedgerRecord | null>(null);

  // Load live data from FastAPI backend
  const loadData = async (silent = false) => {
    if (!silent) setIsLoading(true);
    setFetchError(null);
    try {
      const [hData, sData, lData, rData] = await Promise.all([
        fetchHealth().catch(() => ({ status: 'unreachable', version: 'unknown', network: 'eip155:84532' })),
        fetchServices().catch(() => ({ services: [], total: 0 })),
        fetchLedger().catch(() => ({ records: [], total: 0 })),
        fetchReputations().catch(() => ({}))
      ]);

      const healthy = hData.status === 'healthy';
      setIsHealthy(healthy);
      setHealthInfo(hData);
      setServices(sData.services || []);
      setLedger(lData.records || []);
      setReputations(rData || {});
    } catch (err: any) {
      console.error('Failed to load marketplace data:', err);
      setFetchError(err.message || 'Error communicating with backend');
      setIsHealthy(false);
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Refresh ledger and service health periodically without disruptive UI flicker
    const timer = setInterval(() => loadData(true), 8000);
    return () => clearInterval(timer);
  }, []);

  // Filtered and Sorted Services
  const filteredServices = useMemo(() => {
    return services.filter(s => {
      if (categoryFilter !== 'all' && s.category !== categoryFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q) ||
          s.category.toLowerCase().includes(q) ||
          s.service_id.toLowerCase().includes(q) ||
          s.endpoint_url.toLowerCase().includes(q)
        );
      }
      return true;
    }).sort((a, b) => {
      if (sortBy === 'price_asc') {
        return parseFloat(a.price_usdc) - parseFloat(b.price_usdc);
      } else if (sortBy === 'price_desc') {
        return parseFloat(b.price_usdc) - parseFloat(a.price_usdc);
      } else if (sortBy === 'name') {
        return a.name.localeCompare(b.name);
      } else if (sortBy === 'reputation') {
        const repA = reputations[a.service_id]?.reputation_score ?? 0;
        const repB = reputations[b.service_id]?.reputation_score ?? 0;
        return repB - repA;
      }
      return 0;
    });
  }, [services, categoryFilter, searchQuery, sortBy, reputations]);

  // Client-side Preview / Task Planning heuristic (aligned with backend TaskPlanner)
  const handlePreviewPlan = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskPrompt.trim()) return;

    setTaskError(null);
    setIsPlanning(true);

    try {
      const promptLower = taskPrompt.toLowerCase();
      const steps: PlannedStepEstimate[] = [];
      let stepCounter = 1;

      // Heuristic alignment matching backend/buyer/task_planner.py
      if (['market', 'price', 'eth', 'btc', 'financial', 'volume'].some(w => promptLower.includes(w))) {
        steps.push({
          step_number: stepCounter++,
          category: 'data',
          service_id: 'data_001',
          estimated_cost_usdc: '0.002',
          service_name: services.find(s => s.service_id === 'data_001')?.name || 'Market Data Provider'
        });
      }

      if (['scrape', 'web', 'article', 'url', 'extract'].some(w => promptLower.includes(w))) {
        steps.push({
          step_number: stepCounter++,
          category: 'scraping',
          service_id: 'scraping_001',
          estimated_cost_usdc: '0.003',
          service_name: services.find(s => s.service_id === 'scraping_001')?.name || 'Web Scraping Engine'
        });
      }

      // Always include inference/summary if requested or as aggregation step
      if (['summarize', 'analyze', 'infer', 'synthesize', 'takeaway'].some(w => promptLower.includes(w)) || steps.length === 0) {
        steps.push({
          step_number: stepCounter++,
          category: 'inference',
          service_id: 'inference_001',
          estimated_cost_usdc: '0.004',
          service_name: services.find(s => s.service_id === 'inference_001')?.name || 'Deep Inference & Synthesis'
        });
      }

      const totalEstimated = steps.reduce((acc, step) => acc + parseFloat(step.estimated_cost_usdc), 0);
      const budgetNum = parseFloat(budgetUsdc) || 0;
      const isAffordable = budgetNum >= totalEstimated;

      setTaskPlan({
        prompt: taskPrompt,
        budget_usdc: budgetUsdc,
        steps,
        estimated_total_usdc: totalEstimated.toFixed(6),
        is_affordable: isAffordable
      });
    } catch (err: any) {
      setTaskError('Failed to generate task plan: ' + err.message);
    } finally {
      setIsPlanning(false);
    }
  };

  // Submit Buyer Task to Backend API
  const handleExecuteConfirmedTask = async () => {
    if (!taskPrompt.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setTaskError(null);
    setTaskResult(null);

    try {
      const result = await submitBuyerTask(taskPrompt, budgetUsdc);
      setTaskResult(result);
      setTaskPlan(null); // Close confirmation modal
      // Refresh registry & ledger
      await loadData(true);
      // Switch view to display results or keep on console
      if (activeTab !== 'task-console') {
        setActiveTab('task-console');
      }
    } catch (err: any) {
      setTaskError(err.message || 'Error executing task on server');
    } finally {
      setIsSubmitting(false);
    }
  };

  // View specific ledger record from task results
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

  // Select a service from marketplace to use in Buyer Console
  const handleUseServiceInConsole = (service: ServiceDefinition) => {
    setTaskPrompt(`Query ${service.name} (${service.service_id}) and extract actionable insights`);
    setActiveTab('task-console');
  };

  // Platform Metrics
  const totalVerifiedSpend = useMemo(() => {
    return ledger
      .filter(r => r.status === 'paid' || r.status === 'paid output rejected')
      .reduce((sum, r) => sum + parseFloat(r.amount_paid || '0'), 0)
      .toFixed(6);
  }, [ledger]);

  const settledCount = useMemo(() => {
    return ledger.filter(r => r.status === 'paid' || r.status === 'paid output rejected').length;
  }, [ledger]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        network={healthInfo?.network || 'eip155:84532'}
        isHealthy={isHealthy}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Backend Connectivity Error Alert */}
        {fetchError && (
          <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-500/40 text-rose-300 text-xs font-mono flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>Backend Connectivity Alert: {fetchError}. Check FastAPI server at http://localhost:8000</span>
            </div>
            <button
              onClick={() => loadData(false)}
              className="px-3 py-1 bg-rose-900/50 hover:bg-rose-900 rounded border border-rose-700 text-white text-[11px]"
            >
              Retry
            </button>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB A: MARKETPLACE HOME */}
        {/* ========================================================================= */}
        {activeTab === 'marketplace' && (
          <div className="space-y-8 animate-fadeIn">
            {/* Hero Section */}
            <section className="relative overflow-hidden rounded-2xl glass-panel p-8 sm:p-10 border border-slate-800/80 bg-gradient-to-b from-slate-900/80 via-slate-950/70 to-slate-950">
              <div className="max-w-3xl space-y-4">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-xs font-mono text-blue-400">
                  <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                  <span>Autonomous Microservice Economy</span>
                  <span className="text-slate-600">|</span>
                  <span className="text-slate-400">Base Sepolia Testnet</span>
                </div>

                <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
                  Discover Services. <br />
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-300 to-cyan-400">
                    Pay Per Call via x402.
                  </span> <br />
                  Inspect Every Settlement.
                </h1>

                <p className="text-slate-400 text-sm leading-relaxed font-sans max-w-2xl">
                  A high-integrity agent marketplace where autonomous buyers decompose goals, 
                  settle micropayments over HTTP 402 with signed EIP-712 authorizations, 
                  and write verified proof to an immutable audit ledger.
                </p>

                <div className="pt-2 flex flex-wrap items-center gap-3">
                  <button
                    onClick={() => setActiveTab('task-console')}
                    className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-mono font-bold text-xs uppercase tracking-wide transition-all shadow-lg shadow-blue-500/20 flex items-center gap-2"
                  >
                    <span>Launch Buyer Task Console</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => setActiveTab('ledger')}
                    className="px-5 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 font-mono text-xs font-semibold transition-colors border border-slate-800 flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4 text-slate-400" />
                    <span>View Audit Ledger</span>
                  </button>
                </div>
              </div>

              {/* Verified Platform Metrics */}
              <div className="mt-8 pt-6 border-t border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <span className="text-[11px] font-mono text-slate-500 uppercase block">Registered Services</span>
                  <span className="text-xl font-bold font-mono text-white mt-0.5 block">{services.length} Active</span>
                </div>
                <div>
                  <span className="text-[11px] font-mono text-slate-500 uppercase block">Total Calls Processed</span>
                  <span className="text-xl font-bold font-mono text-blue-400 mt-0.5 block">{ledger.length}</span>
                </div>
                <div>
                  <span className="text-[11px] font-mono text-slate-500 uppercase block">Verified Settlements</span>
                  <span className="text-xl font-bold font-mono text-emerald-400 mt-0.5 block">{settledCount}</span>
                </div>
                <div>
                  <span className="text-[11px] font-mono text-slate-500 uppercase block">Total Verified Spend</span>
                  <span className="text-xl font-bold font-mono text-emerald-400 mt-0.5 block">{totalVerifiedSpend} USDC</span>
                </div>
              </div>
            </section>

            {/* Featured Workflow Bundles (Examples) */}
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono">
                    Featured Autonomous Bundles (Examples)
                  </h3>
                </div>
                <span className="text-[11px] text-slate-500 font-mono">Real pipeline recipes</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div 
                  className="glass-panel p-4 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition-all bg-slate-900/40"
                  onClick={() => {
                    setTaskPrompt('Collect market data on ETH and summarize key metrics');
                    setActiveTab('task-console');
                  }}
                >
                  <div className="flex items-center justify-between text-xs font-mono mb-2">
                    <span className="text-cyan-400 font-semibold uppercase">Market Briefing</span>
                    <span className="text-emerald-400 font-bold">~0.006 USDC</span>
                  </div>
                  <h4 className="text-sm font-bold text-white mb-1">Financial Data & Analysis</h4>
                  <p className="text-xs text-slate-400 line-clamp-2">
                    Pulls latest ticker metrics via Data Provider and produces structured bulleted takeaways via Inference.
                  </p>
                </div>

                <div 
                  className="glass-panel p-4 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition-all bg-slate-900/40"
                  onClick={() => {
                    setTaskPrompt('Scrape latest ethereum updates and extract technical highlights');
                    setActiveTab('task-console');
                  }}
                >
                  <div className="flex items-center justify-between text-xs font-mono mb-2">
                    <span className="text-amber-300 font-semibold uppercase">Web Synthesis</span>
                    <span className="text-emerald-400 font-bold">~0.007 USDC</span>
                  </div>
                  <h4 className="text-sm font-bold text-white mb-1">Live Web Scraping & Extract</h4>
                  <p className="text-xs text-slate-400 line-clamp-2">
                    Crawls target documentation via Scraping Seller and structures executive highlights via Inference.
                  </p>
                </div>

                <div 
                  className="glass-panel p-4 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition-all bg-slate-900/40"
                  onClick={() => {
                    setTaskPrompt('Synthesize recent macroeconomic indicators and generate predictions');
                    setActiveTab('task-console');
                  }}
                >
                  <div className="flex items-center justify-between text-xs font-mono mb-2">
                    <span className="text-purple-400 font-semibold uppercase">Deep Reasoning</span>
                    <span className="text-emerald-400 font-bold">~0.004 USDC</span>
                  </div>
                  <h4 className="text-sm font-bold text-white mb-1">Direct Inference Microservice</h4>
                  <p className="text-xs text-slate-400 line-clamp-2">
                    Runs multi-token inference with deterministic JSON output and prompt token validation.
                  </p>
                </div>
              </div>
            </section>

            {/* Service Directory Toolbar & Grid */}
            <section className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-white tracking-tight">Active Microservices Directory</h2>
                  <p className="text-xs text-slate-400">Autonomous seller agents participating in the x402 economy</p>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                  {/* Category Filter */}
                  <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 p-0.5">
                    {['all', 'data', 'scraping', 'inference'].map(cat => (
                      <button
                        key={cat}
                        onClick={() => setCategoryFilter(cat)}
                        className={`px-3 py-1 rounded-md capitalize transition-colors ${
                          categoryFilter === cat 
                            ? 'bg-blue-600 text-white font-bold' 
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>

                  {/* Sort Filter */}
                  <select
                    value={sortBy}
                    onChange={(e: any) => setSortBy(e.target.value)}
                    className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="price_asc">Price: Low to High</option>
                    <option value="price_desc">Price: High to Low</option>
                    <option value="reputation">Highest Reputation</option>
                    <option value="name">Service Name</option>
                  </select>

                  <button
                    onClick={() => loadData(false)}
                    className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-colors"
                    title="Refresh Registry"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Service Cards Grid */}
              {isLoading && services.length === 0 ? (
                <div className="text-center py-16 glass-panel rounded-2xl">
                  <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  <p className="text-xs font-mono text-slate-400">Querying service catalog from registry...</p>
                </div>
              ) : filteredServices.length === 0 ? (
                <div className="text-center py-16 glass-panel rounded-2xl border border-slate-800 text-slate-400 font-mono text-xs">
                  <Layers className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  <p className="text-slate-300 font-semibold">No services found matching filters</p>
                  <p className="text-slate-500 mt-1">Try resetting the category filter or search query.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {filteredServices.map(service => (
                    <ServiceCard
                      key={service.service_id}
                      service={service}
                      reputation={reputations[service.service_id]}
                      onSelect={handleUseServiceInConsole}
                      onViewDetail={(s) => setSelectedService(s)}
                    />
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB B: BUYER TASK CONSOLE */}
        {/* ========================================================================= */}
        {activeTab === 'task-console' && (
          <div className="space-y-8 animate-fadeIn">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Left Column: Task Input & Planning Form */}
              <div className="lg:col-span-5 space-y-6">
                <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-5">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Send className="w-4 h-4 text-blue-400" />
                      <h2 className="text-base font-bold text-white font-sans">Autonomous Buyer Task Console</h2>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed font-sans">
                      Provide a high-level goal and maximum budget. The Buyer Agent decomposes the task, negotiates x402 payment requirements with seller agents, and aggregates results.
                    </p>
                  </div>

                  <form onSubmit={handlePreviewPlan} className="space-y-4">
                    <div>
                      <label className="block text-xs font-mono text-slate-300 uppercase mb-1.5 flex items-center justify-between">
                        <span>Natural Language Prompt</span>
                        <span className="text-slate-500 text-[10px]">Min. 3 characters</span>
                      </label>
                      <textarea
                        className="w-full h-28 bg-slate-900/90 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-sans resize-none leading-relaxed"
                        value={taskPrompt}
                        onChange={(e) => setTaskPrompt(e.target.value)}
                        placeholder="e.g. Collect market data on ETH and summarize key metrics"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-slate-300 uppercase mb-1.5 flex items-center justify-between">
                        <span>Max Spending Budget (USDC)</span>
                        <span className="text-slate-500 text-[10px]">Base Sepolia USDC</span>
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          className="w-full bg-slate-900/90 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-blue-500 pl-8"
                          value={budgetUsdc}
                          onChange={(e) => setBudgetUsdc(e.target.value)}
                          placeholder="0.05"
                          required
                        />
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs font-mono">$</span>
                      </div>
                    </div>

                    {/* Pre-canned Example Prompts */}
                    <div>
                      <span className="text-[11px] font-mono text-slate-500 block mb-1.5 uppercase">Quick Examples:</span>
                      <div className="flex flex-wrap gap-1.5">
                        <button
                          type="button"
                          onClick={() => setTaskPrompt('Collect market data on ETH and summarize key metrics')}
                          className="text-[11px] font-mono px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
                        >
                          Market Data + Inference
                        </button>
                        <button
                          type="button"
                          onClick={() => setTaskPrompt('Scrape latest web article and synthesize highlights')}
                          className="text-[11px] font-mono px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
                        >
                          Web Scraping + Inference
                        </button>
                        <button
                          type="button"
                          onClick={() => setTaskPrompt('Direct inference analysis for DeFi protocols')}
                          className="text-[11px] font-mono px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
                        >
                          Direct Inference
                        </button>
                      </div>
                    </div>

                    {taskError && (
                      <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs font-mono">
                        {taskError}
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={isPlanning || isSubmitting}
                      className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs uppercase tracking-wide transition-all shadow-lg shadow-blue-500/20 font-mono flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      {isPlanning ? (
                        <>
                          <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          <span>Generating Execution Plan...</span>
                        </>
                      ) : (
                        <>
                          <span>Plan & Preview Costs</span>
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </form>
                </div>

                {/* Safety Protocol Banner */}
                <div className="p-5 rounded-2xl bg-slate-900/40 border border-slate-800 text-xs font-mono space-y-2 text-slate-400">
                  <div className="flex items-center gap-2 text-white font-semibold">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Enforced Payment Safety Boundaries</span>
                  </div>
                  <ul className="space-y-1 list-disc list-inside text-[11px] text-slate-400 font-sans">
                    <li>Budget locked atomically before service execution</li>
                    <li>Payments executed strictly on Base Sepolia (eip155:84532)</li>
                    <li>No charge on network or server execution failure</li>
                  </ul>
                </div>
              </div>

              {/* Right Column: Execution Output & Active Results */}
              <div className="lg:col-span-7">
                {taskResult ? (
                  <TaskResultsView
                    taskResult={taskResult}
                    onViewLedgerRecord={handleInspectLedgerRecord}
                  />
                ) : (
                  <div className="glass-panel rounded-2xl p-8 border border-slate-800 min-h-[420px] flex flex-col items-center justify-center text-center">
                    {isSubmitting ? (
                      <div className="space-y-4 max-w-sm">
                        <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
                        <h3 className="text-base font-bold text-white font-mono">Executing Autonomous Pipeline</h3>
                        <p className="text-xs text-slate-400 font-mono leading-relaxed">
                          Challenging seller endpoints via x402 v2, generating EIP-712 authorizations, and logging verified proofs...
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-3 max-w-sm">
                        <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500">
                          <Cpu className="w-6 h-6" />
                        </div>
                        <h3 className="text-sm font-bold text-slate-300 font-mono uppercase tracking-wide">
                          Awaiting Task Submission
                        </h3>
                        <p className="text-xs text-slate-500 leading-relaxed font-sans">
                          Describe your goal on the left and click "Plan & Preview Costs" to review the microservice pipeline before payment execution.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB C: PAYMENT LEDGER */}
        {/* ========================================================================= */}
        {activeTab === 'ledger' && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold tracking-tight text-white">Immutable Payment Ledger</h2>
                <p className="text-xs text-slate-400">Cryptographically verifiable audit log of all settled, refused, and failed calls</p>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-slate-400 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800">
                  Total Entries: <span className="text-white font-bold">{ledger.length}</span>
                </span>
                <button
                  onClick={() => loadData(false)}
                  className="px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 text-xs font-mono font-semibold transition-colors flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Refresh Ledger</span>
                </button>
              </div>
            </div>

            <LedgerTable
              records={ledger}
              onSelectRecord={(r) => setSelectedLedgerRecord(r)}
              selectedRequestId={selectedLedgerRecord?.request_id}
            />
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB D: REPUTATION & ANALYTICS */}
        {/* ========================================================================= */}
        {activeTab === 'reputation' && (
          <div className="animate-fadeIn">
            <ReputationDashboardView
              reputations={reputations}
              services={services}
              onSelectService={(s) => setSelectedService(s)}
            />
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB E: SELLER TOOLS */}
        {/* ========================================================================= */}
        {activeTab === 'seller-tools' && (
          <div className="animate-fadeIn">
            <SellerToolsView />
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB F: ABOUT / PROTOCOL DOCS */}
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
      <footer className="border-t border-slate-800/80 bg-slate-950/80 py-6 text-xs text-slate-500 font-mono mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            <span className="text-slate-400">DI-06 Pay-Per-Call Agent Economy</span>
            <span>—</span>
            <span>Base Sepolia USDC Testnet</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            <button onClick={() => setActiveTab('about')} className="hover:text-white transition-colors">
              Protocol Specs
            </button>
            <span>•</span>
            <button onClick={() => setActiveTab('seller-tools')} className="hover:text-white transition-colors">
              Seller Onboarding
            </button>
            <span>•</span>
            <span className="text-slate-600">x402 v2.0 Standard</span>
          </div>
        </div>
      </footer>

      {/* ========================================================================= */}
      {/* INTERACTIVE INSPECTION MODALS */}
      {/* ========================================================================= */}
      
      {/* 1. Service Detail Inspection Modal */}
      <ServiceDetailModal
        service={selectedService}
        reputation={selectedService ? reputations[selectedService.service_id] : undefined}
        onClose={() => setSelectedService(null)}
        onUseInTask={handleUseServiceInConsole}
      />

      {/* 2. Ledger Record Deep Dive Modal */}
      <LedgerDetailModal
        record={selectedLedgerRecord}
        onClose={() => setSelectedLedgerRecord(null)}
      />

      {/* 3. Task Plan Preview & Confirmation Modal */}
      <TaskPlanPreviewModal
        plan={taskPlan}
        onConfirm={handleExecuteConfirmedTask}
        onCancel={() => setTaskPlan(null)}
        isSubmitting={isSubmitting}
      />

    </div>
  );
};
