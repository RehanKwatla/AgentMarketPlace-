import React, { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  FileText, 
  Search, 
  RotateCw,
  ShieldCheck
} from 'lucide-react';
import { useMarketplace } from '../context/MarketplaceContext';
import { LedgerTable } from '../components/LedgerTable';
import { X402PaymentModal } from '../components/X402PaymentModal';
import { Skeleton } from '../components/ui/Skeleton';
import { LedgerRecord } from '../types';

export const Ledger: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const taskIdParam = searchParams.get('taskId');
  const statusParam = searchParams.get('status');
  const serviceParam = searchParams.get('service');

  const { 
    ledger, 
    totalVolumeUsdc, 
    isLoading,
    refreshData 
  } = useMarketplace();

  const [statusFilter, setStatusFilter] = useState<string>(statusParam || 'all');
  const [serviceFilter, setServiceFilter] = useState<string>(serviceParam || 'all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [selectedRecord, setSelectedRecord] = useState<LedgerRecord | null>(null);

  const paidCount = ledger.filter(r => r.status === 'paid').length;
  const rejectedCount = ledger.filter(r => r.status === 'paid output rejected').length;
  const failedCount = ledger.filter(r => r.status === 'failed and not charged' || r.status === 'refused').length;

  const uniqueServices = Array.from(new Set(ledger.map(r => r.service_id))).filter(Boolean);

  const filteredRecords = useMemo(() => {
    return ledger.filter(rec => {
      // 1. Task ID filter from query param
      if (taskIdParam) {
        const matchesTask = 
          (rec.task_id && rec.task_id.toLowerCase().includes(taskIdParam.toLowerCase())) ||
          (rec.request_id && rec.request_id.toLowerCase().includes(taskIdParam.toLowerCase()));
        if (!matchesTask) return false;
      }

      // 2. Status filter
      if (statusFilter !== 'all' && rec.status !== statusFilter) return false;

      // 3. Service filter
      if (serviceFilter !== 'all' && rec.service_id !== serviceFilter) return false;

      // 4. Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchId = rec.request_id.toLowerCase().includes(q);
        const matchSvc = rec.service_id.toLowerCase().includes(q);
        const matchTx = rec.tx_hash ? rec.tx_hash.toLowerCase().includes(q) : false;
        const matchSeller = rec.seller_id ? rec.seller_id.toLowerCase().includes(q) : false;
        const matchTask = rec.task_id ? rec.task_id.toLowerCase().includes(q) : false;
        if (!matchId && !matchSvc && !matchTx && !matchSeller && !matchTask) return false;
      }

      return true;
    });
  }, [ledger, taskIdParam, statusFilter, serviceFilter, searchQuery]);

  const handleSyncLedger = async () => {
    setIsSyncing(true);
    try {
      await refreshData();
    } finally {
      setIsSyncing(false);
    }
  };

  const clearTaskParam = () => {
    const next = new URLSearchParams(searchParams);
    next.delete('taskId');
    setSearchParams(next);
  };

  const resetAllFilters = () => {
    setStatusFilter('all');
    setServiceFilter('all');
    setSearchQuery('');
    clearTaskParam();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto font-sans pb-12 animate-fade-in">
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#CFC7BB] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-serif font-bold text-[#241B19] flex items-center gap-2">
              <FileText className="w-6 h-6 text-[#7D292D]" />
              <span>Immutable Audit Ledger</span>
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#DED8CD] text-[#241B19] border border-[#CFC7BB]">
              Network: Base Sepolia (84532)
            </span>
          </div>
          <p className="text-xs text-[#82786F] mt-1 leading-relaxed">
            Cryptographic receipts, EIP-712 authorizations, and verified state transitions committed for every microservice invocation.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          {taskIdParam && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#DED8CD] border border-[#CFC7BB] text-[#241B19] text-xs">
              <span>Task: {taskIdParam.slice(0, 8)}...</span>
              <button 
                type="button"
                onClick={clearTaskParam}
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
            onClick={handleSyncLedger}
            disabled={isSyncing}
            className="px-3 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB] flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 shadow-sm"
            title="Fetch authoritative ledger records from backend"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-[#7D292D]' : 'text-[#82786F]'}`} />
            <span>{isSyncing ? 'Syncing...' : 'Sync Ledger'}</span>
          </button>
        </div>
      </div>

      {/* 2. Metric Counters */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="bg-[#F7F4EE] rounded-xl p-4 border border-[#CFC7BB] shadow-sm space-y-1">
          <span className="text-[11px] font-mono text-[#82786F] block">Total Settled Volume</span>
          <span className="text-xl font-bold font-serif text-[#241B19] block">${totalVolumeUsdc} USDC</span>
          <span className="text-[11px] text-[#82786F] font-mono block">Base Sepolia testnet</span>
        </div>

        <div className="bg-[#F7F4EE] rounded-xl p-4 border border-[#CFC7BB] shadow-sm space-y-1">
          <span className="text-[11px] font-mono text-[#82786F] block">Paid Invocations</span>
          <span className="text-xl font-bold font-serif text-[#38865B] block">{paidCount}</span>
          <span className="text-[11px] text-[#82786F] font-mono block">Verified settlement</span>
        </div>

        <div className="bg-[#F7F4EE] rounded-xl p-4 border border-[#CFC7BB] shadow-sm space-y-1">
          <span className="text-[11px] font-mono text-[#82786F] block">Paid Output Rejected</span>
          <span className="text-xl font-bold font-serif text-[#A86E24] block">{rejectedCount}</span>
          <span className="text-[11px] text-[#82786F] font-mono block">Schema validation failure</span>
        </div>

        <div className="bg-[#F7F4EE] rounded-xl p-4 border border-[#CFC7BB] shadow-sm space-y-1">
          <span className="text-[11px] font-mono text-[#82786F] block">Refused / Not Charged</span>
          <span className="text-xl font-bold font-serif text-[#82786F] block">{failedCount}</span>
          <span className="text-[11px] text-[#82786F] font-mono block">Zero fee protection</span>
        </div>
      </div>

      {/* 3. Predefined transaction queries (allowlisted local filters only) */}
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Predefined transaction queries">
        <span className="text-[11px] font-mono text-[#82786F] mr-1">Quick queries:</span>
        {([
          { id: 'latest', label: 'Latest transactions', status: 'all' },
          { id: 'paid', label: 'Successful', status: 'paid' },
          { id: 'rejected', label: 'Output rejected', status: 'paid output rejected' },
          { id: 'refused', label: 'Refused', status: 'refused' },
          { id: 'failed', label: 'Failed & not charged', status: 'failed and not charged' },
          { id: 'pending', label: 'Pending settlement', status: 'pending reconciliation' },
        ] as const).map((query) => {
          const isActive = statusFilter === query.status;
          return (
            <button
              key={query.id}
              type="button"
              aria-pressed={isActive}
              onClick={() => {
                setStatusFilter(query.status);
                setSearchQuery('');
              }}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-mono border transition-colors cursor-pointer ${
                isActive
                  ? 'bg-[#7D292D] text-[#F7F4EE] border-[#612024] font-semibold'
                  : 'bg-[#F7F4EE] text-[#241B19] border-[#CFC7BB] hover:bg-[#DED8CD]/60'
              }`}
            >
              {query.label}
            </button>
          );
        })}
      </div>

      {/* 4. Filter and Search Bar */}
      <div className="bg-[#F7F4EE] rounded-xl p-3.5 border border-[#CFC7BB] shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex-1 max-w-md relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#82786F]" />
          <input
            type="text"
            placeholder="Search request ID, service, task, tx hash..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#FFFFFF] border border-[#CFC7BB] rounded-md pl-8 pr-3 py-1.5 text-xs text-[#241B19] placeholder-[#82786F] focus:outline-none focus:border-[#7D292D] focus:ring-1 focus:ring-[#7D292D]"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Status Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-[#82786F] text-[11px]">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-md px-2.5 py-1 text-xs text-[#241B19] focus:outline-none focus:border-[#7D292D] cursor-pointer"
            >
              <option value="all">All Statuses ({ledger.length})</option>
              <option value="paid">Paid ({paidCount})</option>
              <option value="paid output rejected">Paid Output Rejected ({rejectedCount})</option>
              <option value="refused">Refused</option>
              <option value="failed and not charged">Failed & Not Charged</option>
              <option value="pending reconciliation">Pending Reconciliation</option>
            </select>
          </div>

          {/* Service Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-[#82786F] text-[11px]">Service:</span>
            <select
              value={serviceFilter}
              onChange={(e) => setServiceFilter(e.target.value)}
              className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-md px-2.5 py-1 text-xs text-[#241B19] focus:outline-none focus:border-[#7D292D] cursor-pointer"
            >
              <option value="all">All Services</option>
              {uniqueServices.map(sid => (
                <option key={sid} value={sid}>{sid}</option>
              ))}
            </select>
          </div>

          {/* Reset button */}
          {(statusFilter !== 'all' || serviceFilter !== 'all' || searchQuery || taskIdParam) && (
            <button
              type="button"
              onClick={resetAllFilters}
              className="px-2.5 py-1 rounded bg-[#DED8CD] hover:bg-[#DED8CD]/80 text-[#241B19] text-[11px] border border-[#CFC7BB] transition-colors cursor-pointer"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* 5. Ledger Table */}
      <div className="space-y-3">
        {isLoading && ledger.length === 0 ? (
          <div
            className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm overflow-hidden divide-y divide-[#CFC7BB]/60"
            aria-busy="true"
            aria-label="Loading ledger records"
          >
            {[0, 1, 2, 3, 4].map((row) => (
              <div key={row} className="p-4 flex items-center justify-between gap-4">
                <div className="space-y-2 min-w-0 flex-1">
                  <Skeleton className="h-3 w-48" />
                  <Skeleton className="h-2.5 w-32" />
                </div>
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-3 w-16" />
              </div>
            ))}
          </div>
        ) : (
          <LedgerTable
            records={filteredRecords}
            onSelectRecord={(rec) => setSelectedRecord(rec)}
            selectedRequestId={selectedRecord?.request_id}
          />
        )}
      </div>

      {/* 6. Cryptographic Proof Audit Summary */}
      <div className="p-4 rounded-xl bg-[#F7F4EE] border border-[#CFC7BB] space-y-2 text-xs shadow-sm">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-[#38865B]" />
          <span className="font-semibold text-[#241B19] font-mono">
            Authoritative Ledger Accounting Principles
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px] text-[#82786F] pt-1">
          <div className="p-2.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-1">
            <span className="text-[#241B19] font-semibold font-mono block">Zero Floating-Point Drift</span>
            <p>Financial ledger commits strictly record atomic units (6 decimals) before computing display values.</p>
          </div>
          <div className="p-2.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-1">
            <span className="text-[#241B19] font-semibold font-mono block">Zero Charge Guarantee</span>
            <p>Failed or refused calls never deduct funds from the buyer's balance. Budget caps are released immediately.</p>
          </div>
          <div className="p-2.5 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] space-y-1">
            <span className="text-[#241B19] font-semibold font-mono block">Immutable Proofs</span>
            <p>Every settled entry is verifiable against Base Sepolia on-chain receipts or local EIP-712 authorization nonces.</p>
          </div>
        </div>
      </div>

      {/* Detailed x402 Modal */}
      {selectedRecord && (
        <X402PaymentModal
          record={selectedRecord}
          onClose={() => setSelectedRecord(null)}
        />
      )}
    </div>
  );
};

export default Ledger;
