export type ServiceCategory = 'data' | 'scraping' | 'inference';

export type LedgerStatus = 
  | 'paid' 
  | 'paid output rejected' 
  | 'refused' 
  | 'failed and not charged';

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

export interface SettlementEvidenceSummary {
  confirmed_on_chain: number;
  local_authorization: number;
  unverified_hash: number;
  pending_reconciliation: number;
  failed_or_not_charged: number;
}

export interface PaymentDashboardData {
  network: string;
  token_address: string;
  total_tasks: number;
  total_paid_calls: number;
  total_spend_usdc: string;
  total_spend_base_units: number;
  status_breakdown: Record<string, number>;
  settlement_evidence: SettlementEvidenceSummary;
  services_count: number;
  pending_reconciliations_count: number;
  recent_transactions: Array<{
    request_id: string;
    task_id: string;
    service_id: string;
    status: string;
    amount_usdc: string;
    amount_base_units: number;
    tx_hash: string | null;
    settlement_proof: string | null;
    timestamp: string;
    latency_ms: number;
    evidence_type: string;
    evidence_label: string;
  }>;
}
