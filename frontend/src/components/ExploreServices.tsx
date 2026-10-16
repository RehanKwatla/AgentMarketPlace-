import React, { useState } from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { Search, List, Grid } from 'lucide-react';
import { ServiceCard } from './ServiceCard';

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
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [category, setCategory] = useState<string>('all');
  const [networkFilter, setNetworkFilter] = useState<string>('all');
  const [priceFilter, setPriceFilter] = useState<string>('all');
  const [query, setQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'price_asc' | 'price_desc' | 'calls' | 'latency' | 'name'>('price_asc');

  const filtered = services.filter(s => {
    if (category !== 'all' && s.category !== category) return false;
    if (networkFilter !== 'all' && s.network !== networkFilter) return false;
    if (priceFilter === 'under_003' && parseFloat(s.price_usdc) > 0.003) return false;
    if (priceFilter === 'under_005' && parseFloat(s.price_usdc) > 0.005) return false;

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
    if (sortBy === 'price_asc') return parseFloat(a.price_usdc) - parseFloat(b.price_usdc);
    if (sortBy === 'price_desc') return parseFloat(b.price_usdc) - parseFloat(a.price_usdc);
    if (sortBy === 'latency') {
      const latA = reputations[a.service_id]?.median_latency_ms || 999;
      const latB = reputations[b.service_id]?.median_latency_ms || 999;
      return latA - latB;
    }
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    const callsA = reputations[a.service_id]?.total_calls || 0;
    const callsB = reputations[b.service_id]?.total_calls || 0;
    return callsB - callsA;
  });

  return (
    <div className="space-y-4">
      {/* Search and Filters Bar */}
      <div className="wallet-card rounded-lg p-2.5 flex flex-col md:flex-row items-center gap-2.5 text-xs">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#737373]" />
          <input
            type="text"
            placeholder="Search by name, endpoint, or capability..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.18)] rounded-md pl-8 pr-3 py-1.5 text-[#FAFAFA] placeholder-[#737373] focus:outline-none focus:border-[#FFFFFF] font-sans"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Category Filter */}
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.18)] rounded-md px-2.5 py-1.5 text-[#FAFAFA] focus:outline-none focus:border-[#FFFFFF] font-sans"
          >
            <option value="all">All Categories</option>
            <option value="data">Data</option>
            <option value="scraping">Web Scraping</option>
            <option value="inference">AI Inference</option>
          </select>

          {/* Network Filter */}
          <select
            value={networkFilter}
            onChange={(e) => setNetworkFilter(e.target.value)}
            className="bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.18)] rounded-md px-2.5 py-1.5 text-[#FAFAFA] focus:outline-none focus:border-[#FFFFFF] font-sans"
          >
            <option value="all">All Networks</option>
            <option value="eip155:84532">Base Sepolia</option>
          </select>

          {/* Price Filter */}
          <select
            value={priceFilter}
            onChange={(e) => setPriceFilter(e.target.value)}
            className="bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.18)] rounded-md px-2.5 py-1.5 text-[#FAFAFA] focus:outline-none focus:border-[#FFFFFF] font-sans"
          >
            <option value="all">Any Price</option>
            <option value="under_003">≤ 0.003 USDC</option>
            <option value="under_005">≤ 0.005 USDC</option>
          </select>

          {/* Sort Select */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.18)] rounded-md px-2.5 py-1.5 text-[#FAFAFA] focus:outline-none focus:border-[#FFFFFF] font-sans"
          >
            <option value="price_asc">Price: Low to High</option>
            <option value="price_desc">Price: High to Low</option>
            <option value="latency">Lowest Latency</option>
            <option value="calls">Most Calls</option>
            <option value="name">Name</option>
          </select>

          {/* View Toggle */}
          <div className="flex items-center border border-[rgba(255, 255, 255,0.18)] rounded-md bg-[#0D0D0D] p-0.5 ml-auto md:ml-0">
            <button
              onClick={() => setViewMode('table')}
              className={`p-1 rounded ${viewMode === 'table' ? 'bg-[#171717] text-[#FFFFFF]' : 'text-[#737373] hover:text-[#A3A3A3]'}`}
              title="Table View"
            >
              <List className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('cards')}
              className={`p-1 rounded ${viewMode === 'cards' ? 'bg-[#171717] text-[#FFFFFF]' : 'text-[#737373] hover:text-[#A3A3A3]'}`}
              title="Card View"
            >
              <Grid className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area: Simple Table (Default) or Cards */}
      {filtered.length === 0 ? (
        <div className="wallet-card rounded-lg p-10 text-center text-xs text-[#A3A3A3]">
          No matching services found for the current filters.
        </div>
      ) : viewMode === 'table' ? (
        <div className="wallet-card rounded-lg border border-[rgba(255, 255, 255,0.18)] overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[rgba(255, 255, 255,0.16)] bg-[#0E0E0E] text-[#A3A3A3]">
                <th className="py-2.5 px-4 font-medium">Service Name</th>
                <th className="py-2.5 px-4 font-medium">Category</th>
                <th className="py-2.5 px-4 font-medium">Description</th>
                <th className="py-2.5 px-4 font-medium">Price</th>
                <th className="py-2.5 px-4 font-medium hidden lg:table-cell">Endpoint Route</th>
                <th className="py-2.5 px-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255, 255, 255,0.12)] text-[#FAFAFA]">
              {filtered.map((svc) => (
                <tr 
                  key={svc.service_id}
                  onClick={() => onSelectService(svc)}
                  className="hover:bg-[#151515] transition-colors cursor-pointer"
                >
                  <td className="py-3 px-4 font-medium">
                    <div>{svc.name}</div>
                    <div className="text-[11px] text-[#A3A3A3] font-mono">{svc.service_id}</div>
                  </td>

                  <td className="py-3 px-4">
                    <span className="capitalize text-[11px] px-2 py-0.5 rounded bg-[#171717] text-[#A3A3A3] border border-[rgba(255, 255, 255,0.18)]">
                      {svc.category}
                    </span>
                  </td>

                  <td className="py-3 px-4 text-[#A3A3A3] text-xs max-w-xs truncate font-sans">
                    {svc.description}
                  </td>

                  <td className="py-3 px-4 font-mono font-medium text-[#FFFFFF] whitespace-nowrap">
                    {svc.price_usdc} USDC
                  </td>

                  <td className="py-3 px-4 font-mono text-[11px] text-[#A3A3A3] hidden lg:table-cell max-w-[180px] truncate">
                    {svc.endpoint_url}
                  </td>

                  <td className="py-3 px-4 text-right whitespace-nowrap space-x-1.5">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectService(svc);
                      }}
                      className="px-2.5 py-1 rounded bg-[#171717] hover:bg-[#1F1F1F] text-[#A3A3A3] hover:text-[#FAFAFA] text-xs border border-[rgba(255, 255, 255,0.2)] transition-colors cursor-pointer"
                    >
                      Details
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRunService(svc);
                      }}
                      className="px-2.5 py-1 rounded bg-[#FFFFFF] hover:bg-[#E5E5E5] text-[#0A0A0A] font-medium text-xs transition-colors cursor-pointer"
                    >
                      Use in Task
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {filtered.map((service) => (
            <ServiceCard
              key={service.service_id}
              service={service}
              reputation={reputations[service.service_id]}
              onSelect={onRunService}
              onViewDetail={onSelectService}
            />
          ))}
        </div>
      )}
    </div>
  );
};
