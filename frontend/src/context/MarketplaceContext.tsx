import React, { createContext, useContext, useState, useEffect, useMemo, ReactNode } from 'react';
import { 
  ServiceDefinition, 
  LedgerRecord, 
  ReputationMetrics, 
  TaskResponse, 
  TaskPlanPreview, 
  PlannedStepEstimate 
} from '../types';
import { 
  fetchHealth, 
  fetchServices, 
  fetchLedger, 
  fetchReputations, 
  submitBuyerTask, 
  fetchLedgerRecord 
} from '../api/client';

interface MarketplaceContextType {
  services: ServiceDefinition[];
  ledger: LedgerRecord[];
  reputations: Record<string, ReputationMetrics>;
  totalVolumeUsdc: string;
  fetchError: string | null;
  refreshData: () => Promise<void>;

  // Global search
  searchQuery: string;
  setSearchQuery: (q: string) => void;

  // Buyer console state
  taskPrompt: string;
  setTaskPrompt: (p: string) => void;
  budgetUsdc: string;
  setBudgetUsdc: (b: string) => void;
  isPlanning: boolean;
  isSubmitting: boolean;
  taskPlan: TaskPlanPreview | null;
  setTaskPlan: (p: TaskPlanPreview | null) => void;
  taskResult: TaskResponse | null;
  taskError: string | null;
  handlePreviewPlan: (prompt?: string, budget?: string) => void;
  handleExecuteConfirmedTask: () => Promise<void>;

  // Modal inspection state
  selectedService: ServiceDefinition | null;
  setSelectedService: (s: ServiceDefinition | null) => void;
  selectedLedgerRecord: LedgerRecord | null;
  setSelectedLedgerRecord: (r: LedgerRecord | null) => void;
  inspectLedgerRecord: (requestId: string) => Promise<void>;
  useServiceInTask: (service: ServiceDefinition) => void;
}

const MarketplaceContext = createContext<MarketplaceContextType | undefined>(undefined);

export const MarketplaceProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [services, setServices] = useState<ServiceDefinition[]>([]);
  const [ledger, setLedger] = useState<LedgerRecord[]>([]);
  const [reputations, setReputations] = useState<Record<string, ReputationMetrics>>({});
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Buyer task states
  const [taskPrompt, setTaskPrompt] = useState<string>('Collect market data on ETH and summarize key metrics');
  const [budgetUsdc, setBudgetUsdc] = useState<string>('0.05');
  const [isPlanning, setIsPlanning] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [taskPlan, setTaskPlan] = useState<TaskPlanPreview | null>(null);
  const [taskResult, setTaskResult] = useState<TaskResponse | null>(null);
  const [taskError, setTaskError] = useState<string | null>(null);

  // Modals
  const [selectedService, setSelectedService] = useState<ServiceDefinition | null>(null);
  const [selectedLedgerRecord, setSelectedLedgerRecord] = useState<LedgerRecord | null>(null);

  const loadData = async () => {
    setFetchError(null);
    try {
      const [, sData, lData, rData] = await Promise.all([
        fetchHealth().catch(() => ({ status: 'unreachable', version: 'unknown', network: 'eip155:84532' })),
        fetchServices().catch(() => ({ services: [], total: 0 })),
        fetchLedger().catch(() => ({ records: [], total: 0 })),
        fetchReputations().catch(() => ({}))
      ]);

      setServices(sData.services || []);
      setLedger(lData.records || []);
      setReputations(rData || {});
    } catch (err: any) {
      console.error('Failed to load marketplace data:', err);
      setFetchError(err.message || 'Error communicating with backend');
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(() => loadData(), 8000);
    return () => clearInterval(timer);
  }, []);

  const totalVolumeUsdc = useMemo(() => {
    return ledger
      .filter(r => r.status === 'paid' || r.status === 'paid output rejected')
      .reduce((sum, r) => sum + parseFloat(r.amount_paid || '0'), 0)
      .toFixed(4);
  }, [ledger]);

  const handlePreviewPlan = (overridePrompt?: string, overrideBudget?: string) => {
    const prompt = (overridePrompt || taskPrompt).trim();
    const budget = overrideBudget || budgetUsdc;
    if (!prompt) return;

    setTaskError(null);
    setIsPlanning(true);

    try {
      const promptLower = prompt.toLowerCase();
      const steps: PlannedStepEstimate[] = [];
      let stepCounter = 1;

      if (['market', 'price', 'eth', 'btc', 'financial', 'volume'].some(w => promptLower.includes(w))) {
        steps.push({
          step_number: stepCounter++,
          category: 'data',
          service_id: 'data_001',
          estimated_cost_usdc: '0.002',
          service_name: services.find(s => s.service_id === 'data_001')?.name || 'Alpha Financial Market Data'
        });
      }

      if (['scrape', 'web', 'article', 'url', 'extract'].some(w => promptLower.includes(w))) {
        steps.push({
          step_number: stepCounter++,
          category: 'scraping',
          service_id: 'scraping_001',
          estimated_cost_usdc: '0.003',
          service_name: services.find(s => s.service_id === 'scraping_001')?.name || 'Web Markdown & Content Extractor'
        });
      }

      if (['summarize', 'analyze', 'infer', 'synthesize', 'takeaway'].some(w => promptLower.includes(w)) || steps.length === 0) {
        steps.push({
          step_number: stepCounter++,
          category: 'inference',
          service_id: 'inference_001',
          estimated_cost_usdc: '0.004',
          service_name: services.find(s => s.service_id === 'inference_001')?.name || 'Agent Synthesis & Inference Engine'
        });
      }

      const totalEstimated = steps.reduce((acc, step) => acc + parseFloat(step.estimated_cost_usdc), 0);
      const budgetNum = parseFloat(budget) || 0;

      setTaskPlan({
        prompt,
        budget_usdc: budget,
        steps,
        estimated_total_usdc: totalEstimated.toFixed(6),
        is_affordable: budgetNum >= totalEstimated
      });
    } catch (err: any) {
      setTaskError('Failed to generate task plan: ' + err.message);
    } finally {
      setIsPlanning(false);
    }
  };

  const handleExecuteConfirmedTask = async () => {
    if (!taskPrompt.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setTaskError(null);
    setTaskResult(null);

    try {
      const result = await submitBuyerTask(taskPrompt, budgetUsdc);
      setTaskResult(result);
      setTaskPlan(null);
      await loadData();
    } catch (err: any) {
      setTaskError(err.message || 'Error executing task on server');
    } finally {
      setIsSubmitting(false);
    }
  };

  const inspectLedgerRecord = async (requestId: string) => {
    try {
      const rec = ledger.find(r => r.request_id === requestId);
      if (rec) {
        setSelectedLedgerRecord(rec);
      } else {
        const fetched = await fetchLedgerRecord(requestId);
        setSelectedLedgerRecord(fetched);
      }
    } catch (err) {
      console.error('Failed to inspect ledger record:', err);
    }
  };

  const useServiceInTask = (service: ServiceDefinition) => {
    setTaskPrompt(`Query ${service.name} (${service.service_id}) and extract actionable insights`);
  };

  return (
    <MarketplaceContext.Provider
      value={{
        services,
        ledger,
        reputations,
        totalVolumeUsdc,
        fetchError,
        refreshData: loadData,
        searchQuery,
        setSearchQuery,
        taskPrompt,
        setTaskPrompt,
        budgetUsdc,
        setBudgetUsdc,
        isPlanning,
        isSubmitting,
        taskPlan,
        setTaskPlan,
        taskResult,
        taskError,
        handlePreviewPlan,
        handleExecuteConfirmedTask,
        selectedService,
        setSelectedService,
        selectedLedgerRecord,
        setSelectedLedgerRecord,
        inspectLedgerRecord,
        useServiceInTask,
      }}
    >
      {children}
    </MarketplaceContext.Provider>
  );
};

export const useMarketplace = () => {
  const context = useContext(MarketplaceContext);
  if (!context) {
    throw new Error('useMarketplace must be used within a MarketplaceProvider');
  }
  return context;
};
