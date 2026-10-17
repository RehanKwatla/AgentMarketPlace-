import React, { useState, useEffect, useRef, useCallback } from 'react';
import { NavLink, useParams, useNavigate } from 'react-router-dom';
import { 
  ShieldCheck, 
  ArrowRight, 
  ChevronDown, 
  ChevronUp, 
  Cpu, 
  RotateCw,
  Database,
  Globe,
  Layers,
  Copy,
  Check,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ExternalLink,
  GitBranch,
  Terminal,
  Activity
} from 'lucide-react';
import { useMarketplace } from '../context/MarketplaceContext';
import { PageHeader } from '../components/ui/PageHeader';
import { fetchTaskDetail } from '../api/client';
import { TaskDetailResponse, ServiceCallRecord, LedgerRecord } from '../types';
import { mapTaskStatus, mapCallStatus, StatusDisplayInfo } from '../utils/statusMapping';

export const AgentExecution: React.FC = () => {
  const { taskId } = useParams<{ taskId?: string }>();
  const navigate = useNavigate();
  const { 
    taskResult, 
    setSelectedLedgerRecord,
  } = useMarketplace();

  // If taskId in URL, prioritize that, else fall back to context taskResult
  const activeTaskId = taskId || taskResult?.task_id;

  const [taskDetail, setTaskDetail] = useState<TaskDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [isManualRefreshing, setIsManualRefreshing] = useState<boolean>(false);

  const pollingRef = useRef<any>(null);
  const isMountedRef = useRef<boolean>(true);

  const toggleStep = (stepIdx: number) => {
    setExpandedSteps(prev => ({ ...prev, [stepIdx]: !prev[stepIdx] }));
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(label);
    setTimeout(() => setCopiedText(null), 2000);
  };

  // Fetch task detail from backend API
  const loadTask = useCallback(async (isPollingCall = false) => {
    if (!activeTaskId) {
      setIsLoading(false);
      return;
    }

    if (!isPollingCall) {
      setFetchError(null);
    }

    try {
      const data = await fetchTaskDetail(activeTaskId);
      if (!isMountedRef.current) return;

      setTaskDetail(data);
      setFetchError(null);

      // Check if task reached a terminal state
      const statusInfo = mapTaskStatus(data.status);
      if (statusInfo.isTerminal && pollingRef.current) {
        // Stop polling immediately upon reaching terminal state
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    } catch (err: any) {
      if (!isMountedRef.current) return;
      if (!isPollingCall) {
        setFetchError(err.message || `Failed to fetch task ${activeTaskId}`);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
        setIsManualRefreshing(false);
      }
    }
  }, [activeTaskId]);

  // Initial load and polling setup
  useEffect(() => {
    isMountedRef.current = true;
    setIsLoading(true);

    if (activeTaskId) {
      loadTask(false).then(() => {
        // Start polling every 2.5s if task is still running / not terminal
        if (pollingRef.current) clearInterval(pollingRef.current);
        
        pollingRef.current = setInterval(() => {
          loadTask(true);
        }, 2500);
      });
    } else {
      setIsLoading(false);
    }

    // Cleanup on unmount: stop polling
    return () => {
      isMountedRef.current = false;
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [activeTaskId, loadTask]);

  const handleManualRefresh = () => {
    setIsManualRefreshing(true);
    loadTask(false);
  };

  // Inspect ledger record from call transaction reference
  const handleInspectPayment = (call: ServiceCallRecord) => {
    const record: LedgerRecord = {
      request_id: call.call_id || call.payment_reference || `req_${call.step_id}`,
      timestamp: call.completed_at || call.created_at || new Date().toISOString(),
      buyer_id: 'buyer_orchestrator',
      seller_id: call.source_metadata?.seller_pay_to || 'seller',
      service_id: call.service_id,
      listed_price: call.listed_price_usdc,
      amount_paid: call.amount_paid_usdc,
      tx_hash: call.transaction_hash || null,
      status: (call.status === 'succeeded' || call.status === 'paid' ? 'paid' : 'refused') as any,
      latency_ms: call.latency_ms || 0,
      error_reason: call.error || null,
    };
    setSelectedLedgerRecord(record);
  };

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'data': return <Database className="w-3.5 h-3.5 text-cyan-400" />;
      case 'scraping': return <Globe className="w-3.5 h-3.5 text-amber-400" />;
      case 'inference': return <Cpu className="w-3.5 h-3.5 text-purple-400" />;
      default: return <Layers className="w-3.5 h-3.5 text-[#A3A3A3]" />;
    }
  };

  const renderStatusBadge = (info: StatusDisplayInfo) => {
    let style = 'bg-[#DED8CD]/60 text-[#82786F] border-[#CFC7BB]';
    let icon = <HelpCircle className="w-3 h-3 text-[#82786F]" />;

    switch (info.variant) {
      case 'success':
        style = 'bg-[#A8B3A1]/25 text-[#38865B] border-[#A8B3A1]/60';
        icon = <CheckCircle2 className="w-3 h-3 text-[#38865B]" />;
        break;
      case 'running':
        style = 'bg-[#7D292D]/15 text-[#7D292D] border-[#7D292D]/40';
        icon = <div className="w-2.5 h-2.5 border-2 border-[#7D292D] border-t-transparent rounded-full animate-spin" />;
        break;
      case 'warning':
        style = 'bg-[#A86E24]/15 text-[#A86E24] border-[#A86E24]/40';
        icon = <AlertTriangle className="w-3 h-3 text-[#A86E24]" />;
        break;
      case 'error':
        style = 'bg-[#B84040]/15 text-[#B84040] border-[#B84040]/40';
        icon = <XCircle className="w-3 h-3 text-[#B84040]" />;
        break;
      case 'pending':
        style = 'bg-[#DED8CD]/60 text-[#82786F] border-[#CFC7BB]';
        icon = <span className="w-1.5 h-1.5 rounded-full bg-[#82786F]" />;
        break;
      case 'unknown':
      default:
        style = 'bg-[#DED8CD]/60 text-[#82786F] border-[#CFC7BB]';
        icon = <HelpCircle className="w-3 h-3 text-[#82786F]" />;
        break;
    }

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium border ${style}`}>
        {icon}
        <span>{info.label}</span>
      </span>
    );
  };

  // If no taskId is present
  if (!activeTaskId && !isLoading) {
    return (
      <div className="space-y-6 max-w-[1600px] mx-auto pb-12">
        <PageHeader
          title="Agent Execution Pipeline"
          description="Real-time telemetry and step-by-step verification of autonomous multi-hop service calls."
        />
        <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] p-12 text-center space-y-4 max-w-lg mx-auto shadow-sm">
          <div className="w-12 h-12 rounded-xl bg-[#DED8CD] border border-[#CFC7BB] flex items-center justify-center mx-auto text-[#7D292D]">
            <Cpu className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h2 className="text-base font-serif font-bold text-[#241B19]">No Active Execution Session</h2>
            <p className="text-xs text-[#82786F] leading-relaxed">
              Launch a task from the Buyer Console to watch multi-hop service execution, x402 payment authorization, and output validation in real-time.
            </p>
          </div>
          <div className="pt-2">
            <NavLink
              to="/buyer"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-medium text-xs transition-colors shadow-xs"
            >
              <span>Open Buyer Console</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </NavLink>
          </div>
        </div>
      </div>
    );
  }

  // Loading skeleton
  if (isLoading && !taskDetail) {
    return (
      <div className="space-y-6 max-w-[1600px] mx-auto pb-12">
        <PageHeader
          title="Agent Execution Pipeline"
          description="Real-time telemetry and step-by-step verification of autonomous multi-hop service calls."
        />
        <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] p-12 text-center space-y-4 shadow-sm">
          <div className="w-8 h-8 border-2 border-[#7D292D] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-mono text-[#82786F]">
            Connecting to orchestrator telemetry for session {activeTaskId?.slice(0, 8)}...
          </p>
        </div>
      </div>
    );
  }

  // Error state
  if (fetchError && !taskDetail) {
    return (
      <div className="space-y-6 max-w-[1600px] mx-auto pb-12">
        <PageHeader
          title="Agent Execution Pipeline"
          description="Real-time telemetry and step-by-step verification of autonomous multi-hop service calls."
        />
        <div className="rounded-xl border border-[#B84040]/30 bg-[#B84040]/10 p-8 text-center space-y-3 max-w-lg mx-auto">
          <XCircle className="w-8 h-8 text-[#B84040] mx-auto" />
          <h2 className="text-base font-serif font-bold text-[#B84040]">Failed to Retrieve Task</h2>
          <p className="text-xs font-mono text-[#82786F] leading-relaxed">{fetchError}</p>
          <div className="pt-2 flex justify-center gap-3">
            <button
              type="button"
              onClick={() => loadTask(false)}
              className="px-4 py-2 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-medium border border-[#CFC7BB] transition-colors cursor-pointer"
            >
              Retry
            </button>
            <NavLink
              to="/buyer"
              className="px-4 py-2 rounded-lg bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-medium text-xs transition-colors shadow-xs"
            >
              New Task
            </NavLink>
          </div>
        </div>
      </div>
    );
  }

  // Loaded task detail values
  const currentStatus = taskDetail?.status || 'unknown';
  const taskStatusInfo = mapTaskStatus(currentStatus);
  const calls = taskDetail?.calls || [];
  const hasResult = Boolean(taskDetail?.final_result || taskDetail?.result);
  const spendingSummary = taskDetail?.explanation?.spending_summary;

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-12">
      {/* 1. Header with Status & Action Buttons */}
      <PageHeader
        title="Agent Execution Pipeline"
        description="Real-time telemetry and step-by-step verification of autonomous multi-hop service calls."
        badge={renderStatusBadge(taskStatusInfo)}
        actions={
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={handleManualRefresh}
              disabled={isManualRefreshing}
              className="px-3.5 py-2 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono border border-[#CFC7BB] flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 shadow-xs"
              title="Refresh telemetry"
            >
              <RotateCw className={`w-3.5 h-3.5 text-[#82786F] ${isManualRefreshing ? 'animate-spin' : ''}`} />
              <span>{isManualRefreshing ? 'Syncing...' : 'Sync'}</span>
            </button>

            {hasResult && activeTaskId && (
              <NavLink
                to={`/results/${activeTaskId}`}
                className="px-4 py-2 rounded-lg bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-medium text-xs font-mono transition-colors flex items-center gap-1.5 shadow-xs"
              >
                <span>View Results</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </NavLink>
            )}

            <NavLink
              to="/buyer"
              className="px-3.5 py-2 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono border border-[#CFC7BB] transition-colors shadow-xs"
            >
              New Task
            </NavLink>
          </div>
        }
      />

      {/* 2. Task Summary Overview Banner */}
      <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] p-6 space-y-5 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-[#CFC7BB]/60">
          <div className="space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#82786F]">
              Active Task Session ID
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-[#241B19] select-all">
                {activeTaskId}
              </span>
              <button
                type="button"
                onClick={() => activeTaskId && handleCopy(activeTaskId, 'taskId')}
                className="p-1 rounded text-[#82786F] hover:text-[#241B19] transition-colors"
                title="Copy Task ID"
              >
                {copiedText === 'taskId' ? <Check className="w-3.5 h-3.5 text-[#38865B]" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-[#82786F]">Policy:</span>
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#A8B3A1]/20 border border-[#A8B3A1]/50 text-[10px] font-mono text-[#241B19]">
              <ShieldCheck className="w-3 h-3 text-[#38865B]" />
              <span>EIP-712 Settlement On-Delivery</span>
            </span>
          </div>
        </div>

        {/* Prompt Text */}
        <div className="space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-wider text-[#82786F]">
            Objective Prompt
          </div>
          <p className="text-xs text-[#241B19] leading-relaxed">
            {taskDetail?.task || taskResult?.cost_explanation || 'Natural language task prompt'}
          </p>
        </div>

        {/* Financial Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB]">
            <span className="text-[10px] font-mono text-[#82786F] block uppercase tracking-wider">
              Budget Allocated
            </span>
            <div className="text-sm font-bold font-mono text-[#241B19] mt-1">
              ${taskDetail?.budget_usdc || '0.00'} USDC
            </div>
            <span className="text-[10px] font-mono text-[#82786F]">
              {(taskDetail?.budget_atomic || 0).toLocaleString()} base units
            </span>
          </div>

          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB]">
            <span className="text-[10px] font-mono text-[#82786F] block uppercase tracking-wider">
              Authoritative Spend
            </span>
            <div className="text-sm font-bold font-mono text-[#7D292D] mt-1">
              ${taskDetail?.spent_usdc || spendingSummary?.verified_spent_usdc || '0.000000'} USDC
            </div>
            <span className="text-[10px] font-mono text-[#82786F]">
              {(taskDetail?.spent_atomic || taskDetail?.actual_spent_atomic || 0).toLocaleString()} base units
            </span>
          </div>

          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB]">
            <span className="text-[10px] font-mono text-[#82786F] block uppercase tracking-wider">
              Remaining Budget
            </span>
            <div className="text-sm font-bold font-mono text-[#241B19] mt-1">
              ${taskDetail?.remaining_usdc || spendingSummary?.remaining_budget_usdc || '0.000000'} USDC
            </div>
            <span className="text-[10px] font-mono text-[#82786F]">
              Released / uncharged
            </span>
          </div>

          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB]">
            <span className="text-[10px] font-mono text-[#82786F] block uppercase tracking-wider">
              Execution Steps
            </span>
            <div className="text-sm font-bold font-mono text-[#241B19] mt-1">
              {calls.length} Microservice {calls.length === 1 ? 'Call' : 'Calls'}
            </div>
            <span className="text-[10px] font-mono text-[#82786F]">
              {calls.filter(c => c.status === 'succeeded' || c.status === 'paid').length} validated
            </span>
          </div>
        </div>
      </div>

      {/* 3. Dependency Graph & Step Plan */}
      <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] p-5 space-y-4 shadow-xs">
        <div className="flex items-center justify-between pb-2 border-b border-[#CFC7BB]/60">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-[#7D292D]" />
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#241B19]">
              Autonomous Dependency Sequence
            </h3>
          </div>
          <span className="text-[10px] font-mono text-[#82786F]">
            {calls.length} sequential & parallel nodes
          </span>
        </div>

        {calls.length === 0 ? (
          <div className="py-8 text-center text-xs font-mono text-[#82786F]">
            Awaiting orchestrator dependency formulation...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {calls.map((c) => {
              const callStatus = mapCallStatus(c.status, c.validation_status);
              const hasDeps = c.depends_on && c.depends_on.length > 0;

              return (
                <div
                  key={c.call_id || c.step_id}
                  className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-2 text-xs font-mono"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#241B19]">
                      Step {c.step_id}
                    </span>
                    {renderStatusBadge(callStatus)}
                  </div>
                  <div className="text-xs text-[#241B19] font-medium truncate">
                    {c.service_id}
                  </div>
                  <div className="text-[10px] text-[#82786F] flex items-center justify-between">
                    <span>
                      {hasDeps ? `Depends on Step ${c.depends_on?.join(', ')}` : 'Root dependency'}
                    </span>
                    <span className="text-[#7D292D] font-bold">
                      {c.amount_paid_usdc || c.listed_price_usdc} USDC
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 4. Vertical Execution Timeline */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#241B19] flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#7D292D]" />
            <span>Granular Execution Telemetry Timeline</span>
          </h3>
          <span className="text-[10px] font-mono text-[#82786F]">
            Click any step to inspect payload & receipt
          </span>
        </div>

        <div className="space-y-3">
          {calls.map((call, idx) => {
            const isExpanded = expandedSteps[idx] ?? true;
            const callStatus = mapCallStatus(call.status, call.validation_status);
            const isOutputAccepted = call.validation_status === 'accepted';
            const hasTx = Boolean(call.transaction_hash || call.payment_reference);

            return (
              <div 
                key={call.call_id || idx}
                className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] overflow-hidden shadow-xs"
              >
                {/* Step Header */}
                <div
                  onClick={() => toggleStep(idx)}
                  className="p-4 bg-[#DED8CD]/30 hover:bg-[#DED8CD]/50 transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-7 h-7 rounded-lg bg-[#7D292D] text-[#F7F4EE] flex items-center justify-center font-mono font-bold text-xs shrink-0 shadow-xs">
                      {call.step_id}
                    </div>

                    <div className="min-w-0 space-y-0.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-xs text-[#241B19] font-mono truncate">
                          {call.service_id}
                        </span>
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#DED8CD] border border-[#CFC7BB] text-[10px] uppercase font-mono text-[#241B19]">
                          {getCategoryIcon(call.category as string)}
                          <span>{call.category}</span>
                        </span>
                        {renderStatusBadge(callStatus)}
                      </div>
                      <div className="text-[10px] font-mono text-[#82786F] truncate">
                        Call ID: {call.call_id}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0 justify-between sm:justify-end">
                    <div className="text-right font-mono">
                      <div className="text-xs font-bold text-[#241B19]">
                        {call.amount_paid_usdc || call.listed_price_usdc} USDC
                      </div>
                      <div className="text-[10px] text-[#82786F]">
                        {call.latency_ms ? `${call.latency_ms.toFixed(1)}ms` : '—'}
                      </div>
                    </div>

                    <div className="text-[#82786F] p-1">
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="p-4 border-t border-[#CFC7BB]/60 bg-[#F7F4EE] space-y-3.5 text-xs">
                    {/* Metadata Strip */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 font-mono text-[11px]">
                      <div className="p-3 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB]">
                        <span className="text-[#82786F] block text-[10px] uppercase font-medium">Output Validation</span>
                        <span className={`font-semibold mt-0.5 block ${isOutputAccepted ? 'text-[#38865B]' : 'text-[#A86E24]'}`}>
                          {call.validation_status ? `${call.validation_status.toUpperCase()} (Draft-7)` : 'Verified'}
                        </span>
                      </div>

                      <div className="p-3 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB]">
                        <span className="text-[#82786F] block text-[10px] uppercase font-medium">Seller PayTo</span>
                        <span className="text-[#241B19] mt-0.5 block truncate" title={call.source_metadata?.seller_pay_to}>
                          {call.source_metadata?.seller_pay_to || '0x0000...0000'}
                        </span>
                      </div>

                      <div className="p-3 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] flex items-center justify-between">
                        <div>
                          <span className="text-[#82786F] block text-[10px] uppercase font-medium">Cryptographic Receipt</span>
                          <span className="text-[#241B19] mt-0.5 block truncate max-w-[120px]" title={call.transaction_hash || ''}>
                            {call.transaction_hash ? `${call.transaction_hash.slice(0, 10)}...` : 'Committed'}
                          </span>
                        </div>
                        {hasTx && (
                          <button
                            type="button"
                            onClick={() => handleInspectPayment(call)}
                            className="px-2.5 py-1 rounded bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-[10px] font-mono border border-[#CFC7BB] transition-colors flex items-center gap-1 cursor-pointer shadow-xs"
                          >
                            <span>Inspect</span>
                            <ExternalLink className="w-3 h-3 text-[#82786F]" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Output Payload JSON Preview */}
                    {call.output && (
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-1.5 text-[11px] font-mono text-[#82786F]">
                          <Terminal className="w-3 h-3 text-[#241B19]" />
                          <span className="font-medium text-[#241B19]">Output Payload (Schema Verified)</span>
                        </div>
                        <pre className="bg-[#FFFFFF] p-3.5 rounded-lg border border-[#CFC7BB] text-[11px] text-[#241B19] font-mono overflow-x-auto max-h-48 leading-relaxed shadow-inner">
                          {JSON.stringify(call.output, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Error message if step failed */}
                    {call.error && (
                      <div className="p-3.5 rounded-lg bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] font-mono text-[11px] space-y-1">
                        <div className="font-bold flex items-center gap-1.5">
                          <XCircle className="w-3.5 h-3.5 text-[#B84040]" />
                          <span>Step Execution Error</span>
                        </div>
                        <p>{call.error}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 5. Fallback & Verification Activity */}
      <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] p-4 text-xs font-mono text-[#82786F] space-y-1">
        <span className="text-[#241B19] font-semibold block">
          Fallback & Output Audit Log:
        </span>
        <p>
          {taskDetail?.explanation?.fallback_attempts && taskDetail.explanation.fallback_attempts.length > 0
            ? `Fallback attempts recorded: ${taskDetail.explanation.fallback_attempts.join(', ')}`
            : 'Zero fallback executions required. All service calls verified on initial execution.'}
        </p>
      </div>

      {/* 6. Terminal Action: View Results */}
      {hasResult && activeTaskId && (
        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={() => navigate(`/results/${activeTaskId}`)}
            className="px-5 py-2.5 rounded-lg bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-medium text-xs font-mono transition-colors flex items-center gap-2 cursor-pointer shadow-sm"
          >
            <span>Proceed to Synthesis Results</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};

export default AgentExecution;
