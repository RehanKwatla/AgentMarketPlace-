import React, { useState, useEffect } from 'react';
import { Navbar } from '../components/Navbar';
import { ServiceCard } from '../components/ServiceCard';
import { LedgerTable } from '../components/LedgerTable';
import { fetchHealth, fetchServices, fetchLedger, fetchReputations, submitBuyerTask, fetchPaymentDashboard } from '../api/client';
import { ServiceDefinition, LedgerRecord, ReputationMetrics, TaskResponse, PaymentDashboardData } from '../types';

export const Dashboard: React.FC = () => {
  const [network, setNetwork] = useState('eip155:84532');
  const [isHealthy, setIsHealthy] = useState(false);
  const [services, setServices] = useState<ServiceDefinition[]>([]);
  const [ledger, setLedger] = useState<LedgerRecord[]>([]);
  const [reputations, setReputations] = useState<Record<string, ReputationMetrics>>({});
  const [dashboardMetrics, setDashboardMetrics] = useState<PaymentDashboardData | null>(null);

  // Task input state
  const [taskPrompt, setTaskPrompt] = useState('Collect market data on ETH and summarize key metrics');
  const [budgetUsdc, setBudgetUsdc] = useState('0.05');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [taskResult, setTaskResult] = useState<TaskResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setConfigError(null);
      const health = await fetchHealth();
      setIsHealthy(health.status === 'healthy');
      setNetwork(health.network || 'eip155:84532');

      const sData = await fetchServices();
      setServices(sData.services);

      const lData = await fetchLedger();
      setLedger(lData.records);

      const rData = await fetchReputations();
      setReputations(rData);

      try {
        const pData = await fetchPaymentDashboard();
        setDashboardMetrics(pData);
      } catch (pErr) {
        console.warn('Dashboard payment metrics fetch warning:', pErr);
      }
    } catch (err: any) {
      console.error('Failed to load marketplace data:', err);
      setIsHealthy(false);
      if (err instanceof Error && err.message.includes('VITE_API_BASE_URL is not set')) {
        setConfigError(err.message);
      }
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
    setSubmitError(null);
    try {
      const result = await submitBuyerTask(taskPrompt, budgetUsdc);
      setTaskResult(result);
      await loadData();
    } catch (err: any) {
      setSubmitError(err.message || 'Task execution failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar network={network} isHealthy={isHealthy} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-8">
        {/* Production Configuration Error Banner */}
        {configError && (
          <div className="bg-red-950/80 border border-red-500/50 text-red-200 px-5 py-4 rounded-xl flex items-start gap-4 shadow-xl">
            <span className="text-xl">⚠️</span>
            <div>
              <h3 className="font-semibold text-sm text-red-100">Production Deployment Configuration Required</h3>
              <p className="text-xs text-red-300 mt-1">{configError}</p>
            </div>
          </div>
        )}

        {/* Overview & Settlement Evidence Stats */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="glass-panel rounded-xl p-5 border border-slate-800 bg-slate-900/40">
            <div className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-1">
              Marketplace Settlement Spend
            </div>

            <div className="text-2xl font-bold font-mono text-emerald-400">
              {dashboardMetrics?.total_spend_usdc || '0.000000'} <span className="text-sm text-slate-400 font-sans">USDC</span>
            </div>
            <div className="text-xs text-slate-500 font-mono mt-2 flex justify-between">
              <span>{dashboardMetrics?.total_paid_calls || ledger.length} Calls Recorded</span>
              <span>{dashboardMetrics?.total_tasks || 0} Tasks</span>
            </div>
          </div>

          <div className="glass-panel rounded-xl p-5 border border-slate-800 bg-slate-900/40">
            <div className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-1">
              Settlement Evidence Status
            </div>
            <div className="space-y-1 text-xs font-mono">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Confirmed On-Chain:</span>
                <span className="text-slate-300 font-bold">{dashboardMetrics?.settlement_evidence.confirmed_on_chain || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Local Auth (rec_auth_*):</span>
                <span className="text-blue-400 font-bold">{dashboardMetrics?.settlement_evidence.local_authorization || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Unverified Hash:</span>
                <span className="text-amber-400 font-bold">{dashboardMetrics?.settlement_evidence.unverified_hash || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Pending Reconciliation:</span>
                <span className="text-purple-400 font-bold">{dashboardMetrics?.settlement_evidence.pending_reconciliation || 0}</span>
              </div>
            </div>
          </div>

          <div className="glass-panel rounded-xl p-5 border border-slate-800 bg-slate-900/40">
            <div className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-1">
              Protocol & Gate D Status
            </div>
            <div className="space-y-1.5 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-slate-400">Network:</span>
                <span className="text-slate-200">Base Sepolia (84532)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Token:</span>
                <span className="text-slate-200">USDC (6 decimals)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">x402 Protocol:</span>
                <span className="text-emerald-400">v2.0 Verified</span>
              </div>
              <div className="text-[11px] text-amber-400/90 bg-amber-950/30 px-2 py-0.5 rounded border border-amber-800/30 mt-1">
                Gate D: Base Sepolia live RPC gated (test mode)
              </div>
            </div>
          </div>
        </section>

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

            {submitError && (
              <div className="mb-4 p-3 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs font-mono">
                Error: {submitError}
              </div>
            )}

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
                <h3 className="text-sm font-semibold text-white">Multi-Hop Execution Console & Telemetry</h3>
                {taskResult && (
                  <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/20">
                    Status: {taskResult.status.toUpperCase()}
                  </span>
                )}
              </div>

              {taskResult ? (
                <div className="space-y-3 font-mono text-xs">
                  <div className="bg-slate-900/90 rounded-lg p-3 border border-slate-800">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Total Charged: <span className="text-emerald-400 font-bold">{taskResult.total_cost_usdc} USDC</span></span>
                      <span className="text-slate-400">Allocated Budget: <span className="text-slate-200 font-bold">{taskResult.budget_allocated_usdc} USDC</span></span>
                    </div>
                    <div className="text-slate-400 mt-1">Cost Breakdown: <span className="text-slate-200">{taskResult.cost_explanation}</span></div>
                  </div>

                  <div className="bg-slate-900/70 rounded-lg p-3 border border-slate-800">
                    <div className="text-slate-400 uppercase text-[10px] font-bold mb-1">Final Synthesized Result</div>
                    <p className="text-slate-100 font-sans leading-relaxed text-xs">{taskResult.final_result}</p>
                  </div>

                  {/* Multi-Hop Step Breakdown */}
                  <div>
                    <div className="text-slate-400 uppercase text-[10px] font-bold mb-2">Executed Hops Breakdown</div>
                    <div className="space-y-2">
                      {taskResult.executions.map((e) => (
                        <div key={e.step} className="bg-slate-900/60 p-2.5 rounded border border-slate-800 flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="w-5 h-5 rounded-full bg-blue-950 text-blue-400 border border-blue-800 flex items-center justify-center text-[10px] font-bold">
                              {e.step}
                            </span>
                            <span className="font-semibold text-slate-200">{e.service_id}</span>
                            <span className="text-slate-500">|</span>
                            <span className="text-slate-400">{e.price_paid_usdc} USDC</span>
                            <span className="text-slate-500">|</span>
                            <span className="text-slate-400">{e.latency_ms.toFixed(1)}ms</span>
                          </div>
                          <div>
                            <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                              {e.tx_hash ? (e.tx_hash.startsWith('rec_auth_') ? `Auth (${e.tx_hash.slice(0, 10)}...)` : `Tx (${e.tx_hash.slice(0, 8)}...)`) : 'No Tx'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
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
