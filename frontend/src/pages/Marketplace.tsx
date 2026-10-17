import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, 
  List, 
  Grid, 
  RotateCw, 
  X, 
  ArrowRight,
  Database,
  Globe,
  Cpu,
  Layers,
  Activity
} from 'lucide-react';
import { useMarketplace } from '../context/MarketplaceContext';
import { ServiceDefinition } from '../types';
import { PageHeader } from '../components/ui/PageHeader';
import { ServiceCard } from '../components/ServiceCard';
import { EmptyState } from '../components/ui/EmptyState';
import { fetchRecommendations } from '../api/client';

export const Marketplace: React.FC = () => {
  const navigate = useNavigate();
  const { 
    services, 
    reputations, 
    setSelectedService, 
    useServiceInTask,
    fetchError,
    refreshData,
    searchQuery: globalSearchQuery,
    setSearchQuery: setGlobalSearchQuery
  } = useMarketplace();

  // Local filter states
  const [localSearch, setLocalSearch] = useState<string>(globalSearchQuery || '');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [maxPrice, setMaxPrice] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'enabled' | 'disabled'>('all');
  const [sortBy, setSortBy] = useState<'price_asc' | 'price_desc' | 'reputation' | 'calls' | 'name'>('price_asc');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [recommendationTask, setRecommendationTask] = useState('Find a reliable agent for market data');
  const [recommendation, setRecommendation] = useState<any>(null);
  const [recommendationError, setRecommendationError] = useState<string | null>(null);
  const [isRecommending, setIsRecommending] = useState(false);

  const runRecommendation = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsRecommending(true);
    setRecommendationError(null);
    try {
      const category = /scrap|web|page|document/i.test(recommendationTask) ? 'scraping'
        : /summar|infer|classif|compar|reason/i.test(recommendationTask) ? 'inference' : 'data';
      setRecommendation(await fetchRecommendations({ task_prompt: recommendationTask, category, max_budget_usdc: '0.05' }));
    } catch (error: any) {
      setRecommendationError(error.message || 'Could not calculate recommendation');
    } finally {
      setIsRecommending(false);
    }
  };

  // Sync global search from context if updated externally
  React.useEffect(() => {
    if (globalSearchQuery !== localSearch) {
      setLocalSearch(globalSearchQuery);
    }
  }, [globalSearchQuery]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await refreshData();
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleUseService = (service: ServiceDefinition) => {
    useServiceInTask(service);
    navigate('/buyer');
  };

  const handleSearchChange = (val: string) => {
    setLocalSearch(val);
    setGlobalSearchQuery(val);
  };

  const clearAllFilters = () => {
    setLocalSearch('');
    setGlobalSearchQuery('');
    setSelectedCategory('all');
    setMaxPrice('all');
    setStatusFilter('all');
    setSortBy('price_asc');
  };

  const hasActiveFilters = 
    localSearch.trim() !== '' || 
    selectedCategory !== 'all' || 
    maxPrice !== 'all' || 
    statusFilter !== 'all' || 
    sortBy !== 'price_asc';

  // Client-side filtering & sorting respecting actual schemas
  const filteredServices = useMemo(() => {
    return services.filter((s) => {
      // Category filter
      if (selectedCategory !== 'all' && s.category !== selectedCategory) {
        return false;
      }

      // Max price filter
      if (maxPrice !== 'all') {
        const priceNum = parseFloat(s.price_usdc || '0');
        const maxNum = parseFloat(maxPrice);
        if (priceNum > maxNum) return false;
      }

      // Status filter
      if (statusFilter === 'enabled') {
        const isEnabled = s.is_active && (s.enabled !== false);
        if (!isEnabled) return false;
      } else if (statusFilter === 'disabled') {
        const isEnabled = s.is_active && (s.enabled !== false);
        if (isEnabled) return false;
      }

      // Search query (matches name, service_id, description, capabilities, endpoint)
      if (localSearch.trim()) {
        const q = localSearch.toLowerCase();
        const matchesName = s.name.toLowerCase().includes(q);
        const matchesId = s.service_id.toLowerCase().includes(q);
        const matchesDesc = (s.description || '').toLowerCase().includes(q);
        const matchesEndpoint = (s.endpoint_url || '').toLowerCase().includes(q);
        const matchesCaps = s.capabilities?.some(c => c.toLowerCase().includes(q)) ?? false;

        if (!matchesName && !matchesId && !matchesDesc && !matchesEndpoint && !matchesCaps) {
          return false;
        }
      }

      return true;
    }).sort((a, b) => {
      const repA = a.reputation || reputations[a.service_id];
      const repB = b.reputation || reputations[b.service_id];

      if (sortBy === 'price_asc') {
        return parseFloat(a.price_usdc || '0') - parseFloat(b.price_usdc || '0');
      }
      if (sortBy === 'price_desc') {
        return parseFloat(b.price_usdc || '0') - parseFloat(a.price_usdc || '0');
      }
      if (sortBy === 'reputation') {
        const scoreA = repA?.reputation_score ?? -1;
        const scoreB = repB?.reputation_score ?? -1;
        return scoreB - scoreA;
      }
      if (sortBy === 'calls') {
        const callsA = repA?.total_calls ?? 0;
        const callsB = repB?.total_calls ?? 0;
        return callsB - callsA;
      }
      if (sortBy === 'name') {
        return a.name.localeCompare(b.name);
      }
      return 0;
    });
  }, [services, reputations, selectedCategory, maxPrice, statusFilter, localSearch, sortBy]);

  // Category counts
  const categoryCounts = useMemo(() => {
    return {
      all: services.length,
      data: services.filter(s => s.category === 'data').length,
      scraping: services.filter(s => s.category === 'scraping').length,
      inference: services.filter(s => s.category === 'inference').length,
    };
  }, [services]);

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-12">
      {/* 1. Page Header */}
      <PageHeader
        title="Service Marketplace"
        description="Autonomous AI microservice directory compliant with x402 v2 payment specifications on Base Sepolia."
        badge={
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#DED8CD]/60 border border-[#CFC7BB] text-[11px] font-mono text-[#82786F]">
            <span className="w-2 h-2 rounded-full bg-[#38865B]" />
            <span className="text-[#241B19] font-medium">{services.length} Registered</span>
            <span className="text-[#CFC7BB]">•</span>
            <span className="text-[#7D292D] font-semibold">Base Sepolia USDC</span>
          </div>
        }
        actions={
          <div className="flex items-center gap-2">
            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearAllFilters}
                className="px-3 py-1.5 rounded-md bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#82786F] hover:text-[#7D292D] text-xs font-mono border border-[#CFC7BB] flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
                title="Reset all search filters"
              >
                <X className="w-3.5 h-3.5" />
                <span>Reset Filters</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="px-3 py-1.5 rounded-md bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono border border-[#CFC7BB] flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 shadow-xs"
              title="Refresh services from registry"
            >
              <RotateCw className={`w-3.5 h-3.5 text-[#82786F] ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>{isRefreshing ? 'Syncing...' : 'Sync Registry'}</span>
            </button>
          </div>
        }
      />

      <section className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] p-5 space-y-3" aria-label="Recommendation inspection">
        <div>
          <h2 className="text-sm font-semibold text-[#241B19]">Recommendation inspection</h2>
          <p className="text-xs text-[#82786F]">Ranking is computed by the registry API. A recommendation does not authorize payment.</p>
        </div>
        <form onSubmit={runRecommendation} className="flex flex-wrap gap-2">
          <input aria-label="Task for recommendation" value={recommendationTask} onChange={e => setRecommendationTask(e.target.value)} className="min-w-[240px] flex-1 rounded-md border border-[#CFC7BB] bg-white px-3 py-2 text-sm" />
          <button disabled={isRecommending} className="rounded-md bg-[#7D292D] px-4 py-2 text-sm text-white disabled:opacity-60">{isRecommending ? 'Ranking…' : 'Rank candidates'}</button>
        </form>
        {recommendationError && <p role="alert" className="text-sm text-red-700">{recommendationError}</p>}
        {recommendation && <div className="space-y-2 text-sm">
          <p className="text-[#82786F]">{recommendation.explanation_summary}</p>
          <div className="grid gap-2 md:grid-cols-3">{recommendation.recommendations.map((candidate: any) => <article key={candidate.service_id} className="rounded-lg border border-[#CFC7BB] bg-white p-3">
            <div className="flex justify-between gap-2"><strong>{candidate.rank}. {candidate.name}</strong><span>{candidate.price_usdc} USDC</span></div>
            <p className="mt-1 text-xs">Score {candidate.weighted_score.toFixed(3)} · {candidate.performance.evidence_status} · {candidate.performance.sample_size} ledger records</p>
            <p className="mt-1 text-xs text-[#82786F]">Success: {candidate.performance.success_rate === null ? 'NEW' : `${(candidate.performance.success_rate * 100).toFixed(1)}%`} · Median observed latency: {candidate.performance.median_latency_ms === null ? 'NEW' : `${candidate.performance.median_latency_ms} ms`}</p>
          </article>)}</div>
          {recommendation.rejected_candidates.length > 0 && <details><summary className="cursor-pointer text-xs">Rejected alternatives ({recommendation.rejected_candidates.length})</summary><ul className="mt-1 list-disc pl-5 text-xs">{recommendation.rejected_candidates.map((candidate: any) => <li key={candidate.service_id}>{candidate.name}: {candidate.rejection_reasons.join('; ')}</li>)}</ul></details>}
        </div>}
      </section>

      {/* 2. Category Selector Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-[#CFC7BB]/60 pb-3">
        <button
          type="button"
          onClick={() => setSelectedCategory('all')}
          className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center gap-2 cursor-pointer ${
            selectedCategory === 'all'
              ? 'bg-[#7D292D] text-[#F7F4EE] font-semibold shadow-sm'
              : 'bg-[#F7F4EE] hover:bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB]'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>All Categories</span>
          <span className={`px-1.5 py-0.2 rounded text-[10px] ${selectedCategory === 'all' ? 'bg-[#612024] text-[#F7F4EE]' : 'bg-[#DED8CD] text-[#82786F]'}`}>
            {categoryCounts.all}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setSelectedCategory('data')}
          className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center gap-2 cursor-pointer ${
            selectedCategory === 'data'
              ? 'bg-[#7D292D] text-[#F7F4EE] font-semibold shadow-sm'
              : 'bg-[#F7F4EE] hover:bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB]'
          }`}
        >
          <Database className={`w-3.5 h-3.5 ${selectedCategory === 'data' ? 'text-[#F7F4EE]' : 'text-[#586452]'}`} />
          <span>Data Providers</span>
          <span className={`px-1.5 py-0.2 rounded text-[10px] ${selectedCategory === 'data' ? 'bg-[#612024] text-[#F7F4EE]' : 'bg-[#DED8CD] text-[#82786F]'}`}>
            {categoryCounts.data}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setSelectedCategory('scraping')}
          className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center gap-2 cursor-pointer ${
            selectedCategory === 'scraping'
              ? 'bg-[#7D292D] text-[#F7F4EE] font-semibold shadow-sm'
              : 'bg-[#F7F4EE] hover:bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB]'
          }`}
        >
          <Globe className={`w-3.5 h-3.5 ${selectedCategory === 'scraping' ? 'text-[#F7F4EE]' : 'text-[#A86E24]'}`} />
          <span>Web Scraping</span>
          <span className={`px-1.5 py-0.2 rounded text-[10px] ${selectedCategory === 'scraping' ? 'bg-[#612024] text-[#F7F4EE]' : 'bg-[#DED8CD] text-[#82786F]'}`}>
            {categoryCounts.scraping}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setSelectedCategory('inference')}
          className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all flex items-center gap-2 cursor-pointer ${
            selectedCategory === 'inference'
              ? 'bg-[#7D292D] text-[#F7F4EE] font-semibold shadow-sm'
              : 'bg-[#F7F4EE] hover:bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB]'
          }`}
        >
          <Cpu className={`w-3.5 h-3.5 ${selectedCategory === 'inference' ? 'text-[#F7F4EE]' : 'text-[#7D292D]'}`} />
          <span>AI Inference</span>
          <span className={`px-1.5 py-0.2 rounded text-[10px] ${selectedCategory === 'inference' ? 'bg-[#612024] text-[#F7F4EE]' : 'bg-[#DED8CD] text-[#82786F]'}`}>
            {categoryCounts.inference}
          </span>
        </button>
      </div>

      {/* 3. Search & Operational Filter Bar */}
      <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-4 space-y-3">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 text-xs">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#82786F]" />
            <input
              type="text"
              placeholder="Search by service name, ID, capability, description, or endpoint..."
              value={localSearch}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="w-full bg-[#FFFFFF] border border-[#CFC7BB] rounded-lg pl-9 pr-8 py-2 text-xs font-mono text-[#241B19] placeholder-[#82786F] focus:outline-none focus:border-[#7D292D] focus:ring-1 focus:ring-[#7D292D] transition-colors shadow-xs"
            />
            {localSearch && (
              <button
                onClick={() => handleSearchChange('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#82786F] hover:text-[#241B19]"
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Filters controls */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Max Price Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-mono text-[#82786F] whitespace-nowrap">Max Price:</span>
              <select
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-lg px-2.5 py-2 text-xs font-mono text-[#241B19] focus:outline-none focus:border-[#7D292D] cursor-pointer shadow-xs"
              >
                <option value="all">Any Price</option>
                <option value="0.002">≤ 0.002 USDC</option>
                <option value="0.003">≤ 0.003 USDC</option>
                <option value="0.004">≤ 0.004 USDC</option>
                <option value="0.005">≤ 0.005 USDC</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-mono text-[#82786F] whitespace-nowrap">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-lg px-2.5 py-2 text-xs font-mono text-[#241B19] focus:outline-none focus:border-[#7D292D] cursor-pointer shadow-xs"
              >
                <option value="all">All Statuses</option>
                <option value="enabled">Enabled Only</option>
                <option value="disabled">Disabled Only</option>
              </select>
            </div>

            {/* Sort Dropdown */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-mono text-[#82786F] whitespace-nowrap">Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-lg px-2.5 py-2 text-xs font-mono text-[#241B19] focus:outline-none focus:border-[#7D292D] cursor-pointer shadow-xs"
              >
                <option value="price_asc">Price: Low to High</option>
                <option value="price_desc">Price: High to Low</option>
                <option value="reputation">Reputation Score</option>
                <option value="calls">Most Calls Recorded</option>
                <option value="name">Name (A-Z)</option>
              </select>
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center border border-[#CFC7BB] rounded-lg bg-[#FFFFFF] p-0.5 ml-auto shadow-xs">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded-md transition-colors ${
                  viewMode === 'grid' 
                    ? 'bg-[#7D292D] text-[#F7F4EE]' 
                    : 'text-[#82786F] hover:text-[#241B19]'
                }`}
                title="Grid View"
              >
                <Grid className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`p-1.5 rounded-md transition-colors ${
                  viewMode === 'table' 
                    ? 'bg-[#7D292D] text-[#F7F4EE]' 
                    : 'text-[#82786F] hover:text-[#241B19]'
                }`}
                title="List / Table View"
              >
                <List className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Active Filter Indicators */}
        {hasActiveFilters && (
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-[#CFC7BB]/60 text-[11px] font-mono">
            <span className="text-[#82786F]">Active filters:</span>
            {localSearch && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB]">
                Query: "{localSearch}"
                <button type="button" aria-label="Clear query filter" onClick={() => handleSearchChange('')} className="hover:text-[#7D292D]">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {selectedCategory !== 'all' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB]">
                Category: {selectedCategory}
                <button type="button" aria-label="Clear category filter" onClick={() => setSelectedCategory('all')} className="hover:text-[#7D292D]">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {maxPrice !== 'all' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB]">
                Max Price: ≤ {maxPrice} USDC
                <button type="button" aria-label="Clear price filter" onClick={() => setMaxPrice('all')} className="hover:text-[#7D292D]">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {statusFilter !== 'all' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#DED8CD]/60 text-[#241B19] border border-[#CFC7BB]">
                Status: {statusFilter}
                <button type="button" aria-label="Clear status filter" onClick={() => setStatusFilter('all')} className="hover:text-[#7D292D]">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            <button 
              type="button"
              onClick={clearAllFilters}
              className="text-[#7D292D] hover:underline ml-2 cursor-pointer font-medium"
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {/* 4. Service Results Count & Summary */}
      <div className="flex items-center justify-between text-xs font-mono text-[#82786F]">
        <div>
          Showing <span className="text-[#241B19] font-bold">{filteredServices.length}</span> of {services.length} services
        </div>
        <div>
          Protocol: <span className="text-[#7D292D] font-medium">x402 EIP-712</span>
        </div>
      </div>

      {/* 5. Main Services Content (Empty, Grid, or Table) */}
      {fetchError && services.length === 0 ? (
        <div className="rounded-xl border border-[#F8B4B4] bg-[#FDE8E8] p-8 text-center space-y-3 shadow-xs">
          <p className="text-sm font-semibold text-[#7D292D]">Failed to connect to Service Registry</p>
          <p className="text-xs text-[#82786F] max-w-md mx-auto">{fetchError}</p>
          <button
            type="button"
            onClick={handleRefresh}
            className="px-4 py-2 rounded-md bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] text-xs font-mono shadow-sm"
          >
            Retry Connection
          </button>
        </div>
      ) : filteredServices.length === 0 ? (
        <EmptyState
          title="No services match your filters"
          description="Try broadening your search term, selecting another category, or resetting your maximum price threshold."
          action={
            <button
              type="button"
              onClick={clearAllFilters}
              className="px-4 py-2 rounded-md bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-semibold text-xs font-mono transition-colors cursor-pointer shadow-sm"
            >
              Clear All Filters
            </button>
          }
        />
      ) : viewMode === 'grid' ? (
        /* Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredServices.map((svc) => (
            <ServiceCard
              key={svc.service_id}
              service={svc}
              reputation={svc.reputation || reputations[svc.service_id]}
              onViewDetail={(s) => setSelectedService(s)}
              onSelect={handleUseService}
            />
          ))}
        </div>
      ) : (
        /* Table / List View */
        <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#CFC7BB] bg-[#DED8CD]/60 text-[#82786F] font-mono text-[11px]">
                  <th className="py-3 px-4 font-medium">Service Name & ID</th>
                  <th className="py-3 px-4 font-medium">Category</th>
                  <th className="py-3 px-4 font-medium">Status</th>
                  <th className="py-3 px-4 font-medium">Price</th>
                  <th className="py-3 px-4 font-medium">Telemetry</th>
                  <th className="py-3 px-4 font-medium hidden lg:table-cell">Endpoint Route</th>
                  <th className="py-3 px-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#CFC7BB]/60 font-mono text-xs">
                {filteredServices.map((svc) => {
                  const rep = svc.reputation || reputations[svc.service_id];
                  const totalCalls = rep?.total_calls ?? 0;
                  const isEnabled = svc.is_active && (svc.enabled !== false);

                  return (
                    <tr
                      key={svc.service_id}
                      onClick={() => setSelectedService(svc)}
                      className="hover:bg-[#DED8CD]/40 transition-colors cursor-pointer group"
                    >
                      <td className="py-3 px-4">
                        <div className="font-semibold text-[#241B19] font-sans group-hover:text-[#7D292D]">
                          {svc.name}
                        </div>
                        <div className="text-[10px] text-[#82786F] mt-0.5">
                          ID: {svc.service_id}
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <span className="inline-block uppercase text-[10px] px-2 py-0.5 rounded bg-[#DED8CD]/60 border border-[#CFC7BB] text-[#586452] font-semibold">
                          {svc.category}
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] border ${
                          isEnabled 
                            ? 'bg-[#E4EFE8] text-[#38865B] border-[#A8B3A1]/70' 
                            : 'bg-[#F4ECEB] text-[#7D292D] border-[#CFC7BB]'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${isEnabled ? 'bg-[#38865B]' : 'bg-[#7D292D]'}`} />
                          <span>{isEnabled ? 'Enabled' : 'Disabled'}</span>
                        </span>
                      </td>

                      <td className="py-3 px-4 font-bold text-[#7D292D]">
                        {svc.price_usdc} USDC
                      </td>

                      <td className="py-3 px-4">
                        {totalCalls > 0 ? (
                          <div className="space-y-0.5">
                            <div className="text-[#38865B] flex items-center gap-1 font-semibold">
                              <Activity className="w-3 h-3" />
                              <span>{rep?.reputation_score}% score</span>
                            </div>
                            <div className="text-[10px] text-[#82786F]">
                              {totalCalls} calls • {rep?.median_latency_ms?.toFixed(0)}ms
                            </div>
                          </div>
                        ) : (
                          <span className="text-[#82786F]">No call history</span>
                        )}
                      </td>

                      <td className="py-3 px-4 hidden lg:table-cell text-[#82786F] text-[11px] truncate max-w-[220px]">
                        {svc.endpoint_url}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            onClick={() => setSelectedService(svc)}
                            className="px-2.5 py-1 rounded bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono border border-[#CFC7BB] transition-colors shadow-xs"
                          >
                            Details
                          </button>
                          <button
                            type="button"
                            onClick={() => handleUseService(svc)}
                            className="px-3 py-1 rounded bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] font-semibold text-xs font-mono transition-colors flex items-center gap-1 shadow-sm"
                          >
                            <span>Use</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Marketplace;
