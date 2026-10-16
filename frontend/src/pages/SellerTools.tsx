import React from 'react';
import { SellerToolsView as SellerToolsFormComponent } from '../components/SellerToolsView';
import { useMarketplace } from '../context/MarketplaceContext';
import { Database, Globe, Cpu, ShieldCheck } from 'lucide-react';

export const SellerTools: React.FC = () => {
  const { services, setSelectedService } = useMarketplace();

  const getCategoryIcon = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'data': return <Database className="w-3.5 h-3.5 text-[#36D6C8]" />;
      case 'scraping': return <Globe className="w-3.5 h-3.5 text-[#42C995]" />;
      case 'inference': return <Cpu className="w-3.5 h-3.5 text-[#53E3D6]" />;
      default: return <ShieldCheck className="w-3.5 h-3.5 text-[#36D6C8]" />;
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
            <h2 className="text-sm font-semibold text-[#F4F7F6]">
              Registered Services ({services.length})
            </h2>
            <p className="text-xs text-[#A0AAA7]">
              Active microservices registered on Base Sepolia.
            </p>
          </div>

          <span className="text-[11px] font-mono text-[#42C995] bg-[rgba(66,201,149,0.08)] border border-[rgba(66,201,149,0.20)] px-2 py-0.5 rounded">
            All Endpoints Active
          </span>
        </div>

        <div className="bg-[#101514] rounded-xl border border-[rgba(120,160,153,0.16)] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[rgba(120,160,153,0.14)] bg-[#0D1111] text-[#A0AAA7]">
                  <th className="py-2.5 px-4 font-medium text-xs">Service Name</th>
                  <th className="py-2.5 px-4 font-medium text-xs">Category</th>
                  <th className="py-2.5 px-4 font-medium text-xs">Price</th>
                  <th className="py-2.5 px-4 font-medium text-xs">Endpoint</th>
                  <th className="py-2.5 px-4 font-medium text-xs">PayTo Recipient</th>
                  <th className="py-2.5 px-4 font-medium text-xs text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(120,160,153,0.10)] text-[#F4F7F6]">
                {services.map((svc) => (
                  <tr 
                    key={svc.service_id}
                    className="hover:bg-[#141A19] transition-colors cursor-pointer"
                    onClick={() => setSelectedService(svc)}
                  >
                    <td className="py-3 px-4 font-medium flex items-center gap-2">
                      <div className="w-6 h-6 rounded bg-[#0D1111] border border-[rgba(120,160,153,0.18)] flex items-center justify-center shrink-0">
                        {getCategoryIcon(svc.category)}
                      </div>
                      <span className="truncate">{svc.name}</span>
                    </td>

                    <td className="py-3 px-4">
                      <span className="capitalize text-[11px] px-2 py-0.5 rounded border border-[rgba(54,214,200,0.20)] bg-[rgba(54,214,200,0.08)] text-[#36D6C8] font-medium">
                        {svc.category}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono text-[11px] text-[#36D6C8] font-medium">
                      {svc.price_usdc} USDC
                    </td>

                    <td className="py-3 px-4 font-mono text-[11px] text-[#A0AAA7] truncate max-w-[200px]" title={svc.endpoint_url}>
                      {svc.endpoint_url}
                    </td>

                    <td className="py-3 px-4 font-mono text-[11px] text-[#A0AAA7] truncate max-w-[160px]" title={svc.pay_to}>
                      {svc.pay_to ? `${svc.pay_to.slice(0, 6)}...${svc.pay_to.slice(-4)}` : 'Auto'}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedService(svc);
                        }}
                        className="px-2.5 py-1 rounded bg-[#141A19] hover:bg-[#1A2221] text-[#36D6C8] border border-[rgba(54,214,200,0.25)] text-xs font-medium cursor-pointer transition-colors"
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
