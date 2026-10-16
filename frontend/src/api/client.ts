import { ServiceDefinition, TaskResponse, LedgerRecord, ReputationMetrics } from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchServices(category?: string): Promise<{ services: ServiceDefinition[]; total: number }> {
  const url = new URL(`${API_BASE_URL}/api/v1/services`);
  if (category) url.searchParams.set('category', category);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Failed to fetch services');
  return res.json();
}

export async function submitBuyerTask(task: string, budgetUsdc: string): Promise<TaskResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/buyer/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task, budget_usdc: budgetUsdc }),
  });
  if (!res.ok) throw new Error('Failed to execute buyer task');
  return res.json();
}

export async function fetchLedger(): Promise<{ records: LedgerRecord[]; total: number }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ledger`);
  if (!res.ok) throw new Error('Failed to fetch ledger');
  return res.json();
}

export async function fetchReputations(): Promise<Record<string, ReputationMetrics>> {
  const res = await fetch(`${API_BASE_URL}/api/v1/reputation`);
  if (!res.ok) throw new Error('Failed to fetch reputations');
  return res.json();
}
