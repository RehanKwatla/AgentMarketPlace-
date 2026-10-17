import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  Activity, 
  Layers, 
  Coins, 
  ArrowRight, 
  ArrowUpRight,
  ShieldCheck, 
  RotateCw,
  Cpu,
  Clock,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Send,
  FileText
} from 'lucide-react';
import { useMarketplace } from '../context/MarketplaceContext';
import { PageHeader } from '../components/ui/PageHeader';
import { StatusBadge } from '../components/ui/StatusBadge';
import { CallsOverTimeChart } from '../components/dashboard/CallsOverTimeChart';
import { PaymentActivityChart } from '../components/dashboard/PaymentActivityChart';
import { OutcomeDistributionChart } from '../components/dashboard/OutcomeDistributionChart';
import { SystemReadinessMatrix } from '../components/dashboard/SystemReadinessMatrix';
import { ExecutionLifecycle } from '../components/dashboard/ExecutionLifecycle';
import { MetricCardSkeleton, ActivityRowSkeleton } from '../components/ui/Skeleton';

export const Dashboard: React.FC = () => {
  const { 
    services, 
    ledger, 
    healthInfo, 
    paymentStatus, 
    pendingReconciliations, 
    totalVolumeUsdc,
    recentTasks,
    isLoading,
    refreshData,
    setSelectedLedgerRecord,
  } = useMarketplace();

  const navigate = useNavigate();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await refreshData();
    } finally {
      setIsRefreshing(false);
    }
  };

  const isHealthy = healthInfo?.status === 'healthy';
  const pendingCount = paymentStatus?.pending_reconciliations_count ?? Object.keys(pendingReconciliations).length;

  // Calculate genuine success rate from real ledger data
  const totalCalls = ledger.length;
  const successfulCalls = ledger.filter(r => r.status === 'paid').length;
  const hasTelemetry = totalCalls > 0;
  const successRate = hasTelemetry 
    ? ((successfulCalls / totalCalls) * 100).toFixed(1)
    : null;

  // Format relative timestamp helper
  const formatTimeAgo = (isoString?: string) => {
    if (!isoString) return 'recently';
    const ms = Date.now() - new Date(isoString).getTime();
    if (isNaN(ms)) return 'recently';
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${Math.max(1, seconds)}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <div className="space-y-8 max-w-[1600px] mx-auto pb-12 animate-fade-in">
      {/* 1. Restrained Header & Live Status */}
      <PageHeader
        title="Agent Marketplace"
        description="Discover registered services, execute paid tasks, and inspect every transaction across the Base Sepolia settlement ledger."
        badge={
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#DED8CD]/60 border border-[#CFC7BB] text-[11px] font-mono text-[#82786F]">
            <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-[#38865B] animate-pulse' : 'bg-[#B84040]'}`} />
            <span className="text-[#241B19] font-medium">{isHealthy ? 'Live Network' : 'Disconnected'}</span>
            <span className="text-[#CFC7BB]">•</span>
            <span className="text-[#7D292D] font-semibold">x402 v2</span>
          </div>
        }
        actions={
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="px-3 py-1.5 rounded-md bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono border border-[#CFC7BB] flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 shadow-xs"
              title="Refresh telemetry and ledger state"
            >
              <RotateCw className={`w-3.5 h-3.5 text-[#82786F] ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>{isRefreshing ? 'Syncing...' : 'Refresh'}</span>
            </button>

            <NavLink
              to="/buyer"
              className="px-3.5 py-1.5 rounded-md bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-semibold text-xs font-mono transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm"
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>Launch Task</span>
            </NavLink>
          </div>
        }
      />

      {/* 2. Key Metrics (~20-30% visual weight) */}
      <section aria-label="Key Operational Metrics">
        <div className="metric-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {isLoading ? (
            <>
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
              <MetricCardSkeleton />
            </>
          ) : (
            <>
          {/* Metric 1: Registered Services */}
          <div
            onClick={() => navigate('/marketplace')}
            className="card-lift group relative rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] hover:border-[#7D292D]/50 hover:bg-[#FFFFFF] shadow-sm p-5 transition-all cursor-pointer flex flex-col justify-between space-y-4"
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && navigate('/marketplace')}
            title="View active microservices in Marketplace"
          >
            <div className="flex items-center justify-between text-[#82786F]">
              <span className="text-xs font-mono uppercase tracking-wider text-[#82786F] group-hover:text-[#7D292D] transition-colors font-medium">
                Registered Services
              </span>
              <div className="p-1.5 rounded-md bg-[#DED8CD]/60 border border-[#CFC7BB] group-hover:border-[#7D292D]/40 transition-colors">
                <Layers className="w-4 h-4 text-[#7D292D]" />
              </div>
            </div>

            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold font-serif tracking-tight text-[#241B19]">
                  {services.length}
                </span>
                <span className="text-xs font-mono text-[#82786F]">
                  {services.length === 1 ? 'service' : 'services'}
                </span>
              </div>
              <p className="text-[11px] text-[#82786F] mt-1 line-clamp-1">
                Data, Scraping, and Inference agents
              </p>
            </div>

            <div className="pt-2 border-t border-[#CFC7BB]/60 flex items-center justify-between text-[11px] font-mono text-[#82786F] group-hover:text-[#7D292D] transition-colors">
              <span>Explore Marketplace</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </div>
          </div>

          {/* Metric 2: Total Recorded Calls */}
          <div
            onClick={() => navigate('/ledger')}
            className="card-lift group relative rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] hover:border-[#7D292D]/50 hover:bg-[#FFFFFF] shadow-sm p-5 transition-all cursor-pointer flex flex-col justify-between space-y-4"
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && navigate('/ledger')}
            title="Inspect all executed calls in Audit Ledger"
          >
            <div className="flex items-center justify-between text-[#82786F]">
              <span className="text-xs font-mono uppercase tracking-wider text-[#82786F] group-hover:text-[#7D292D] transition-colors font-medium">
                Total Recorded Calls
              </span>
              <div className="p-1.5 rounded-md bg-[#DED8CD]/60 border border-[#CFC7BB] group-hover:border-[#7D292D]/40 transition-colors">
                <Activity className="w-4 h-4 text-[#7D292D]" />
              </div>
            </div>

            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold font-serif tracking-tight text-[#241B19]">
                  {ledger.length}
                </span>
                <span className="text-xs font-mono text-[#82786F]">
                  {ledger.length === 1 ? 'handshake' : 'handshakes'}
                </span>
              </div>
              <p className="text-[11px] text-[#82786F] mt-1 line-clamp-1">
                Verified cryptographically via EIP-712
              </p>
            </div>

            <div className="pt-2 border-t border-[#CFC7BB]/60 flex items-center justify-between text-[11px] font-mono text-[#82786F] group-hover:text-[#7D292D] transition-colors">
              <span>View Audit Ledger</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </div>
          </div>

          {/* Metric 3: Total Paid in USDC */}
          <div
            onClick={() => navigate('/ledger')}
            className="card-lift group relative rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] hover:border-[#7D292D]/50 hover:bg-[#FFFFFF] shadow-sm p-5 transition-all cursor-pointer flex flex-col justify-between space-y-4"
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && navigate('/ledger')}
            title="View financial settlement activity in Ledger"
          >
            <div className="flex items-center justify-between text-[#82786F]">
              <span className="text-xs font-mono uppercase tracking-wider text-[#82786F] group-hover:text-[#7D292D] transition-colors font-medium">
                Total Paid in USDC
              </span>
              <div className="p-1.5 rounded-md bg-[#DED8CD]/60 border border-[#CFC7BB] group-hover:border-[#7D292D]/40 transition-colors">
                <Coins className="w-4 h-4 text-[#7D292D]" />
              </div>
            </div>

            <div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-3xl font-bold font-serif tracking-tight text-[#7D292D]">
                  ${totalVolumeUsdc}
                </span>
                <span className="text-xs font-mono text-[#82786F]">
                  USDC
                </span>
              </div>
              <p className="text-[11px] text-[#82786F] mt-1 line-clamp-1">
                Base Sepolia atomic micro-settlements
              </p>
            </div>

            <div className="pt-2 border-t border-[#CFC7BB]/60 flex items-center justify-between text-[11px] font-mono text-[#82786F] group-hover:text-[#7D292D] transition-colors">
              <span>Settlement Details</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </div>
          </div>

          {/* Metric 4: Success Rate (Strictly No Fabrication) */}
          <div
            className="card-lift relative rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-5 flex flex-col justify-between space-y-4"
            title={hasTelemetry ? `${successfulCalls} of ${totalCalls} calls completed successfully` : 'No execution calls recorded yet'}
          >
            <div className="flex items-center justify-between text-[#82786F]">
              <span className="text-xs font-mono uppercase tracking-wider text-[#82786F] font-medium">
                Success Rate
              </span>
              <div className="p-1.5 rounded-md bg-[#DED8CD]/60 border border-[#CFC7BB]">
                <ShieldCheck className="w-4 h-4 text-[#38865B]" />
              </div>
            </div>

            <div>
              {hasTelemetry ? (
                <div className="space-y-1">
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-3xl font-bold font-serif tracking-tight text-[#38865B]">
                      {successRate}%
                    </span>
                    <span className="text-xs font-mono text-[#82786F]">
                      ({successfulCalls}/{totalCalls})
                    </span>
                  </div>
                  <p className="text-[11px] text-[#82786F] line-clamp-1">
                    Verified successful service deliveries
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#DED8CD]/60 border border-[#CFC7BB] text-xs font-mono text-[#82786F]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#A86E24]" />
                    <span>No telemetry yet</span>
                  </div>
                  <p className="text-[11px] text-[#82786F] mt-1">
                    Requires recorded execution calls
                  </p>
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-[#CFC7BB]/60 flex items-center justify-between text-[11px] font-mono text-[#82786F]">
              <span>Telemetry State</span>
              <span className={hasTelemetry ? 'text-[#38865B] font-semibold' : 'text-[#A86E24] font-semibold'}>
                {hasTelemetry ? 'Active Stream' : 'Awaiting Data'}
              </span>
            </div>
          </div>
            </>
          )}
        </div>
      </section>

      {/* 3. Data Visualizations (~35% visual weight, intentional negative space) */}
      <section aria-label="Visualizations" className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#82786F]">
              Telemetry & Settlement Analytics
            </h2>
            <p className="text-[11px] text-[#82786F] mt-0.5">
              Live execution throughput, settlement curve, and outcome verification.
            </p>
          </div>
          <div className="text-[10px] font-mono text-[#82786F]">
            {ledger.length} events indexed
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          {/* Chart 1: Recorded Calls Over Time */}
          <div className="lg:col-span-7">
            <CallsOverTimeChart records={ledger} />
          </div>

          {/* Chart 3: Execution Outcome Distribution */}
          <div className="lg:col-span-5">
            <OutcomeDistributionChart records={ledger} />
          </div>

          {/* Chart 2: Cumulative Settlement Volume Over Time */}
          <div className="lg:col-span-12">
            <PaymentActivityChart records={ledger} totalVolumeUsdc={totalVolumeUsdc} />
          </div>
        </div>
      </section>

      {/* 4. Operational Information (~20-30% visual weight) */}
      <section aria-label="Operational Activity" className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Column 1: Recent Tasks */}
          <div className="lg:col-span-6 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#82786F]">
                  Recent Tasks
                </h3>
                <p className="text-[11px] text-[#82786F] mt-0.5">
                  Autonomous buyer formulations and multi-hop plans.
                </p>
              </div>

              <NavLink
                to="/buyer"
                className="text-[11px] font-mono text-[#7D292D] hover:underline flex items-center gap-1 font-semibold"
              >
                <span>Buyer Console</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </NavLink>
            </div>

            <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm overflow-hidden">
              {isLoading ? (
                <div className="divide-y divide-[#CFC7BB]/60">
                  <ActivityRowSkeleton />
                  <ActivityRowSkeleton />
                  <ActivityRowSkeleton />
                </div>
              ) : recentTasks.length === 0 ? (
                <div className="py-12 px-6 text-center space-y-3">
                  <div className="w-10 h-10 rounded-lg bg-[#DED8CD]/60 border border-[#CFC7BB] flex items-center justify-center text-[#82786F] mx-auto">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-[#241B19]">No buyer tasks recorded yet</p>
                    <p className="text-[11px] text-[#82786F] max-w-sm mx-auto">
                      Formulate and run autonomous multi-hop tasks with budget caps from the Buyer Console.
                    </p>
                  </div>
                  <div className="pt-1">
                    <NavLink
                      to="/buyer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono border border-[#CFC7BB] transition-colors shadow-xs"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-[#7D292D]" />
                      <span>Formulate New Task</span>
                    </NavLink>
                  </div>
                </div>
              ) : (
                <div className="divide-y divide-[#CFC7BB]/60">
                  {recentTasks.slice(0, 5).map((task) => (
                    <div
                      key={task.task_id}
                      onClick={() => navigate(`/results/${task.task_id}`)}
                      className="p-3.5 hover:bg-[#DED8CD]/40 transition-colors cursor-pointer flex items-center justify-between gap-3 group"
                    >
                      <div className="space-y-1 min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-semibold text-[#241B19] truncate group-hover:text-[#7D292D]">
                            {task.task_id}
                          </span>
                          <StatusBadge status={task.status} size="sm" />
                        </div>
                        <p className="text-xs text-[#82786F] truncate font-sans">
                          {task.prompt}
                        </p>
                        <div className="flex items-center gap-3 text-[10px] font-mono text-[#82786F]">
                          <span>{formatTimeAgo(task.timestamp)}</span>
                          <span>•</span>
                          <span>{task.services_used.length} services used</span>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <div className="font-mono text-xs font-bold text-[#7D292D]">
                          ${task.total_cost_usdc || '0.000'} USDC
                        </div>
                        <div className="text-[10px] font-mono text-[#82786F]">
                          Cap: ${task.budget_usdc}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Column 2: Recent Payment Activity */}
          <div className="lg:col-span-6 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#82786F]">
                  Recent Payment Activity
                </h3>
                <p className="text-[11px] text-[#82786F] mt-0.5">
                  Latest x402 settlement commitments and transaction links.
                </p>
              </div>

              <NavLink
                to="/ledger"
                className="text-[11px] font-mono text-[#7D292D] hover:underline flex items-center gap-1 font-semibold"
              >
                <span>Full Ledger ({ledger.length})</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </NavLink>
            </div>

            <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm overflow-hidden">
              {isLoading ? (
                <div className="divide-y divide-[#CFC7BB]/60">
                  <ActivityRowSkeleton />
                  <ActivityRowSkeleton />
                  <ActivityRowSkeleton />
                </div>
              ) : ledger.length === 0 ? (
                <div className="py-12 px-6 text-center space-y-3">
                  <div className="w-10 h-10 rounded-lg bg-[#DED8CD]/60 border border-[#CFC7BB] flex items-center justify-center text-[#82786F] mx-auto">
                    <Clock className="w-5 h-5" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-[#241B19]">No ledger records yet</p>
                    <p className="text-[11px] text-[#82786F] max-w-sm mx-auto">
                      Transactions will appear here as autonomous agents pay for microservices.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="divide-y divide-[#CFC7BB]/60">
                  {ledger.slice(0, 5).map((rec) => (
                    <div
                      key={rec.request_id}
                      onClick={() => setSelectedLedgerRecord(rec)}
                      className="p-3.5 hover:bg-[#DED8CD]/40 transition-colors cursor-pointer flex items-center justify-between gap-3 group"
                    >
                      <div className="space-y-1 min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-semibold text-[#241B19] truncate group-hover:text-[#7D292D]">
                            {rec.service_id}
                          </span>
                          <StatusBadge status={rec.status} size="sm" />
                        </div>
                        <div className="flex items-center gap-2 text-[10px] font-mono text-[#82786F]">
                          <span className="truncate max-w-[120px]">{rec.request_id}</span>
                          <span>•</span>
                          <span>{rec.latency_ms}ms</span>
                          <span>•</span>
                          <span>{formatTimeAgo(rec.timestamp)}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <div className="text-right">
                          <div className="font-mono text-xs font-bold text-[#7D292D]">
                            {rec.amount_paid} USDC
                          </div>
                          <div className="text-[10px] font-mono text-[#82786F]">
                            Settled
                          </div>
                        </div>

                        {/* Verified transaction link ONLY when tx_hash exists */}
                        {rec.tx_hash ? (
                          <a
                            href={`https://sepolia.basescan.org/tx/${rec.tx_hash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="p-1.5 rounded bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#82786F] hover:text-[#7D292D] border border-[#CFC7BB] transition-colors shadow-xs"
                            title={`Inspect tx ${rec.tx_hash} on BaseScan`}
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        ) : (
                          <div 
                            className="p-1.5 rounded text-[#82786F]"
                            title="Receipt verifiable in audit ledger"
                          >
                            <ArrowUpRight className="w-3.5 h-3.5 group-hover:text-[#7D292D] transition-colors" />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Execution lifecycle reference */}
        <ExecutionLifecycle />

        {/* Quick actions into the real workspace pages */}
        <section aria-label="Quick actions" className="space-y-3 animate-rise">
          <div>
            <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#82786F]">
              Quick Actions
            </h2>
            <p className="text-[11px] text-[#82786F] mt-0.5">
              Jump straight into the operational surfaces of the marketplace.
            </p>
          </div>

          <div className="metric-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <NavLink
              to="/marketplace"
              className="card-lift group rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-4 space-y-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7D292D]"
            >
              <div className="flex items-center justify-between">
                <Layers className="w-4 h-4 text-[#7D292D]" />
                <ArrowRight className="w-3.5 h-3.5 text-[#82786F] group-hover:translate-x-0.5 group-hover:text-[#7D292D] transition-transform" />
              </div>
              <div className="text-xs font-semibold text-[#241B19] font-sans">Explore Marketplace</div>
              <p className="text-[11px] text-[#82786F]">Browse registered services, prices, and declared capabilities.</p>
            </NavLink>

            <NavLink
              to="/buyer"
              className="card-lift group rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-4 space-y-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7D292D]"
            >
              <div className="flex items-center justify-between">
                <Send className="w-4 h-4 text-[#7D292D]" />
                <ArrowRight className="w-3.5 h-3.5 text-[#82786F] group-hover:translate-x-0.5 group-hover:text-[#7D292D] transition-transform" />
              </div>
              <div className="text-xs font-semibold text-[#241B19] font-sans">Submit a Buyer Task</div>
              <p className="text-[11px] text-[#82786F]">Formulate a multi-hop plan with an explicit budget cap.</p>
            </NavLink>

            <NavLink
              to="/payments"
              className="card-lift group rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-4 space-y-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7D292D]"
            >
              <div className="flex items-center justify-between">
                <Coins className="w-4 h-4 text-[#7D292D]" />
                <ArrowRight className="w-3.5 h-3.5 text-[#82786F] group-hover:translate-x-0.5 group-hover:text-[#7D292D] transition-transform" />
              </div>
              <div className="text-xs font-semibold text-[#241B19] font-sans">Inspect Payments</div>
              <p className="text-[11px] text-[#82786F]">Review authorizations, settlement attempts, and reconciliation queues.</p>
            </NavLink>

            <NavLink
              to="/ledger"
              className="card-lift group rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-4 space-y-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7D292D]"
            >
              <div className="flex items-center justify-between">
                <FileText className="w-4 h-4 text-[#7D292D]" />
                <ArrowRight className="w-3.5 h-3.5 text-[#82786F] group-hover:translate-x-0.5 group-hover:text-[#7D292D] transition-transform" />
              </div>
              <div className="text-xs font-semibold text-[#241B19] font-sans">View Audit Ledger</div>
              <p className="text-[11px] text-[#82786F]">Trace every recorded call, receipt, and settlement reference.</p>
            </NavLink>
          </div>
        </section>

        {/* System Readiness Matrix */}
        <SystemReadinessMatrix
          healthInfo={healthInfo}
          paymentStatus={paymentStatus}
          services={services}
          ledger={ledger}
          pendingReconciliationsCount={pendingCount}
        />
      </section>
    </div>
  );
};

export default Dashboard;
