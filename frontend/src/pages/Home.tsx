import React from 'react';
import { useNavigate, NavLink } from 'react-router-dom';
import { HeroSection } from '../components/HeroSection';
import TopoField from '../components/ui/topo-field';
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
      <section className="relative isolate min-h-[360px] overflow-hidden rounded-2xl border border-white/10 bg-black sm:min-h-[400px]">
        <TopoField
          className="pointer-events-none absolute inset-0"
          mode="dark"
          speed={0.35}
          opacity={0.42}
        />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/35 via-transparent to-black/70" />
        <div className="relative z-10 flex min-h-[360px] items-center justify-center px-4 sm:min-h-[400px]">
          <HeroSection
            onExplore={() => navigate('/marketplace')}
            onPublish={() => navigate('/buyer')}
            serviceCount={services.length}
          />
        </div>
      </section>

      {/* 2. Platform Summary Metrics */}
      <div className="wallet-card rounded-lg p-4 border border-[rgba(255, 255, 255,0.18)] grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div className="p-1 border-r border-[rgba(255, 255, 255,0.12)] last:border-none">
          <span className="text-[11px] text-[#A3A3A3] block">Total Settled</span>
          <span className="text-lg font-semibold text-[#FFFFFF] font-mono mt-0.5 block">
            ${totalVolumeUsdc} <span className="text-xs text-[#A3A3A3]">USDC</span>
          </span>
        </div>

        <div className="p-1 border-r border-[rgba(255, 255, 255,0.12)] last:border-none">
          <span className="text-[11px] text-[#A3A3A3] block">Active Services</span>
          <span className="text-lg font-semibold text-[#FAFAFA] font-mono mt-0.5 block">
            {services.length} verified
          </span>
        </div>

        <div className="p-1 border-r border-[rgba(255, 255, 255,0.12)] last:border-none">
          <span className="text-[11px] text-[#A3A3A3] block">Testnet Network</span>
          <span className="text-sm font-medium text-[#FAFAFA] font-mono mt-1 block">
            Base Sepolia
          </span>
        </div>

        <div className="p-1">
          <span className="text-[11px] text-[#A3A3A3] block">Protocol Specification</span>
          <span className="text-sm font-medium text-[#A3A3A3] font-mono mt-1 block">
            x402 v2 EIP-712
          </span>
        </div>
      </div>

      {/* 3. Simple Services Table (Preferred over oversized cards) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-[#FAFAFA]">Available Services</h2>
            <p className="text-xs text-[#A3A3A3]">Registered seller agents ready for instant execution.</p>
          </div>
          <NavLink 
            to="/marketplace" 
            className="text-xs font-medium text-[#FFFFFF] hover:underline flex items-center gap-1"
          >
            <span>View All ({services.length})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </NavLink>
        </div>

        <div className="wallet-card rounded-lg border border-[rgba(255, 255, 255,0.18)] overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[rgba(255, 255, 255,0.16)] bg-[#0E0E0E] text-[#A3A3A3]">
                <th className="py-2.5 px-4 font-medium">Service</th>
                <th className="py-2.5 px-4 font-medium">Category</th>
                <th className="py-2.5 px-4 font-medium">Price</th>
                <th className="py-2.5 px-4 font-medium hidden sm:table-cell">Endpoint</th>
                <th className="py-2.5 px-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255, 255, 255,0.12)] text-[#FAFAFA]">
              {services.map((svc) => (
                <tr 
                  key={svc.service_id} 
                  className="hover:bg-[#151515] transition-colors cursor-pointer"
                  onClick={() => setSelectedService(svc)}
                >
                  <td className="py-3 px-4">
                    <div className="font-medium text-[#FAFAFA]">{svc.name}</div>
                    <div className="text-[11px] text-[#A3A3A3] font-mono">{svc.service_id}</div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="capitalize text-[11px] px-2 py-0.5 rounded bg-[#171717] text-[#A3A3A3] border border-[rgba(255, 255, 255,0.18)]">
                      {svc.category}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono font-medium text-[#FFFFFF]">
                    {svc.price_usdc} USDC
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-[#A3A3A3] hidden sm:table-cell max-w-[200px] truncate">
                    {svc.endpoint_url}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        useServiceInTask(svc);
                        navigate('/buyer');
                      }}
                      className="px-2.5 py-1 rounded bg-[#171717] hover:bg-[#FFFFFF] hover:text-[#0A0A0A] text-[#FFFFFF] text-xs font-medium border border-[rgba(255, 255, 255,0.3)] transition-colors cursor-pointer"
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
            <h2 className="text-base font-semibold text-[#FAFAFA]">Recent Settlement Stream</h2>
            <p className="text-xs text-[#A3A3A3]">Immutable record of verified x402 payment handshakes.</p>
          </div>
          <NavLink 
            to="/payments" 
            className="text-xs font-medium text-[#FFFFFF] hover:underline flex items-center gap-1"
          >
            <span>Full Ledger</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </NavLink>
        </div>

        <div className="wallet-card rounded-lg border border-[rgba(255, 255, 255,0.18)] overflow-hidden">
          {ledger.length === 0 ? (
            <div className="py-8 text-center text-xs text-[#A3A3A3]">
              No transactions recorded yet. Execute a buyer task to initialize testnet settlement.
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[rgba(255, 255, 255,0.16)] bg-[#0E0E0E] text-[#A3A3A3]">
                  <th className="py-2.5 px-4 font-medium">Request ID</th>
                  <th className="py-2.5 px-4 font-medium">Service Target</th>
                  <th className="py-2.5 px-4 font-medium">Status</th>
                  <th className="py-2.5 px-4 font-medium">Amount</th>
                  <th className="py-2.5 px-4 font-medium text-right">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(255, 255, 255,0.12)] font-mono text-xs">
                {ledger.slice(0, 4).map((rec) => (
                  <tr key={rec.request_id} className="hover:bg-[#151515] transition-colors">
                    <td className="py-2.5 px-4 font-medium text-[#FAFAFA]">{rec.request_id}</td>
                    <td className="py-2.5 px-4 text-[#FFFFFF]">{rec.service_id}</td>
                    <td className="py-2.5 px-4">
                      <span className="inline-flex items-center gap-1 text-[11px] text-[#A3A3A3]">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#A3A3A3]" />
                        {rec.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 font-medium">{rec.amount_paid} USDC</td>
                    <td className="py-2.5 px-4 text-right text-[#A3A3A3]">{rec.latency_ms} ms</td>
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
