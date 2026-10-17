import { ServiceDefinition, TaskResponse, LedgerRecord, ReputationMetrics, PaymentDashboardData } from '../types';


/**
 * Resolves the backend API base URL with production safety enforcement.
 *
 * Rules:
 * 1. If VITE_API_BASE_URL is configured, trim trailing slashes and return it.
 * 2. In production builds (import.meta.env.PROD === true or MODE === 'production'):
 *    Reject missing configuration explicitly. Never silently route production calls to localhost.
 * 3. In local development / test environments:
 *    Safely fall back to http://localhost:8000 for seamless local development.
 */
export function getApiBaseUrl(): string {
  const env = (import.meta as any).env || {};
  const rawUrl = env.VITE_API_BASE_URL;
  const isProd = env.PROD === true || env.MODE === 'production';

  if (rawUrl && typeof rawUrl === 'string' && rawUrl.trim().length > 0) {
    return rawUrl.trim().replace(/\/+$/, '');
  }

  if (isProd) {
    throw new Error(
      'Deployment Configuration Error: VITE_API_BASE_URL is not set in this production build. ' +
      'Please configure VITE_API_BASE_URL to point to your deployed Render API (e.g. https://<app>.onrender.com) ' +
      'in your Vercel Project Settings -> Environment Variables.'
    );
  }

  return 'http://localhost:8000';
}

export async function fetchHealth() {
  const res = await fetch(`${getApiBaseUrl()}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}


export async function fetchServices(category?: string): Promise<{ services: ServiceDefinition[]; total: number }> {
  const url = new URL(`${getApiBaseUrl()}/api/v1/services`);
  if (category) url.searchParams.set('category', category);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Failed to fetch services');
  return res.json();
}

export async function submitBuyerTask(task: string, budgetUsdc: string): Promise<TaskResponse> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/buyer/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task, budget_usdc: budgetUsdc }),
  });
  if (!res.ok) throw new Error('Failed to execute buyer task');
  return res.json();
}

export async function fetchLedger(): Promise<{ records: LedgerRecord[]; total: number }> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/ledger`);
  if (!res.ok) throw new Error('Failed to fetch ledger');
  return res.json();
}

export async function fetchReputations(): Promise<Record<string, ReputationMetrics>> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/reputation`);
  if (!res.ok) throw new Error('Failed to fetch reputations');
  return res.json();
}

export async function fetchPaymentDashboard(): Promise<PaymentDashboardData> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/payments/dashboard`);
  if (!res.ok) throw new Error('Failed to fetch payment dashboard metrics');
  return res.json();
}

export async function submitMultiHopTask(steps: Array<{ service_id: string; input_data?: Record<string, any>; max_cost_usdc?: string }>, maxTotalBudgetUsdc?: string): Promise<any> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/payments/multi-hop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ steps, max_total_budget_usdc: maxTotalBudgetUsdc || '1.000000' }),
  });
  if (!res.ok) throw new Error('Failed to execute multi-hop route');
  return res.json();
}

export async function fetchPendingReconciliations(): Promise<Record<string, any>> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/payments/reconciliations`);
  if (!res.ok) throw new Error('Failed to fetch pending reconciliations');
  return res.json();
}

export async function triggerReconciliation(lookbackMinutes?: number): Promise<any> {
  const url = new URL(`${getApiBaseUrl()}/api/v1/payments/reconcile`);
  if (lookbackMinutes) url.searchParams.set('lookback_minutes', String(lookbackMinutes));
  const res = await fetch(url.toString(), { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger reconciliation');
  return res.json();
}

export async function syncLedger(): Promise<any> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/ledger/sync`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to synchronize ledger records');
  return res.json();
}
