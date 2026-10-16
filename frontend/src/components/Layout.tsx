import React from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { PaymentTicker } from './PaymentTicker';
import { WalletBackground } from './WalletBackground';
import { ServiceDetailModal } from './ServiceDetailModal';
import { LedgerDetailModal } from './LedgerDetailModal';
import { TaskPlanPreviewModal } from './TaskPlanPreviewModal';
import { useMarketplace } from '../context/MarketplaceContext';

export const Layout: React.FC = () => {
  const { 
    selectedService, 
    setSelectedService, 
    reputations, 
    useServiceInTask,
    selectedLedgerRecord, 
    setSelectedLedgerRecord,
    taskPlan, 
    setTaskPlan, 
    handleExecuteConfirmedTask, 
    isSubmitting,
    fetchError,
    refreshData,
    ledger,
    totalVolumeUsdc
  } = useMarketplace();

  const location = useLocation();
  const isHomePage = location.pathname === '/';

  return (
    <div className="relative min-h-screen bg-[#0B0D0D] text-[#F4F7F6] flex flex-col font-sans selection:bg-[#36D6C8] selection:text-[#0B0D0D]">
      {/* Concentric Circular Rings & Radial Lighting Background */}
      <WalletBackground subtle={!isHomePage} />

      {/* Persistent Top Navigation Bar */}
      <Header />

      {/* Horizontal Live Payment Ticker */}
      <PaymentTicker records={ledger} totalVolumeUsdc={totalVolumeUsdc} />

      {/* Main Page Workspace */}
      <main className="relative z-10 flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 py-6">
        {fetchError && (
          <div className="mb-6 p-3.5 rounded-xl bg-[rgba(225,109,109,0.12)] border border-[rgba(225,109,109,0.3)] text-[#E16D6D] text-xs font-mono flex items-center justify-between">
            <span>Backend Notice: {fetchError}. Check FastAPI server at http://localhost:8000</span>
            <button
              onClick={() => refreshData()}
              className="px-2.5 py-1 bg-[#E16D6D] text-[#0B0D0D] font-bold rounded-lg text-[11px] cursor-pointer hover:bg-[#E16D6D]/90 transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        <Outlet />
      </main>

      {/* Consistent Footer */}
      <footer className="relative z-10 border-t border-[rgba(120,160,153,0.18)] bg-[#0B0D0D]/90 backdrop-blur-md py-6 text-xs text-[#A0AAA7] font-mono mt-12">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#36D6C8] shadow-sm shadow-[#36D6C8]" />
            <span className="text-[#F4F7F6] font-bold">Agentic Market</span>
            <span>—</span>
            <span>DISCOVER → CONNECT → PAY → AUTOMATE</span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-[#A0AAA7] text-[11px]">
            <NavLink to="/marketplace" className="hover:text-[#36D6C8] transition-colors">Marketplace</NavLink>
            <span>•</span>
            <NavLink to="/payments" className="hover:text-[#36D6C8] transition-colors">Payments</NavLink>
            <span>•</span>
            <NavLink to="/buyer" className="hover:text-[#36D6C8] transition-colors">Buyer Agent</NavLink>
            <span>•</span>
            <NavLink to="/seller" className="hover:text-[#36D6C8] transition-colors">Seller Tools</NavLink>
            <span>•</span>
            <NavLink to="/analytics" className="hover:text-[#36D6C8] transition-colors">Analytics</NavLink>
            <span>•</span>
            <NavLink to="/about" className="hover:text-[#36D6C8] transition-colors">About</NavLink>
            <span>•</span>
            <span className="text-[#42C995] font-semibold">Base Sepolia USDC</span>
          </div>
        </div>
      </footer>

      {/* Global Modals */}
      <ServiceDetailModal
        service={selectedService}
        reputation={selectedService ? reputations[selectedService.service_id] : undefined}
        onClose={() => setSelectedService(null)}
        onUseInTask={useServiceInTask}
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
