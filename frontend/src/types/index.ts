export type ServiceCategory = 'data' | 'scraping' | 'inference';

export type LedgerStatus = 
  | 'paid' 
  | 'paid output rejected' 
  | 'refused' 
  | 'failed and not charged'
  | 'simulated'
  | 'pending'
  | 'pending reconciliation'
  | 'verified on-chain'
  | 'verified facilitator receipt';

export interface ServiceDefinition {
  service_id: string;
  name: string;
  category: ServiceCategory;
  endpoint_url: string;
  price_usdc: string;
  price_base_units: number;
  network: string;
  pay_to: string;
  description: string;
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  is_active: boolean;
}

export interface ExecutionStep {
  step: number;
  service_id: string;
  request_id: string;
  price_paid_usdc: string;
  tx_hash: string | null;
  status: LedgerStatus;
  latency_ms: number;
  output?: Record<string, any>;
  error?: string;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  budget_allocated_usdc: string;
  total_cost_usdc: string;
  cost_explanation: string;
  selected_services: string[];
  executions: ExecutionStep[];
  final_result: string | null;
  errors_and_fallbacks: string[];
}

export interface LedgerRecord {
  request_id: string;
  timestamp: string;
  buyer_id: string;
  seller_id: string;
  service_id: string;
  listed_price: string;
  amount_paid: string;
  tx_hash: string | null;
  status: LedgerStatus;
  latency_ms: number;
  error_reason: string | null;
}

export interface ReputationMetrics {
  service_id: string;
  total_calls: number;
  successful_calls: number;
  success_rate: number;
  median_latency_ms: number;
  failure_counts: number;
  schema_invalid_counts: number;
  listed_price_usdc: string;
  reputation_score: number;
}

export interface HealthInfo {
  status: string;
  version: string;
  network: string;
  timestamp?: string;
  services?: Record<string, string>;
}

export interface PlannedStepEstimate {
  step_number: number;
  category: ServiceCategory;
  service_id: string;
  estimated_cost_usdc: string;
  service_name?: string;
}

export interface TaskPlanPreview {
  prompt: string;
  budget_usdc: string;
  steps: PlannedStepEstimate[];
  estimated_total_usdc: string;
  is_affordable: boolean;
  missing_services?: string[];
}

export const isValidBaseSepoliaTxHash = (hash: string | null | undefined): boolean => {
  if (!hash) return false;
  // Strict 66-character hex string starting with 0x (Base Sepolia transaction hash)
  // Synthetics like rec_auth_..., simulated_..., mock_... evaluate to false
  return /^0x[0-9a-fA-F]{64}$/.test(hash.trim());
};

export const getBaseSepoliaExplorerUrl = (hash: string | null | undefined): string | null => {
  if (!isValidBaseSepoliaTxHash(hash)) return null;
  return `https://sepolia.basescan.org/tx/${hash?.trim()}`;
};
