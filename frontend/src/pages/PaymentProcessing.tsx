import React, { useState, useMemo, useEffect } from 'react';
import { NavLink, useSearchParams } from 'react-router-dom';
import { 
  Coins, 
  ShieldCheck, 
  CheckCircle2, 
  RefreshCw, 
  ArrowRight,
  Zap,
  RotateCw,
  Search,
  ExternalLink,
  SlidersHorizontal,
  Info,
  Clock,
  Check
} from 'lucide-react';
import { useMarketplace } from '../context/MarketplaceContext';
import { PaymentsRace } from '../components/PaymentsRace';
import { StatusBadge } from '../components/ui/StatusBadge';
import { X402PaymentModal, PaymentDisplayRecord } from '../components/X402PaymentModal';
import { mapPaymentStatus } from '../utils/statusMapping';
import { LedgerRecord } from '../types';

export const PaymentProcessing: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const taskIdParam = searchParams.get('taskId');
  const requestIdParam = searchParams.get('requestId');

  const { 
    ledger, 
    totalVolumeUsdc, 
    paymentStatus, 
    pendingReconciliations, 
    handleReconcileAttempt,
    refreshData,
    fetchError
  } = useMarketplace();

  // Local component state
  const [reconcilingId, setReconcilingId] = useState<string | null>(null);
  const [reconcileSuccess, setReconcileSuccess] = useState<string | null>(null);
  const [reconcileError, setReconcileError] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [filterTab, setFilterTab] = useState<'all' | 'settled' | 'pending' | 'rejected' | 'failed'>('all');
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [selectedPaymentRecord, setSelectedPaymentRecord] = useState<PaymentDisplayRecord | LedgerRecord | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Auto-inspect request ID from URL query param if present
  useEffect(() => {
    if (requestIdParam && ledger.length > 0) {
      const match = ledger.find(r => r.request_id === requestIdParam);
      if (match) {
        setSelectedPaymentRecord(match);
      }
    }
  }, [requestIdParam, ledger]);

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleSyncEngine = async () => {
    setIsSyncing(true);
    try {
      await refreshData();
    } finally {
      setIsSyncing(false);
    }
  };

  const onReconcileClick = async (attemptId: string) => {
    setReconcilingId(attemptId);
    setReconcileSuccess(null);
    setReconcileError(null);
    try {
      const res = await handleReconcileAttempt(attemptId);
      setReconcileSuccess(`Attempt ${attemptId} reconciled successfully: ${res.outcome || 'Settled'}`);
    } catch (err: any) {
      setReconcileError(err.message || `Reconciliation failed for ${attemptId}`);
    } finally {
      setReconcilingId(null);
    }
  };

  const pendingEntries = Object.entries(pendingReconciliations);

  // Authoritative financial calculations
  const settledRecords = useMemo(() => {
    return ledger.filter(r => r.status === 'paid');
  }, [ledger]);

  const rejectedOutputRecords = useMemo(() => {
    return ledger.filter(r => r.status === 'paid output rejected');
  }, [ledger]);

  const failedUnchargedRecords = useMemo(() => {
    return ledger.filter(r => r.status === 'refused' || r.status === 'failed and not charged');
  }, [ledger]);

  // Verified settled spend in USDC
  const verifiedSettledUsdc = totalVolumeUsdc;

  // Total pending / uncertain amount held in suspense
  const pendingSuspenseUsdc = useMemo(() => {
    return pendingEntries.reduce((sum, [, details]) => {
      const amt = typeof details === 'object' && details.amount_usdc ? parseFloat(details.amount_usdc) : 0;
      return sum + amt;
    }, 0).toFixed(6);
  }, [pendingEntries]);

  // Uncharged / released budget sum
  const unchargedReleasedUsdc = useMemo(() => {
    return failedUnchargedRecords.reduce((sum, r) => {
      const listed = parseFloat(r.listed_price || '0');
      return sum + listed;
    }, 0).toFixed(6);
  }, [failedUnchargedRecords]);

  // Filtered payment records
  const filteredRecords = useMemo(() => {
    return ledger.filter(record => {
      // 1. Task ID query param filter
      if (taskIdParam) {
        const matchesTaskId = (record.task_id && record.task_id.toLowerCase().includes(taskIdParam.toLowerCase())) ||
                              (record.request_id.toLowerCase().includes(taskIdParam.toLowerCase()));
        if (!matchesTaskId) return false;
      }

      // 2. Status tab filter
      if (filterTab === 'settled' && record.status !== 'paid') return false;
      if (filterTab === 'rejected' && record.status !== 'paid output rejected') return false;
      if (filterTab === 'failed' && record.status !== 'refused' && record.status !== 'failed and not charged') return false;

      // 3. Search query filter
      if (searchFilter.trim()) {
        const q = searchFilter.toLowerCase().trim();
        const matchesQuery = 
          record.request_id.toLowerCase().includes(q) ||
          record.service_id.toLowerCase().includes(q) ||
          (record.seller_id && record.seller_id.toLowerCase().includes(q)) ||
          (record.task_id && record.task_id.toLowerCase().includes(q)) ||
          (record.tx_hash && record.tx_hash.toLowerCase().includes(q));
        if (!matchesQuery) return false;
      }

      return true;
    });
  }, [ledger, taskIdParam, filterTab, searchFilter]);

  const clearTaskFilter = () => {
    const next = new URLSearchParams(searchParams);
    next.delete('taskId');
    setSearchParams(next);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans pb-12">
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#CFC7BB] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-serif font-bold text-[#241B19] flex items-center gap-2">
              <Coins className="w-6 h-6 text-[#7D292D]" />
              <span>x402 Payment Processing & Settlement</span>
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#DED8CD] text-[#241B19] border border-[#CFC7BB]">
              Protocol: x402 v{paymentStatus?.protocol_version || '2.0'}
            </span>
          </div>
          <p className="text-xs text-[#82786F] mt-1 leading-relaxed">
            Transparent lifecycle visibility of EIP-712 cryptographic authorizations, micropayment settlement engine, and suspense reconciliation queue.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          {taskIdParam && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] text-[#241B19] text-xs shadow-xs">
              <span>Task: {taskIdParam.slice(0, 8)}...</span>
              <button 
                type="button"
                onClick={clearTaskFilter} 
                className="text-[#82786F] hover:text-[#241B19] font-bold ml-1 cursor-pointer"
                title="Clear task filter"
                aria-label="Clear task filter"
              >
                ✕
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={handleSyncEngine}
            disabled={isSyncing}
            className="px-3.5 py-2 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB] flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 shadow-xs"
            title="Fetch authoritative status from backend"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-[#7D292D]' : 'text-[#82786F]'}`} />
            <span>{isSyncing ? 'Syncing...' : 'Sync Engine'}</span>
          </button>
        </div>
      </div>

      {/* Backend error notification */}
      {fetchError && (
        <div className="p-4 rounded-xl bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-bold">Backend Sync Notice:</span>
            <span>{fetchError}</span>
          </div>
          <button 
            type="button"
            onClick={() => refreshData()} 
            className="px-3 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#B84040] border border-[#B84040]/40 text-xs font-mono transition-colors cursor-pointer ml-3 shrink-0 shadow-xs"
          >
            Retry
          </button>
        </div>
      )}

      {/* Reconcile Banners */}
      {reconcileSuccess && (
        <div className="p-4 rounded-xl bg-[#A8B3A1]/20 border border-[#A8B3A1]/50 text-[#38865B] text-xs font-mono flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-[#38865B] shrink-0" />
            <span>{reconcileSuccess}</span>
          </div>
          <button 
            type="button"
            onClick={() => setReconcileSuccess(null)} 
            className="text-[#38865B] hover:text-[#241B19] font-bold ml-2 cursor-pointer p-1"
            aria-label="Dismiss success notification"
          >
            ✕
          </button>
        </div>
      )}

      {reconcileError && (
        <div className="p-4 rounded-xl bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] text-xs font-mono flex items-center justify-between animate-fadeIn">
          <span>{reconcileError}</span>
          <button 
            type="button"
            onClick={() => setReconcileError(null)} 
            className="text-[#B84040] hover:text-[#241B19] font-bold ml-2 cursor-pointer p-1"
            aria-label="Dismiss error notification"
          >
            ✕
          </button>
        </div>
      )}

      {/* 2. Payment Engine Operational Status Matrix */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="rounded-xl p-5 border border-[#CFC7BB] space-y-1.5 bg-[#F7F4EE] shadow-xs">
          <span className="text-[11px] font-mono text-[#82786F] block">Engine Operational State</span>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${paymentStatus?.status === 'operational' ? 'bg-[#38865B]' : 'bg-[#A86E24]'}`} />
            <span className="text-base font-bold font-mono text-[#241B19]">
              {paymentStatus?.status ? paymentStatus.status.toUpperCase() : 'OPERATIONAL'}
            </span>
          </div>
          <span className="text-[11px] text-[#82786F] font-mono block">
            Protocol: x402 v{paymentStatus?.protocol_version || '2.0'}
          </span>
        </div>

        <div className="rounded-xl p-5 border border-[#CFC7BB] space-y-1.5 bg-[#F7F4EE] shadow-xs">
          <span className="text-[11px] font-mono text-[#82786F] block">Total Settled Volume</span>
          <span className="text-lg font-bold font-mono text-[#7D292D] block">
            ${verifiedSettledUsdc} USDC
          </span>
          <span className="text-[11px] text-[#82786F] font-mono block">
            {settledRecords.length} authoritative receipts
          </span>
        </div>

        <div className="rounded-xl p-5 border border-[#CFC7BB] space-y-1.5 bg-[#F7F4EE] shadow-xs">
          <span className="text-[11px] font-mono text-[#82786F] block">Settlement Facilitator</span>
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-[#38865B]" />
            <span className="text-sm font-semibold text-[#241B19] font-mono">
              {paymentStatus?.facilitator_configured ? 'Active & Ready' : 'Local Mode'}
            </span>
          </div>
          <span className="text-[11px] text-[#82786F] font-mono block">
            Target: Base Sepolia (84532)
          </span>
        </div>

        <div className="rounded-xl p-5 border border-[#CFC7BB] space-y-1.5 bg-[#F7F4EE] shadow-xs">
          <span className="text-[11px] font-mono text-[#82786F] block">Suspense Queue</span>
          <span className="text-lg font-bold font-mono text-[#A86E24] block">
            {paymentStatus?.pending_reconciliations_count ?? pendingEntries.length}
          </span>
          <span className="text-[11px] text-[#82786F] font-mono block">
            uncertain on-chain attempts
          </span>
        </div>
      </div>

      {/* 3. Authoritative Financial Transparency Breakdown */}
      <div className="rounded-xl p-5 border border-[#CFC7BB] bg-[#F7F4EE] space-y-4 shadow-xs">
        <div className="flex items-center justify-between pb-2 border-b border-[#CFC7BB]/60">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#7D292D]" />
            <h2 className="text-xs font-semibold text-[#241B19] uppercase tracking-wider font-mono">
              Authoritative Financial Accounting
            </h2>
          </div>
          <span className="text-[11px] font-mono text-[#82786F]">
            Verified ledger records vs uncharged / suspense balance
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-1">
            <span className="text-[#82786F] text-[11px] block">Verified Settled Spend:</span>
            <span className="text-base font-bold text-[#7D292D] block">${verifiedSettledUsdc} USDC</span>
            <span className="text-[10px] text-[#82786F] block">Cryptographically settled</span>
          </div>

          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-1">
            <span className="text-[#82786F] text-[11px] block">Held in Suspense:</span>
            <span className="text-base font-bold text-[#A86E24] block">${pendingSuspenseUsdc} USDC</span>
            <span className="text-[10px] text-[#82786F] block">{pendingEntries.length} pending reconciliations</span>
          </div>

          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-1">
            <span className="text-[#82786F] text-[11px] block">Uncharged / Released:</span>
            <span className="text-base font-bold text-[#241B19] block">${unchargedReleasedUsdc} USDC</span>
            <span className="text-[10px] text-[#82786F] block">{failedUnchargedRecords.length} refused/failed calls</span>
          </div>

          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-1">
            <span className="text-[#82786F] text-[11px] block">Micro-Tariff Range:</span>
            <span className="text-base font-bold text-[#241B19] block">0.002 - 0.004 USDC</span>
            <span className="text-[10px] text-[#82786F] block">2,000 - 4,000 base units</span>
          </div>
        </div>

        <div className="pt-2 border-t border-[#CFC7BB]/60 flex items-center gap-2 text-[11px] text-[#82786F] font-mono">
          <Info className="w-3.5 h-3.5 text-[#7D292D] shrink-0" />
          <span>
            Security Invariant: The frontend never presents an unverified amount as settled spending. Only persisted ledger records confirm settlement.
          </span>
        </div>
      </div>

      {/* 4. Suspense & Pending Reconciliations Inspection */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-serif font-bold text-[#241B19] flex items-center gap-2">
              <span>Suspense & Pending Reconciliations</span>
              <span className="text-[11px] font-mono text-[#A86E24] px-2.5 py-0.5 rounded-full bg-[#A86E24]/15 border border-[#A86E24]/30">
                {pendingEntries.length} held in suspense
              </span>
            </h2>
            <p className="text-xs text-[#82786F] mt-0.5">
              Payment attempts waiting for authoritative facilitator / block explorer settlement confirmation.
            </p>
          </div>
        </div>

        <div className="rounded-xl border border-[#CFC7BB] overflow-hidden bg-[#F7F4EE] shadow-xs">
          {pendingEntries.length === 0 ? (
            <div className="py-8 text-center text-xs text-[#82786F] space-y-1">
              <CheckCircle2 className="w-5 h-5 text-[#38865B] mx-auto mb-1.5" />
              <p className="text-[#241B19] font-medium">No pending reconciliations in suspense</p>
              <p className="text-[11px] text-[#82786F]">
                All executed payments are authoritatively settled or released in the ledger.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-[#CFC7BB]/60">
              {pendingEntries.map(([attemptId, details]) => {
                const isThisReconciling = reconcilingId === attemptId;
                const d = typeof details === 'object' ? details : {};

                return (
                  <div key={attemptId} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono bg-[#FFFFFF]/70">
                    <div className="space-y-1.5 max-w-2xl">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[#241B19] font-semibold">{attemptId}</span>
                        <StatusBadge status="pending reconciliation" size="sm" />
                        {d.service_id && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-[#DED8CD] text-[#241B19] border border-[#CFC7BB]">
                            Service: {d.service_id}
                          </span>
                        )}
                        {d.task_id && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-[#DED8CD] text-[#241B19] border border-[#CFC7BB]">
                            Task: {d.task_id}
                          </span>
                        )}
                      </div>

                      {d.error_message && (
                        <p className="text-[11px] text-[#A86E24] leading-relaxed font-sans">
                          {d.error_message}
                        </p>
                      )}

                      <div className="text-[11px] text-[#82786F] space-x-3">
                        {d.seller_recipient && (
                          <span>Recipient: {d.seller_recipient.slice(0, 10)}...{d.seller_recipient.slice(-6)}</span>
                        )}
                        {d.token_address && (
                          <span>Token: {d.token_address.slice(0, 8)}...</span>
                        )}
                        {d.amount_usdc && <span>Amount: ${d.amount_usdc} USDC</span>}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => setSelectedPaymentRecord({
                          request_id: d.request_id || attemptId,
                          task_id: d.task_id,
                          call_id: d.call_id,
                          service_id: d.service_id || 'unknown',
                          status: 'pending reconciliation',
                          amount_paid: d.amount_usdc || '0.000000',
                          listed_price: d.amount_usdc || '0.002',
                          error_reason: d.error_message,
                          seller_id: d.seller_recipient,
                          network: d.network || 'eip155:84532',
                          token: d.token_address,
                          timestamp: d.settled_at || new Date().toISOString()
                        })}
                        className="px-3 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB] transition-colors cursor-pointer text-xs shadow-xs"
                      >
                        Details
                      </button>

                      <button
                        type="button"
                        onClick={() => onReconcileClick(attemptId)}
                        disabled={isThisReconciling}
                        className="px-3.5 py-1.5 rounded-lg bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-medium text-xs transition-colors cursor-pointer flex items-center gap-1.5 disabled:opacity-50 shadow-xs"
                      >
                        {isThisReconciling ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            <span>Reconciling...</span>
                          </>
                        ) : (
                          <>
                            <Zap className="w-3.5 h-3.5 text-[#F7F4EE]" />
                            <span>Authoritative Reconcile</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* 5. Authoritative Payment Lifecycle Ledger Explorer */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-serif font-bold text-[#241B19] flex items-center gap-2">
              <span>Payment Lifecycle Ledger</span>
              <span className="text-[11px] font-mono text-[#82786F] px-2.5 py-0.5 rounded-full bg-[#DED8CD] border border-[#CFC7BB]">
                {filteredRecords.length} records
              </span>
            </h2>
            <p className="text-xs text-[#82786F] mt-0.5">
              Authoritative records of EIP-712 authorizations, settlements, and rejected payloads.
            </p>
          </div>

          {/* Search filter */}
          <div className="w-full sm:w-64 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#82786F]" />
            <input
              type="text"
              placeholder="Search ID, service, hash..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full bg-[#FFFFFF] border border-[#CFC7BB] rounded-lg pl-9 pr-3 py-2 text-xs text-[#241B19] placeholder-[#82786F] focus:outline-none focus:border-[#7D292D] font-mono shadow-xs"
            />
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto text-xs font-mono pb-1 border-b border-[#CFC7BB]/60">
          <button
            type="button"
            onClick={() => setFilterTab('all')}
            className={`px-3.5 py-1.5 rounded-lg border transition-colors cursor-pointer ${
              filterTab === 'all'
                ? 'bg-[#7D292D] text-[#F7F4EE] font-medium border-[#7D292D] shadow-xs'
                : 'bg-[#FFFFFF] text-[#82786F] hover:text-[#241B19] border-[#CFC7BB]'
            }`}
          >
            All Payments ({ledger.length})
          </button>

          <button
            type="button"
            onClick={() => setFilterTab('settled')}
            className={`px-3.5 py-1.5 rounded-lg border transition-colors cursor-pointer ${
              filterTab === 'settled'
                ? 'bg-[#38865B] text-[#F7F4EE] font-medium border-[#38865B] shadow-xs'
                : 'bg-[#FFFFFF] text-[#82786F] hover:text-[#38865B] border-[#CFC7BB]'
            }`}
          >
            Settled & Verified ({settledRecords.length})
          </button>

          <button
            type="button"
            onClick={() => setFilterTab('rejected')}
            className={`px-3.5 py-1.5 rounded-lg border transition-colors cursor-pointer ${
              filterTab === 'rejected'
                ? 'bg-[#A86E24] text-[#F7F4EE] font-medium border-[#A86E24] shadow-xs'
                : 'bg-[#FFFFFF] text-[#82786F] hover:text-[#A86E24] border-[#CFC7BB]'
            }`}
          >
            Output Rejected ({rejectedOutputRecords.length})
          </button>

          <button
            type="button"
            onClick={() => setFilterTab('failed')}
            className={`px-3.5 py-1.5 rounded-lg border transition-colors cursor-pointer ${
              filterTab === 'failed'
                ? 'bg-[#B84040] text-[#F7F4EE] font-medium border-[#B84040] shadow-xs'
                : 'bg-[#FFFFFF] text-[#82786F] hover:text-[#B84040] border-[#CFC7BB]'
            }`}
          >
            Failed / Uncharged ({failedUnchargedRecords.length})
          </button>
        </div>

        {/* Ledger Table */}
        <div className="rounded-xl border border-[#CFC7BB] overflow-hidden bg-[#F7F4EE] shadow-xs">
          {filteredRecords.length === 0 ? (
            <div className="py-12 text-center text-xs text-[#82786F] space-y-2">
              <SlidersHorizontal className="w-5 h-5 text-[#82786F] mx-auto mb-1" />
              <p className="text-[#241B19] font-medium">No matching payment records found</p>
              <p className="text-[#82786F]">
                {taskIdParam ? `No records matched task "${taskIdParam}".` : 'Try clearing your search query or status filter.'}
              </p>
              {(searchFilter || taskIdParam || filterTab !== 'all') && (
                <button
                  onClick={() => {
                    setSearchFilter('');
                    setFilterTab('all');
                    clearTaskFilter();
                  }}
                  className="px-3.5 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono border border-[#CFC7BB] transition-colors cursor-pointer inline-block mt-1 shadow-xs"
                >
                  Reset Filters
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#DED8CD]/40 text-[#82786F] border-b border-[#CFC7BB]">
                  <tr>
                    <th className="py-3 px-4 font-medium">Request & Call Reference</th>
                    <th className="py-3 px-4 font-medium">Service Target</th>
                    <th className="py-3 px-4 font-medium">Payment State</th>
                    <th className="py-3 px-4 font-medium">Listed vs Verified</th>
                    <th className="py-3 px-4 font-medium">Settlement Proof</th>
                    <th className="py-3 px-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-[#CFC7BB]/50 text-[#241B19]">
                  {filteredRecords.map((record) => {
                    const statusInfo = mapPaymentStatus(record.status);
                    const txHash = record.tx_hash;
                    const isRealOnChain = txHash && txHash.startsWith('0x') && txHash.length >= 42;
                    const explorerUrl = isRealOnChain ? `https://sepolia.basescan.org/tx/${txHash}` : null;

                    return (
                      <tr 
                        key={record.request_id}
                        className="hover:bg-[#DED8CD]/20 transition-colors"
                      >
                        {/* Request ID & Task Badge */}
                        <td className="py-3.5 px-4">
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-[#241B19]">{record.request_id}</span>
                              <button
                                onClick={() => copyToClipboard(record.request_id, record.request_id)}
                                className="text-[#82786F] hover:text-[#241B19] transition-colors cursor-pointer"
                                title="Copy Request ID"
                              >
                                {copiedKey === record.request_id ? (
                                  <Check className="w-3 h-3 text-[#38865B]" />
                                ) : (
                                  <span className="text-[10px]">copy</span>
                                )}
                              </button>
                            </div>
                            <div className="flex items-center gap-1.5 text-[10px] text-[#82786F]">
                              <Clock className="w-3 h-3 text-[#82786F]" />
                              <span>{new Date(record.timestamp).toLocaleTimeString()}</span>
                              {record.latency_ms > 0 && <span>• {record.latency_ms}ms</span>}
                            </div>
                          </div>
                        </td>

                        {/* Service Target */}
                        <td className="py-3.5 px-4">
                          <div className="space-y-0.5">
                            <span className="text-[#241B19] font-medium block">{record.service_id}</span>
                            <span className="text-[11px] text-[#82786F] block truncate max-w-[140px]" title={record.seller_id}>
                              {record.seller_id}
                            </span>
                          </div>
                        </td>

                        {/* Payment State */}
                        <td className="py-3.5 px-4">
                          <StatusBadge status={statusInfo.label} size="sm" />
                        </td>

                        {/* Listed vs Verified Amount */}
                        <td className="py-3.5 px-4">
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-1">
                              <span className="text-[10px] text-[#82786F]">Paid:</span>
                              <span className={`font-semibold ${
                                record.status === 'paid' ? 'text-[#7D292D]' : 'text-[#82786F]'
                              }`}>
                                ${record.amount_paid} USDC
                              </span>
                            </div>
                            <span className="text-[10px] text-[#82786F] block">
                              Tariff: ${record.listed_price} USDC
                            </span>
                          </div>
                        </td>

                        {/* Settlement Proof / Tx Hash */}
                        <td className="py-3.5 px-4">
                          {txHash ? (
                            <div className="flex items-center gap-1.5">
                              {explorerUrl ? (
                                <a
                                  href={explorerUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[#7D292D] hover:underline flex items-center gap-1 text-[11px] font-semibold"
                                >
                                  <span>{txHash.slice(0, 8)}...{txHash.slice(-6)}</span>
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              ) : (
                                <span className="text-[11px] text-[#82786F] truncate max-w-[140px]" title={txHash}>
                                  {txHash.slice(0, 16)}...
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-[11px] text-[#82786F]">
                              Uncharged / Local
                            </span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="py-3.5 px-4 text-right">
                          <button
                            type="button"
                            onClick={() => setSelectedPaymentRecord(record)}
                            className="px-3 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB] transition-colors cursor-pointer text-xs font-mono shadow-xs"
                          >
                            Inspect x402
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* 6. Settlement Flow Telemetry Visualizer */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-serif font-bold text-[#241B19]">
            Settlement Flow Telemetry
          </h2>
          <span className="text-[11px] font-mono text-[#82786F]">
            EIP-712 Micro-auth vs Classical Human Checkout
          </span>
        </div>
        <PaymentsRace />
      </div>

      {/* 7. Security Guarantee Card */}
      <div className="p-5 rounded-xl bg-[#F7F4EE] border border-[#CFC7BB] space-y-3 text-xs shadow-xs">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-[#38865B]" />
          <span className="font-semibold text-[#241B19] font-mono">
            Cryptographic Payment Architecture & Security Principles
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px] text-[#82786F] pt-1">
          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-1 shadow-xs">
            <span className="text-[#241B19] font-semibold font-mono block">Zero Browser Signing</span>
            <p>Private keys are never exposed or stored in local storage. All payment operations execute on authorized backend rails.</p>
          </div>
          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-1 shadow-xs">
            <span className="text-[#241B19] font-semibold font-mono block">Authoritative Ledger</span>
            <p>Outcome verification relies exclusively on persisted backend records and Base Sepolia receipts—never frontend timers.</p>
          </div>
          <div className="p-3.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-1 shadow-xs">
            <span className="text-[#241B19] font-semibold font-mono block">Suspense Isolation</span>
            <p>Uncertain transactions remain quarantined in suspense until authoritative on-chain verification succeeds or reverts.</p>
          </div>
        </div>
      </div>

      {/* 8. Quick Link to Ledger */}
      <div className="pt-2 flex justify-between items-center text-xs font-mono">
        <span className="text-[#82786F]">
          Audit records are permanently preserved in the local ledger.
        </span>
        <NavLink
          to="/ledger"
          className="px-4 py-2 rounded-lg bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] border border-[#7D292D] flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs font-medium"
        >
          <span>View Audit Ledger</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </NavLink>
      </div>

      {/* Interactive x402 Modal */}
      {selectedPaymentRecord && (
        <X402PaymentModal
          record={selectedPaymentRecord}
          onClose={() => setSelectedPaymentRecord(null)}
        />
      )}
    </div>
  );
};

export default PaymentProcessing;
