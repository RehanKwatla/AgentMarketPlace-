import React, { createContext, useContext, useState, useEffect, useMemo, ReactNode } from 'react';
import { 
  ServiceDefinition, 
  LedgerRecord, 
  ReputationMetrics, 
  TaskResponse, 
  TaskPlanPreview, 
  PlannedStepEstimate,
  HealthInfo,
  PaymentSubsystemStatus,
  TaskHistoryItem
} from '../types';
import { 
  fetchHealth, 
  fetchServices, 
  fetchLedger, 
  fetchReputations, 
  submitBuyerTask, 
  fetchLedgerRecord,
  fetchPaymentStatus,
  fetchPendingReconciliations,
  reconcilePaymentAttempt
} from '../api/client';

interface MarketplaceContextType {
  services: ServiceDefinition[];
  ledger: LedgerRecord[];
  reputations: Record<string, ReputationMetrics>;
  healthInfo: HealthInfo | null;
  paymentStatus: PaymentSubsystemStatus | null;
  pendingReconciliations: Record<string, any>;
  isReconciling: boolean;
  totalVolumeUsdc: string;
  fetchError: string | null;
  refreshData: () => Promise<void>;

  // Recent tasks history
  recentTasks: TaskHistoryItem[];

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
  handleExecuteConfirmedTask: (promptOverride?: string, budgetOverride?: string) => Promise<TaskResponse | null>;

  // Reconcile attempt
  handleReconcileAttempt: (attemptId: string) => Promise<any>;

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
  const [healthInfo, setHealthInfo] = useState<HealthInfo | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<PaymentSubsystemStatus | null>(null);
  const [pendingReconciliations, setPendingReconciliations] = useState<Record<string, any>>({});
  const [isReconciling, setIsReconciling] = useState<boolean>(false);
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

  // Persistent Recent Tasks
  const [recentTasks, setRecentTasks] = useState<TaskHistoryItem[]>(() => {
    try {
      const saved = localStorage.getItem('di06_recent_tasks');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });


  const loadData = async () => {
    setFetchError(null);
    try {
      const [hData, sData, lData, rData, pData, prData] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchServices().catch(() => ({ services: [], total: 0 })),
        fetchLedger().catch(() => ({ records: [], total: 0 })),
        fetchReputations().catch(() => ({})),
        fetchPaymentStatus().catch(() => null),
        fetchPendingReconciliations().catch(() => ({ pending_reconciliations: {}, total: 0 }))
      ]);

      setHealthInfo(hData);
      setServices(sData.services || []);
      setLedger(lData.records || []);
      setReputations(rData || {});
      setPaymentStatus(pData);
      setPendingReconciliations(prData.pending_reconciliations || {});
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

  const handleExecuteConfirmedTask = async (
    promptOverride?: string, 
    budgetOverride?: string
  ): Promise<TaskResponse | null> => {
    const prompt = (promptOverride || taskPrompt).trim();
    const budget = budgetOverride || budgetUsdc;
    if (!prompt || isSubmitting) return null;

    setIsSubmitting(true);
    setTaskError(null);
    setTaskResult(null);

    try {
      const result = await submitBuyerTask(prompt, budget);
      setTaskResult(result);
      setTaskPlan(null);

      const newTask: TaskHistoryItem = {
        task_id: result.task_id,
        prompt: prompt,
        status: result.status,
        timestamp: new Date().toISOString(),
        total_cost_usdc: result.total_cost_usdc,
        budget_usdc: result.budget_allocated_usdc,
        services_used: result.selected_services,
      };

      setRecentTasks(prev => {
        const updated = [newTask, ...prev.filter(t => t.task_id !== newTask.task_id)].slice(0, 15);
        try {
          localStorage.setItem('di06_recent_tasks', JSON.stringify(updated));
        } catch {}
        return updated;
      });

      await loadData();
      return result;
    } catch (err: any) {
      const msg = err.message || 'Error executing task on server';
      setTaskError(msg);
      throw err;
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

  const handleReconcileAttempt = async (attemptId: string) => {
    setIsReconciling(true);
    try {
      const outcome = await reconcilePaymentAttempt(attemptId);
      await loadData();
      return outcome;
    } catch (err: any) {
      console.error('Reconciliation failed:', err);
      throw err;
    } finally {
      setIsReconciling(false);
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
        healthInfo,
        paymentStatus,
        pendingReconciliations,
        isReconciling,
        totalVolumeUsdc,
        fetchError,
        refreshData: loadData,
        recentTasks,
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
        handleReconcileAttempt,
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
