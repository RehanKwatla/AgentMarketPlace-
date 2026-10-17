import { 
  ServiceDefinition, 
  TaskResponse, 
  LedgerRecord, 
  ReputationMetrics, 
  HealthInfo,
  TaskDetailResponse
} from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchHealth(): Promise<HealthInfo> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed with status ${res.status}`);
  return res.json();
}

export async function fetchServices(category?: string, maxPriceUsdc?: string): Promise<{ services: ServiceDefinition[]; total: number }> {
  const url = new URL(`${API_BASE_URL}/api/v1/services`);
  if (category && category !== 'all') url.searchParams.set('category', category);
  if (maxPriceUsdc) url.searchParams.set('max_price_usdc', maxPriceUsdc);
  url.searchParams.set('is_active', 'true');
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Failed to fetch services: ${res.statusText}`);
  return res.json();
}

export async function fetchServiceById(serviceId: string): Promise<ServiceDefinition> {
  const res = await fetch(`${API_BASE_URL}/api/v1/services/${serviceId}`);
  if (!res.ok) throw new Error(`Service ${serviceId} not found`);
  return res.json();
}

export interface SubmitBuyerTaskOptions {
  task: string;
  budget_usdc: string;
  max_concurrency?: number;
  preferred_categories?: string[];
  required_categories?: string[];
  execute_now?: boolean;
}

export async function submitBuyerTask(
  taskOrOptions: string | SubmitBuyerTaskOptions, 
  budgetUsdc?: string
): Promise<TaskResponse> {
  const payload = typeof taskOrOptions === 'string'
    ? { task: taskOrOptions, budget_usdc: budgetUsdc || '0.05' }
    : {
        task: taskOrOptions.task,
        budget_usdc: taskOrOptions.budget_usdc,
        max_concurrency: taskOrOptions.max_concurrency ?? 3,
        preferred_categories: taskOrOptions.preferred_categories,
        required_categories: taskOrOptions.required_categories,
        execute_now: taskOrOptions.execute_now ?? true,
      };

  const res = await fetch(`${API_BASE_URL}/api/v1/buyer/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    let errorMsg = 'Failed to execute buyer task';
    if (typeof errorBody.detail === 'string') {
      errorMsg = errorBody.detail;
    } else if (Array.isArray(errorBody.detail) && errorBody.detail.length > 0) {
      errorMsg = errorBody.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

export async function fetchLedger(statusFilter?: string, serviceIdFilter?: string, limit = 100, offset = 0): Promise<{ records: LedgerRecord[]; total: number }> {
  const url = new URL(`${API_BASE_URL}/api/v1/ledger`);
  if (statusFilter && statusFilter !== 'all') url.searchParams.set('status', statusFilter);
  if (serviceIdFilter && serviceIdFilter !== 'all') url.searchParams.set('service_id', serviceIdFilter);
  url.searchParams.set('limit', limit.toString());
  url.searchParams.set('offset', offset.toString());

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Failed to fetch ledger: ${res.statusText}`);
  return res.json();
}

export async function fetchLedgerRecord(requestId: string): Promise<LedgerRecord> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ledger/${requestId}`);
  if (!res.ok) throw new Error(`Ledger record ${requestId} not found`);
  return res.json();
}

export async function fetchReputations(): Promise<Record<string, ReputationMetrics>> {
  const res = await fetch(`${API_BASE_URL}/api/v1/reputation`);
  if (!res.ok) throw new Error(`Failed to fetch reputations: ${res.statusText}`);
  return res.json();
}

export async function fetchServiceReputation(serviceId: string): Promise<ReputationMetrics> {
  const res = await fetch(`${API_BASE_URL}/api/v1/reputation/${serviceId}`);
  if (!res.ok) throw new Error(`Failed to fetch reputation for ${serviceId}`);
  return res.json();
}

export async function fetchPaymentStatus(): Promise<{
  module: string;
  status: string;
  protocol_version: string;
  network: string;
  facilitator_configured: boolean;
  pending_reconciliations_count: number;
}> {
  const res = await fetch(`${API_BASE_URL}/api/v1/payments/status`);
  if (!res.ok) throw new Error(`Failed to fetch payment status: ${res.statusText}`);
  return res.json();
}

export async function fetchPendingReconciliations(): Promise<{
  pending_reconciliations: Record<string, any>;
  total: number;
}> {
  const res = await fetch(`${API_BASE_URL}/api/v1/payments/reconciliations`);
  if (!res.ok) throw new Error(`Failed to fetch pending reconciliations: ${res.statusText}`);
  return res.json();
}

export async function reconcilePaymentAttempt(attemptId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/payments/reconcile/${attemptId}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || `Reconciliation failed for ${attemptId}`);
  }
  return res.json();
}

export async function fetchTaskCalls(taskId: string): Promise<{ task_id: string; items: any[]; calls: any[] }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/calls`);
  if (!res.ok) throw new Error(`Failed to fetch calls for task ${taskId}`);
  return res.json();
}

export async function fetchTaskDetail(taskId: string): Promise<TaskDetailResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/buyer/tasks/${taskId}`);
  if (!res.ok) throw new Error(`Task ${taskId} not found or unreachable`);
  return res.json();
}

export async function fetchTaskResult(taskId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/result`);
  if (!res.ok) throw new Error(`Result for task ${taskId} not found`);
  return res.json();
}

export { API_BASE_URL };

