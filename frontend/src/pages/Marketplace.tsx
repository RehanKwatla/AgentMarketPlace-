import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ExploreServices } from '../components/ExploreServices';
import { useMarketplace } from '../context/MarketplaceContext';

export const Marketplace: React.FC = () => {
  const navigate = useNavigate();
  const { 
    services, 
    reputations, 
    setSelectedService, 
    useServiceInTask,
    searchQuery 
  } = useMarketplace();

  const handleRunService = (service: any) => {
    useServiceInTask(service);
    navigate('/buyer');
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Concise Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[rgba(120,160,153,0.16)] pb-4">
        <div>
          <h1 className="text-2xl font-semibold text-[#F4F7F6]">
            Service Marketplace
          </h1>
          <p className="text-xs text-[#9BA5A2] mt-0.5">
            Verified AI microservices available on Base Sepolia with HTTP 402 pay-per-call endpoints.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-[#9BA5A2]">
          <span className="px-2.5 py-1 rounded bg-[#121616] border border-[rgba(120,160,153,0.18)]">
            Base Sepolia
          </span>
          <span className="px-2.5 py-1 rounded bg-[#121616] border border-[rgba(120,160,153,0.18)] text-[#36D6C8]">
            USDC
          </span>
          <span className="px-2.5 py-1 rounded bg-[#121616] border border-[rgba(120,160,153,0.18)] text-[#42C995]">
            {services.length} active
          </span>
        </div>
      </div>

      {/* Main Service Explorer */}
      <ExploreServices
        services={searchQuery.trim() 
          ? services.filter(s => 
              s.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
              s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
              s.service_id.toLowerCase().includes(searchQuery.toLowerCase())
            )
          : services
        }
        reputations={reputations}
        onSelectService={(s) => setSelectedService(s)}
        onRunService={handleRunService}
      />
    </div>
  );
};
