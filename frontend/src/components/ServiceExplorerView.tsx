import React, { useState } from 'react';
import { ServiceDefinition, ReputationMetrics } from '../types';
import { 
  Search, 
  ShieldCheck
} from 'lucide-react';

interface ServiceExplorerViewProps {
  services: ServiceDefinition[];
  reputations: Record<string, ReputationMetrics>;
  onSelectService: (service: ServiceDefinition) => void;
  onRunService: (service: ServiceDefinition) => void;
}

export const ServiceExplorerView: React.FC<ServiceExplorerViewProps> = ({
  services,
  reputations,
  onSelectService,
  onRunService
}) => {
  const [explorerTab, setExplorerTab] = useState<'services' | 'endpoints' | 'bundles'>('services');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [maxPrice, setMaxPrice] = useState<string>('');
  const [sortField, setSortField] = useState<'price' | 'name' | 'calls'>('price');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const itemsPerPage = 8;

  const filtered = services.filter(s => {
    if (categoryFilter !== 'all' && s.category !== categoryFilter) return false;
    if (maxPrice && parseFloat(s.price_usdc) > parseFloat(maxPrice)) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.service_id.toLowerCase().includes(q) ||
        s.endpoint_url.toLowerCase().includes(q)
      );
    }
    return true;
  }).sort((a, b) => {
    if (sortField === 'price') return parseFloat(a.price_usdc) - parseFloat(b.price_usdc);
    if (sortField === 'name') return a.name.localeCompare(b.name);
    const callsA = reputations[a.service_id]?.total_calls || 0;
    const callsB = reputations[b.service_id]?.total_calls || 0;
    return callsB - callsA;
  });

  const totalPages = Math.ceil(filtered.length / itemsPerPage) || 1;
  const paginated = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div className="space-y-6">
      {/* Top Navigation Subtabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs font-mono">
          <button
            onClick={() => setExplorerTab('services')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              explorerTab === 'services' ? 'bg-blue-600 text-white font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Services ({services.length})
          </button>
          <button
            onClick={() => setExplorerTab('endpoints')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              explorerTab === 'endpoints' ? 'bg-blue-600 text-white font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Endpoints
          </button>
          <button
            onClick={() => setExplorerTab('bundles')}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              explorerTab === 'bundles' ? 'bg-blue-600 text-white font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Bundles (3)
          </button>
        </div>

        <div className="text-xs font-mono text-slate-400">
          Showing <span className="text-white font-bold">{filtered.length}</span> matching services
        </div>
      </div>

      {/* Explorer Filtering Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 bg-slate-900/60 p-3.5 rounded-xl border border-slate-800 text-xs font-mono">
        <div className="sm:col-span-5 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, endpoint or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="sm:col-span-3">
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-blue-500 capitalize"
          >
            <option value="all">All Categories</option>
            <option value="data">Data</option>
            <option value="scraping">Web Scraping</option>
            <option value="inference">AI Inference</option>
          </select>
        </div>

        <div className="sm:col-span-2">
          <input
            type="text"
            placeholder="Max USDC..."
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="sm:col-span-2">
          <select
            value={sortField}
            onChange={(e: any) => setSortField(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-blue-500"
          >
            <option value="price">Sort: Price</option>
            <option value="calls">Sort: Calls</option>
            <option value="name">Sort: Name</option>
          </select>
        </div>
      </div>

      {/* Explorer Content based on Subtab */}
      {explorerTab === 'services' && (
        <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800 shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-4 py-3.5">Rank</th>
                  <th className="px-4 py-3.5">Service Name & Domain</th>
                  <th className="px-4 py-3.5">Category</th>
                  <th className="px-4 py-3.5">Endpoints</th>
                  <th className="px-4 py-3.5">Price / Call</th>
                  <th className="px-4 py-3.5">Network</th>
                  <th className="px-4 py-3.5">Verification</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {paginated.map((svc, idx) => {
                  const rep = reputations[svc.service_id];
                  const calls = rep?.total_calls || 0;

                  return (
                    <tr 
                      key={svc.service_id} 
                      className="hover:bg-slate-900/50 transition-colors cursor-pointer"
                      onClick={() => onSelectService(svc)}
                    >
                      <td className="px-4 py-3.5 text-slate-500 font-bold">
                        #{(currentPage - 1) * itemsPerPage + idx + 1}
                      </td>

                      <td className="px-4 py-3.5">
                        <div className="font-bold text-white font-sans text-sm">{svc.name}</div>
                        <span className="text-[11px] text-slate-400 font-mono">{svc.endpoint_url}</span>
                      </td>

                      <td className="px-4 py-3.5">
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {svc.category}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 text-slate-300">
                        1 endpoint
                      </td>

                      <td className="px-4 py-3.5 text-emerald-400 font-bold">
                        {svc.price_usdc} USDC
                      </td>

                      <td className="px-4 py-3.5 text-slate-300">
                        Base Sepolia
                      </td>

                      <td className="px-4 py-3.5">
                        {calls > 0 ? (
                          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            <span>Verified</span>
                          </span>
                        ) : (
                          <span className="text-slate-500 text-[11px]">Limited data</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5 text-right space-x-2" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => onSelectService(svc)}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors border border-slate-700"
                        >
                          Specs
                        </button>
                        <button
                          onClick={() => onRunService(svc)}
                          className="px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-colors"
                        >
                          Run
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="p-4 border-t border-slate-800/80 bg-slate-900/60 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Page {currentPage} of {totalPages}</span>
              <div className="flex gap-2">
                <button
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200"
                >
                  Previous
                </button>
                <button
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {explorerTab === 'endpoints' && (
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-white font-mono uppercase">Direct Endpoint Explorer</h3>
          <div className="space-y-3 font-mono text-xs">
            {services.map(svc => (
              <div key={svc.service_id} className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-blue-400 font-bold uppercase text-[10px] bg-blue-950 px-1.5 py-0.5 rounded border border-blue-800">POST</span>
                    <span className="text-white font-semibold">{svc.endpoint_url}</span>
                  </div>
                  <p className="text-slate-400 text-xs font-sans mt-1">{svc.description}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-emerald-400 font-bold">{svc.price_usdc} USDC</span>
                  <button
                    onClick={() => onRunService(svc)}
                    className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold"
                  >
                    Invoke
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {explorerTab === 'bundles' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3">
            <span className="text-cyan-400 font-mono text-xs uppercase font-bold">Pipeline Bundle</span>
            <h4 className="text-base font-bold text-white">Full Market Intelligence</h4>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Combines financial market data extraction with multi-token analytical inference.
            </p>
            <div className="pt-2 flex items-center justify-between border-t border-slate-800 text-xs font-mono">
              <span className="text-emerald-400 font-bold">~0.006 USDC</span>
              <button 
                onClick={() => onRunService(services[0])}
                className="px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white font-bold"
              >
                Run Bundle
              </button>
            </div>
          </div>

          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3">
            <span className="text-amber-400 font-mono text-xs uppercase font-bold">Pipeline Bundle</span>
            <h4 className="text-base font-bold text-white">Deep Web Synthesis</h4>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Scrapes web documentation and feeds parsed content into LLM summarization.
            </p>
            <div className="pt-2 flex items-center justify-between border-t border-slate-800 text-xs font-mono">
              <span className="text-emerald-400 font-bold">~0.007 USDC</span>
              <button 
                onClick={() => onRunService(services[1] || services[0])}
                className="px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white font-bold"
              >
                Run Bundle
              </button>
            </div>
          </div>

          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3">
            <span className="text-purple-400 font-mono text-xs uppercase font-bold">Pipeline Bundle</span>
            <h4 className="text-base font-bold text-white">Direct Inference Reasoning</h4>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Multi-token reasoning with schema adherence and deterministic output guarantees.
            </p>
            <div className="pt-2 flex items-center justify-between border-t border-slate-800 text-xs font-mono">
              <span className="text-emerald-400 font-bold">~0.004 USDC</span>
              <button 
                onClick={() => onRunService(services[2] || services[0])}
                className="px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white font-bold"
              >
                Run Bundle
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
