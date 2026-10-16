import React, { useState } from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { Search, ShieldCheck } from 'lucide-react';

interface ExploreServicesProps {
  services: ServiceDefinition[];
  reputations: Record<string, ReputationMetrics>;
  onSelectService: (service: ServiceDefinition) => void;
  onRunService: (service: ServiceDefinition) => void;
}

export const ExploreServices: React.FC<ExploreServicesProps> = ({
  services,
  reputations,
  onSelectService,
  onRunService
}) => {
  const [subTab, setSubTab] = useState<'services' | 'endpoints' | 'bundles'>('services');
  const [category, setCategory] = useState<string>('all');
  const [query, setQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'price' | 'calls' | 'name'>('price');

  const filtered = services.filter(s => {
    if (category !== 'all' && s.category !== category) return false;
    if (query.trim()) {
      const q = query.toLowerCase();
      return (
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.service_id.toLowerCase().includes(q) ||
        s.endpoint_url.toLowerCase().includes(q)
      );
    }
    return true;
  }).sort((a, b) => {
    if (sortBy === 'price') return parseFloat(a.price_usdc) - parseFloat(b.price_usdc);
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    const callsA = reputations[a.service_id]?.total_calls || 0;
    const callsB = reputations[b.service_id]?.total_calls || 0;
    return callsB - callsA;
  });

  return (
    <div className="space-y-4">
      {/* Section Header matching BROWSE label */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <span className="text-[11px] font-mono uppercase font-bold text-[#FF982E] tracking-wider block">
            BROWSE
          </span>
          <h2 className="text-xl sm:text-2xl font-black text-[#F5F5F5] tracking-tight font-sans mt-0.5">
            Explore what your agent can pay for.
          </h2>
        </div>

        {/* Subtabs: Services / Endpoints / Bundles */}
        <div className="flex items-center gap-1 bg-[#171819] border border-[#303133] p-1 rounded-lg text-xs font-mono">
          <button
            onClick={() => setSubTab('services')}
            className={`px-3 py-1 rounded transition-colors ${
              subTab === 'services' ? 'bg-[#FF982E] text-[#101112] font-bold' : 'text-[#96989D] hover:text-[#F5F5F5]'
            }`}
          >
            Services ({services.length})
          </button>
          <button
            onClick={() => setSubTab('endpoints')}
            className={`px-3 py-1 rounded transition-colors ${
              subTab === 'endpoints' ? 'bg-[#FF982E] text-[#101112] font-bold' : 'text-[#96989D] hover:text-[#F5F5F5]'
            }`}
          >
            Endpoints
          </button>
          <button
            onClick={() => setSubTab('bundles')}
            className={`px-3 py-1 rounded transition-colors ${
              subTab === 'bundles' ? 'bg-[#FF982E] text-[#101112] font-bold' : 'text-[#96989D] hover:text-[#F5F5F5]'
            }`}
          >
            Bundles
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#171819] border border-[#303133] rounded-lg p-3 flex flex-col sm:flex-row items-center gap-3 text-xs font-mono">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#96989D]" />
          <input
            type="text"
            placeholder="Search by service, domain, or capability..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-[#101112] border border-[#303133] rounded pl-9 pr-3 py-1.5 text-[#F5F5F5] placeholder-[#96989D] focus:outline-none focus:border-[#FF982E]"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="bg-[#101112] border border-[#303133] rounded px-3 py-1.5 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E] capitalize"
          >
            <option value="all">All Categories</option>
            <option value="data">Data</option>
            <option value="scraping">Web Scraping</option>
            <option value="inference">AI Inference</option>
          </select>

          <select
            value={sortBy}
            onChange={(e: any) => setSortBy(e.target.value)}
            className="bg-[#101112] border border-[#303133] rounded px-3 py-1.5 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E]"
          >
            <option value="price">Lowest Price</option>
            <option value="calls">Most Calls</option>
            <option value="name">Service Name</option>
          </select>
        </div>
      </div>

      {/* Table Content */}
      <div className="bg-[#171819] border border-[#303133] rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#1D1E20] text-[#96989D] border-b border-[#303133] uppercase text-[11px]">
              <tr>
                <th className="px-4 py-3">Service Name & Domain</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Endpoints</th>
                <th className="px-4 py-3">Price / Call</th>
                <th className="px-4 py-3">Network</th>
                <th className="px-4 py-3">Verification</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#303133]">
              {filtered.map((svc) => {
                const rep = reputations[svc.service_id];
                const hasCalls = (rep?.total_calls || 0) > 0;

                return (
                  <tr
                    key={svc.service_id}
                    onClick={() => onSelectService(svc)}
                    className="hover:bg-[#1D1E20] transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <div className="font-bold text-[#F5F5F5] font-sans text-sm">{svc.name}</div>
                      <span className="text-[10px] text-[#96989D] font-mono">{svc.endpoint_url}</span>
                    </td>

                    <td className="px-4 py-3">
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-[#101112] border border-[#303133] text-[#F5F5F5]">
                        {svc.category}
                      </span>
                    </td>

                    <td className="px-4 py-3 text-[#96989D]">
                      1 endpoint
                    </td>

                    <td className="px-4 py-3 text-[#FF982E] font-bold">
                      {svc.price_usdc} USDC
                    </td>

                    <td className="px-4 py-3 text-[#96989D]">
                      Base Sepolia
                    </td>

                    <td className="px-4 py-3">
                      {hasCalls ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-[#58B779]">
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>Verified</span>
                        </span>
                      ) : (
                        <span className="text-[#96989D] text-[11px]">Limited data</span>
                      )}
                    </td>

                    <td className="px-4 py-3 text-right space-x-2" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => onSelectService(svc)}
                        className="px-2.5 py-1 rounded bg-[#101112] hover:bg-[#1D1E20] text-[#F5F5F5] border border-[#303133] font-semibold"
                      >
                        Specs
                      </button>
                      <button
                        onClick={() => onRunService(svc)}
                        className="px-3 py-1 rounded bg-[#FF982E] hover:bg-[#FF982E]/90 text-[#101112] font-bold"
                      >
                        Use
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
