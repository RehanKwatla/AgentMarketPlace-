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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[rgba(255, 255, 255,0.16)] pb-4">
        <div>
          <h1 className="text-2xl font-semibold text-[#FAFAFA]">
            Payments & Settlement
          </h1>
          <p className="text-xs text-[#A3A3A3] mt-0.5">
            Audit ledger of verified EIP-712 authorizations and Base Sepolia settlement proofs.
          </p>
        </div>

        {/* Live Totals */}
        <div className="flex items-center gap-2 text-xs">
          <div className="bg-[#121212] px-3 py-1.5 rounded-md border border-[rgba(255, 255, 255,0.18)]">
            <span className="text-[#A3A3A3] text-[11px] mr-1.5">Volume:</span>
            <span className="font-mono font-semibold text-[#FFFFFF]">${totalVolumeUsdc} USDC</span>
          </div>
          <div className="bg-[#121212] px-3 py-1.5 rounded-md border border-[rgba(255, 255, 255,0.18)]">
            <span className="text-[#A3A3A3] text-[11px] mr-1.5">Settled:</span>
            <span className="font-mono font-semibold text-[#A3A3A3]">{paidTransactions.length}</span>
          </div>
        </div>
      </div>

      {/* Telemetry Visualizer */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-[#FAFAFA]">
            Payments Latency Comparison
          </h2>
          <span className="text-[11px] font-mono text-[#737373]">
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
          <h2 className="text-sm font-medium text-[#FAFAFA]">
            Audit Ledger ({ledger.length})
          </h2>
          <p className="text-xs text-[#A3A3A3]">
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
