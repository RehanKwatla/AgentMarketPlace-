import React from 'react';
import { PaymentsRace } from '../components/PaymentsRace';
import { LedgerTable } from '../components/LedgerTable';
import { useMarketplace } from '../context/MarketplaceContext';

export const Payments: React.FC = () => {
  const { 
    ledger, 
    totalVolumeUsdc, 
    setSelectedLedgerRecord, 
    selectedLedgerRecord 
  } = useMarketplace();

  const paidTransactions = ledger.filter(r => r.status === 'paid');

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[rgba(120,160,153,0.16)] pb-4">
        <div>
          <h1 className="text-2xl font-semibold text-[#F4F7F6]">
            Payments & Settlement
          </h1>
          <p className="text-xs text-[#9BA5A2] mt-0.5">
            Audit ledger of verified EIP-712 authorizations and Base Sepolia settlement proofs.
          </p>
        </div>

        {/* Live Totals */}
        <div className="flex items-center gap-2 text-xs">
          <div className="bg-[#121616] px-3 py-1.5 rounded-md border border-[rgba(120,160,153,0.18)]">
            <span className="text-[#9BA5A2] text-[11px] mr-1.5">Volume:</span>
            <span className="font-mono font-semibold text-[#36D6C8]">${totalVolumeUsdc} USDC</span>
          </div>
          <div className="bg-[#121616] px-3 py-1.5 rounded-md border border-[rgba(120,160,153,0.18)]">
            <span className="text-[#9BA5A2] text-[11px] mr-1.5">Settled:</span>
            <span className="font-mono font-semibold text-[#42C995]">{paidTransactions.length}</span>
          </div>
        </div>
      </div>

      {/* Telemetry Visualizer */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-[#F4F7F6]">
            Payments Latency Comparison
          </h2>
          <span className="text-[11px] font-mono text-[#6B7673]">
            Autonomous x402 vs Manual Checkout
          </span>
        </div>
        <PaymentsRace
          humanTxCount={1420}
          agentTxCount={3891 + ledger.length}
        />
      </div>

      {/* Audit Payment Ledger Table */}
      <div className="space-y-3 pt-2">
        <div>
          <h2 className="text-sm font-medium text-[#F4F7F6]">
            Audit Ledger ({ledger.length})
          </h2>
          <p className="text-xs text-[#9BA5A2]">
            Cryptographic receipts and execution outcomes recorded for every service invocation.
          </p>
        </div>

        <LedgerTable
          records={ledger}
          onSelectRecord={(rec) => setSelectedLedgerRecord(rec)}
          selectedRequestId={selectedLedgerRecord?.request_id}
        />
      </div>
    </div>
  );
};
