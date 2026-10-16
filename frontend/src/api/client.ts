import { ServiceDefinition, TaskResponse, LedgerRecord, ReputationMetrics, HealthInfo } from '../types';

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

export async function submitBuyerTask(task: string, budgetUsdc: string): Promise<TaskResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/buyer/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task, budget_usdc: budgetUsdc }),
  });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || 'Failed to execute buyer task');
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

export { API_BASE_URL };
