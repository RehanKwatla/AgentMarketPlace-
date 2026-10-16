import React from 'react';
import { SellerToolsView as SellerToolsFormComponent } from '../components/SellerToolsView';
import { useMarketplace } from '../context/MarketplaceContext';
import { Database, Globe, Cpu, ShieldCheck } from 'lucide-react';

export const SellerTools: React.FC = () => {
  const { services, setSelectedService } = useMarketplace();

  const getCategoryIcon = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'data': return <Database className="w-3.5 h-3.5 text-[#FFFFFF]" />;
      case 'scraping': return <Globe className="w-3.5 h-3.5 text-[#A3A3A3]" />;
      case 'inference': return <Cpu className="w-3.5 h-3.5 text-[#D4D4D4]" />;
      default: return <ShieldCheck className="w-3.5 h-3.5 text-[#FFFFFF]" />;
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* 1. Seller Onboarding Form & Spec Validator */}
      <SellerToolsFormComponent />

      {/* 2. Registered Seller Microservices Table */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-[#FAFAFA]">
              Registered Services ({services.length})
            </h2>
            <p className="text-xs text-[#A3A3A3]">
              Active microservices registered on Base Sepolia.
            </p>
          </div>

          <span className="text-[11px] font-mono text-[#A3A3A3] bg-[rgba(163, 163, 163,0.08)] border border-[rgba(163, 163, 163,0.20)] px-2 py-0.5 rounded">
            All Endpoints Active
          </span>
        </div>

        <div className="bg-[#111111] rounded-xl border border-[rgba(255, 255, 255,0.16)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[rgba(255, 255, 255,0.14)] bg-[#0D0D0D] text-[#A3A3A3]">
                  <th className="py-2.5 px-4 font-medium text-xs">Service Name</th>
                  <th className="py-2.5 px-4 font-medium text-xs">Category</th>
                  <th className="py-2.5 px-4 font-medium text-xs">Price</th>
                  <th className="py-2.5 px-4 font-medium text-xs">Endpoint</th>
                  <th className="py-2.5 px-4 font-medium text-xs">PayTo Recipient</th>
                  <th className="py-2.5 px-4 font-medium text-xs text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(255, 255, 255,0.10)] text-[#FAFAFA]">
                {services.map((svc) => (
                  <tr 
                    key={svc.service_id}
                    className="hover:bg-[#141414] transition-colors cursor-pointer"
                    onClick={() => setSelectedService(svc)}
                  >
                    <td className="py-3 px-4 font-medium flex items-center gap-2">
                      <div className="w-6 h-6 rounded bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.18)] flex items-center justify-center shrink-0">
                        {getCategoryIcon(svc.category)}
                      </div>
                      <span className="truncate">{svc.name}</span>
                    </td>

                    <td className="py-3 px-4">
                      <span className="capitalize text-[11px] px-2 py-0.5 rounded border border-[rgba(255, 255, 255,0.20)] bg-[rgba(255, 255, 255,0.08)] text-[#FFFFFF] font-medium">
                        {svc.category}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono text-[11px] text-[#FFFFFF] font-medium">
                      {svc.price_usdc} USDC
                    </td>

                    <td className="py-3 px-4 font-mono text-[11px] text-[#A3A3A3] truncate max-w-[200px]" title={svc.endpoint_url}>
                      {svc.endpoint_url}
                    </td>

                    <td className="py-3 px-4 font-mono text-[11px] text-[#A3A3A3] truncate max-w-[160px]" title={svc.pay_to}>
                      {svc.pay_to ? `${svc.pay_to.slice(0, 6)}...${svc.pay_to.slice(-4)}` : 'Auto'}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedService(svc);
                        }}
                        className="px-2.5 py-1 rounded bg-[#141414] hover:bg-[#1A1A1A] text-[#FFFFFF] border border-[rgba(255, 255, 255,0.25)] text-xs font-medium cursor-pointer transition-colors"
                      >
                        View Specs
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
