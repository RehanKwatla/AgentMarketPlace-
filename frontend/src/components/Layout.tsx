import React from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { Header } from './Header';
import { PaymentTicker } from './PaymentTicker';
import TopoField from './ui/topo-field';
import { ServiceDetailModal } from './ServiceDetailModal';
import { LedgerDetailModal } from './LedgerDetailModal';
import { TaskPlanPreviewModal } from './TaskPlanPreviewModal';
import { useMarketplace } from '../context/MarketplaceContext';
import { useDocumentMetadata } from '../utils/useDocumentMetadata';

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

  // Dynamically sync document title and meta description per route
  useDocumentMetadata();

  return (
    <div className="relative min-h-screen bg-[#E8E3DA] text-[#241B19] flex flex-col font-sans selection:bg-[#7D292D] selection:text-[#F7F4EE]">
      {/* 1. Single Fixed TopoField Full-Viewport Background Instance */}
      <div 
        className="fixed inset-0 w-full h-full pointer-events-none z-0 overflow-hidden" 
        aria-hidden="true"
      >
        <TopoField
          mode="light"
          speed={0.25}
          length={1.1}
          density={0.8}
          opacity={0.32}
        />
        {/* Warm ivory radial & vertical fade to guarantee high contrast & readability */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#E8E3DA]/30 via-[#E8E3DA]/50 to-[#E8E3DA] pointer-events-none" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#E8E3DA_85%)] opacity-70 pointer-events-none" />
      </div>

      {/* 2. Persistent Top Navigation Bar */}
      <Header />

      {/* 3. Horizontal Live Payment Ticker */}
      <div className="relative z-10">
        <PaymentTicker records={ledger} totalVolumeUsdc={totalVolumeUsdc} />
      </div>

      {/* 4. Main Page Content Underneath */}
      <main className="relative z-10 flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 py-6">
        {fetchError && (
          <div className="mb-6 p-3.5 rounded-xl bg-[#FDE8E8] border border-[#F8B4B4] text-[#7D292D] text-xs font-mono flex items-center justify-between shadow-sm">
            <span>Backend Notice: {fetchError}. Check FastAPI server at http://localhost:8000</span>
            <button
              onClick={() => refreshData()}
              className="px-2.5 py-1 bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-bold rounded-lg text-[11px] cursor-pointer transition-colors shadow-sm"
            >
              Retry
            </button>
          </div>
        )}

        <Outlet />
      </main>

      {/* 5. Consistent Editorial Footer */}
      <footer className="relative z-10 border-t border-[#CFC7BB] bg-[#F7F4EE]/90 backdrop-blur-md py-6 text-xs text-[#82786F] font-mono mt-12">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#38865B]" />
            <span className="text-[#241B19] font-bold">Agentica</span>
            <span>—</span>
            <span>© {new Date().getFullYear()}</span>
            <span>•</span>
            <span>Discover services. Pay per call. Inspect every result.</span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-[#82786F] text-[11px]">
            <NavLink to="/" className="text-[#7D292D] font-bold hover:underline transition-colors">Landing Page</NavLink>
            <span>•</span>
            <NavLink to="/dashboard" className="hover:text-[#7D292D] transition-colors">Dashboard</NavLink>
            <span>•</span>
            <NavLink to="/marketplace" className="hover:text-[#7D292D] transition-colors">Marketplace</NavLink>
            <span>•</span>
            <NavLink to="/buyer" className="hover:text-[#7D292D] transition-colors">Buyer Console</NavLink>
            <span>•</span>
            <NavLink to="/execution" className="hover:text-[#7D292D] transition-colors">Execution</NavLink>
            <span>•</span>
            <NavLink to="/payments" className="hover:text-[#7D292D] transition-colors">Payments</NavLink>
            <span>•</span>
            <NavLink to="/results" className="hover:text-[#7D292D] transition-colors">Results</NavLink>
            <span>•</span>
            <NavLink to="/ledger" className="hover:text-[#7D292D] transition-colors">Ledger</NavLink>
            <span>•</span>
            <span className="text-[#82786F]/80">Base Sepolia (eip155:84532) USDC</span>
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
export default Layout;
