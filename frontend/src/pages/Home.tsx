import React from 'react';
import { useNavigate, NavLink } from 'react-router-dom';
import { HeroSection } from '../components/HeroSection';
import { useMarketplace } from '../context/MarketplaceContext';
import { ArrowRight } from 'lucide-react';

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const { 
    services, 
    ledger, 
    totalVolumeUsdc, 
    setSelectedService,
    useServiceInTask 
  } = useMarketplace();

  return (
    <div className="space-y-10 py-2 max-w-5xl mx-auto">
      {/* 1. Concise Hero */}
      <HeroSection
        onExplore={() => navigate('/marketplace')}
        onPublish={() => navigate('/buyer')}
        serviceCount={services.length}
      />

      {/* 2. Platform Summary Metrics */}
      <div className="wallet-card rounded-lg p-4 border border-[rgba(120,160,153,0.18)] grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div className="p-1 border-r border-[rgba(120,160,153,0.12)] last:border-none">
          <span className="text-[11px] text-[#9BA5A2] block">Total Settled</span>
          <span className="text-lg font-semibold text-[#36D6C8] font-mono mt-0.5 block">
            ${totalVolumeUsdc} <span className="text-xs text-[#9BA5A2]">USDC</span>
          </span>
        </div>

        <div className="p-1 border-r border-[rgba(120,160,153,0.12)] last:border-none">
          <span className="text-[11px] text-[#9BA5A2] block">Active Services</span>
          <span className="text-lg font-semibold text-[#F4F7F6] font-mono mt-0.5 block">
            {services.length} verified
          </span>
        </div>

        <div className="p-1 border-r border-[rgba(120,160,153,0.12)] last:border-none">
          <span className="text-[11px] text-[#9BA5A2] block">Testnet Network</span>
          <span className="text-sm font-medium text-[#F4F7F6] font-mono mt-1 block">
            Base Sepolia
          </span>
        </div>

        <div className="p-1">
          <span className="text-[11px] text-[#9BA5A2] block">Protocol Specification</span>
          <span className="text-sm font-medium text-[#42C995] font-mono mt-1 block">
            x402 v2 EIP-712
          </span>
        </div>
      </div>

      {/* 3. Simple Services Table (Preferred over oversized cards) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-[#F4F7F6]">Available Services</h2>
            <p className="text-xs text-[#9BA5A2]">Registered seller agents ready for instant execution.</p>
          </div>
          <NavLink 
            to="/marketplace" 
            className="text-xs font-medium text-[#36D6C8] hover:underline flex items-center gap-1"
          >
            <span>View All ({services.length})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </NavLink>
        </div>

        <div className="wallet-card rounded-lg border border-[rgba(120,160,153,0.18)] overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[rgba(120,160,153,0.16)] bg-[#0E1212] text-[#9BA5A2]">
                <th className="py-2.5 px-4 font-medium">Service</th>
                <th className="py-2.5 px-4 font-medium">Category</th>
                <th className="py-2.5 px-4 font-medium">Price</th>
                <th className="py-2.5 px-4 font-medium hidden sm:table-cell">Endpoint</th>
                <th className="py-2.5 px-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(120,160,153,0.12)] text-[#F4F7F6]">
              {services.map((svc) => (
                <tr 
                  key={svc.service_id} 
                  className="hover:bg-[#151A1A] transition-colors cursor-pointer"
                  onClick={() => setSelectedService(svc)}
                >
                  <td className="py-3 px-4">
                    <div className="font-medium text-[#F4F7F6]">{svc.name}</div>
                    <div className="text-[11px] text-[#9BA5A2] font-mono">{svc.service_id}</div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="capitalize text-[11px] px-2 py-0.5 rounded bg-[#161B1A] text-[#9BA5A2] border border-[rgba(120,160,153,0.18)]">
                      {svc.category}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono font-medium text-[#36D6C8]">
                    {svc.price_usdc} USDC
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-[#9BA5A2] hidden sm:table-cell max-w-[200px] truncate">
                    {svc.endpoint_url}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        useServiceInTask(svc);
                        navigate('/buyer');
                      }}
                      className="px-2.5 py-1 rounded bg-[#161B1A] hover:bg-[#36D6C8] hover:text-[#0B0D0D] text-[#36D6C8] text-xs font-medium border border-[rgba(54,214,200,0.3)] transition-colors cursor-pointer"
                    >
                      Use in Task
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Recent Payment Ledger Activity (Simple Table Preview) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-[#F4F7F6]">Recent Settlement Stream</h2>
            <p className="text-xs text-[#9BA5A2]">Immutable record of verified x402 payment handshakes.</p>
          </div>
          <NavLink 
            to="/payments" 
            className="text-xs font-medium text-[#36D6C8] hover:underline flex items-center gap-1"
          >
            <span>Full Ledger</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </NavLink>
        </div>

        <div className="wallet-card rounded-lg border border-[rgba(120,160,153,0.18)] overflow-hidden">
          {ledger.length === 0 ? (
            <div className="py-8 text-center text-xs text-[#9BA5A2]">
              No transactions recorded yet. Execute a buyer task to initialize testnet settlement.
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[rgba(120,160,153,0.16)] bg-[#0E1212] text-[#9BA5A2]">
                  <th className="py-2.5 px-4 font-medium">Request ID</th>
                  <th className="py-2.5 px-4 font-medium">Service Target</th>
                  <th className="py-2.5 px-4 font-medium">Status</th>
                  <th className="py-2.5 px-4 font-medium">Amount</th>
                  <th className="py-2.5 px-4 font-medium text-right">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(120,160,153,0.12)] font-mono text-xs">
                {ledger.slice(0, 4).map((rec) => (
                  <tr key={rec.request_id} className="hover:bg-[#151A1A] transition-colors">
                    <td className="py-2.5 px-4 font-medium text-[#F4F7F6]">{rec.request_id}</td>
                    <td className="py-2.5 px-4 text-[#36D6C8]">{rec.service_id}</td>
                    <td className="py-2.5 px-4">
                      <span className="inline-flex items-center gap-1 text-[11px] text-[#42C995]">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#42C995]" />
                        {rec.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 font-medium">{rec.amount_paid} USDC</td>
                    <td className="py-2.5 px-4 text-right text-[#9BA5A2]">{rec.latency_ms} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
