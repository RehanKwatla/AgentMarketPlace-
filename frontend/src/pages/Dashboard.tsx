import React, { useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { ServiceCard } from '../components/ServiceCard';
import { LedgerTable } from '../components/LedgerTable';
import { fetchHealth, fetchServices, fetchLedger, fetchReputations, submitBuyerTask } from '../api/client';
import { ServiceDefinition, LedgerRecord, ReputationMetrics, TaskResponse } from '../types';

export const Dashboard: React.FC = () => {
  const [network, setNetwork] = useState('eip155:84532');
  const [isHealthy, setIsHealthy] = useState(false);
  const [services, setServices] = useState<ServiceDefinition[]>([]);
  const [ledger, setLedger] = useState<LedgerRecord[]>([]);
  const [reputations, setReputations] = useState<Record<string, ReputationMetrics>>({});
  
  // Task input state
  const [taskPrompt, setTaskPrompt] = useState('Collect market data on ETH and summarize key metrics');
  const [budgetUsdc, setBudgetUsdc] = useState('0.05');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [taskResult, setTaskResult] = useState<TaskResponse | null>(null);

  const loadData = async () => {
    try {
      const health = await fetchHealth();
      setIsHealthy(health.status === 'healthy');
      setNetwork(health.network || 'eip155:84532');

      const sData = await fetchServices();
      setServices(sData.services);

      const lData = await fetchLedger();
      setLedger(lData.records);

      const rData = await fetchReputations();
      setReputations(rData);
    } catch (err) {
      console.error('Failed to load marketplace data:', err);
      setIsHealthy(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleRunTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskPrompt || isSubmitting) return;

    setIsSubmitting(true);
    setTaskResult(null);
    try {
      const result = await submitBuyerTask(taskPrompt, budgetUsdc);
      setTaskResult(result);
      await loadData();
    } catch (err: any) {
      alert(`Error submitting task: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar network={network} isHealthy={isHealthy} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-8">
        {/* Marketplace Services Grid */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white">Registered Microservices</h2>
              <p className="text-xs text-slate-400">Autonomous seller agents participating in the x402 economy</p>
            </div>
            <span className="text-xs font-mono text-slate-400 bg-slate-900 px-3 py-1 rounded-full border border-slate-800">
              {services.length} Providers Active
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {services.map((s) => (
              <ServiceCard key={s.service_id} service={s} reputation={reputations[s.service_id]} />
            ))}
          </div>
        </section>

        {/* Task Trigger & Buyer Agent Panel */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-5 glass-panel rounded-xl p-6 border border-slate-800">
            <h2 className="text-lg font-bold text-white mb-1">Autonomous Buyer Agent</h2>
            <p className="text-xs text-slate-400 mb-5">
              Submit an objective. The buyer agent will discover services, negotiate x402 payments, and aggregate results.
            </p>

            <form onSubmit={handleRunTask} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-300 uppercase mb-1">Goal Prompt</label>
                <textarea
                  className="w-full h-24 bg-slate-900 border border-slate-700/80 rounded-lg p-3 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-sans resize-none"
                  value={taskPrompt}
                  onChange={(e) => setTaskPrompt(e.target.value)}
                  placeholder="e.g. Scrape latest web insights and generate inference summary"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 uppercase mb-1">Task Budget (USDC)</label>
                <input
                  type="text"
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-blue-500"
                  value={budgetUsdc}
                  onChange={(e) => setBudgetUsdc(e.target.value)}
                  placeholder="0.05"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs tracking-wide transition-colors disabled:opacity-50 font-mono uppercase"
              >
                {isSubmitting ? 'Purchasing & Executing Calls...' : 'Execute Pay-Per-Call Task'}
              </button>
            </form>
          </div>

          <div className="lg:col-span-7 glass-panel rounded-xl p-6 border border-slate-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-800">
                <h3 className="text-sm font-semibold text-white">Execution Console & Output</h3>
                {taskResult && (
                  <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
                    Status: {taskResult.status.toUpperCase()}
                  </span>
                )}
              </div>

              {taskResult ? (
                <div className="space-y-3 font-mono text-xs">
                  <div className="bg-slate-900/90 rounded-lg p-3 border border-slate-800">
                    <div className="text-slate-400">Total Spent: <span className="text-emerald-400 font-bold">{taskResult.total_cost_usdc} USDC</span></div>
                    <div className="text-slate-400 mt-1">Cost Breakdown: <span className="text-slate-200">{taskResult.cost_explanation}</span></div>
                  </div>

                  <div className="bg-slate-900/70 rounded-lg p-3 border border-slate-800">
                    <div className="text-slate-400 uppercase text-[10px] font-bold mb-1">Final Synthesized Result</div>
                    <p className="text-slate-100 font-sans leading-relaxed">{taskResult.final_result}</p>
                  </div>

                  <div className="text-slate-400">
                    Steps: {taskResult.executions.map(e => `${e.service_id} (${e.status})`).join(' -> ')}
                  </div>
                </div>
              ) : (
                <div className="text-slate-500 text-xs font-mono text-center py-16">
                  {isSubmitting ? (
                    <div className="space-y-2">
                      <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                      <p>Negotiating x402 challenge & settling Base Sepolia micropayments...</p>
                    </div>
                  ) : (
                    'No active execution. Trigger a task on the left to observe x402 payment flow.'
                  )}
                </div>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-500 font-mono flex justify-between">
              <span>Network: Base Sepolia (eip155:84532)</span>
              <span>x402 Protocol: v2.0</span>
            </div>
          </div>
        </section>

        {/* Ledger & Audit Trail */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white">Immutable Payment Ledger</h2>
              <p className="text-xs text-slate-400">Cryptographically verifiable audit log of all settled & refused service calls</p>
            </div>
            <button
              onClick={loadData}
              className="text-xs font-mono text-slate-400 hover:text-white bg-slate-900 px-3 py-1 rounded-md border border-slate-800 transition-colors"
            >
              Refresh Audit Log
            </button>
          </div>

          <LedgerTable records={ledger} />
        </section>
      </main>
    </div>
  );
};
