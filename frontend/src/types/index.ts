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

export interface ServiceReputation {
  service_id: string;
  reputation_score: number;
  success_rate: number;
  median_latency_ms: number;
  latency_p95_ms?: number;
  total_calls: number;
  successful_calls: number;
  paid_output_rejected_calls?: number;
  listed_price_usdc: string;
  last_call_at?: string;
}

export interface ServiceDefinition {
  service_id: string;
  name: string;
  category: ServiceCategory;
  endpoint_url: string;
  price_usdc: string;
  price_atomic?: number;
  price_base_units: number;
  network: string;
  asset_address?: string;
  pay_to: string;
  description: string;
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  is_active: boolean;
  enabled?: boolean;
  capabilities?: string[];
  reputation?: ServiceReputation;
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
  provenance?: Array<{
    step: number;
    service_id: string;
    request_id: string;
    tx_hash?: string;
    timestamp?: string;
  }>;
}

export interface TaskHistoryItem {
  task_id: string;
  prompt: string;
  status: string;
  timestamp: string;
  total_cost_usdc: string;
  budget_usdc: string;
  services_used: string[];
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
  task_id?: string | null;
  payment_id?: string | null;
  amount_paid_units?: number | null;
  listed_price_units?: number | null;
  network?: string | null;
  token?: string | null;
}

export interface ReputationMetrics {
  service_id: string;
  total_calls: number;
  successful_calls: number;
  success_rate: number;
  median_latency_ms: number;
  latency_p95_ms?: number;
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

export interface PaymentSubsystemStatus {
  module: string;
  status: string;
  protocol_version: string;
  network: string;
  facilitator_configured: boolean;
  pending_reconciliations_count: number;
}

export interface PendingReconciliationItem {
  attempt_id: string;
  task_id?: string;
  service_id?: string;
  amount_units?: number;
  amount_usdc?: string;
  status?: string;
  created_at?: string;
  reason?: string;
}

export interface PendingReconciliationsResponse {
  pending_reconciliations: Record<string, any>;
  total: number;
}

export interface ServiceCallRecord {
  call_id: string;
  service_id: string;
  category: ServiceCategory | string;
  step_id: number;
  depends_on?: number[];
  status: string;
  listed_price_usdc: string;
  amount_paid_usdc: string;
  latency_ms?: number;
  transaction_hash?: string | null;
  payment_reference?: string | null;
  schema_version?: string;
  output?: Record<string, any> | null;
  error?: string | null;
  validation_status?: 'accepted' | 'rejected' | 'pending' | string;
  validation_details?: {
    schema_type?: string;
    is_valid?: boolean;
    error?: string | null;
  };
  source_metadata?: {
    endpoint_url?: string;
    network?: string;
    seller_pay_to?: string;
    category?: string;
  };
  created_at?: string;
  completed_at?: string | null;
}

export interface TaskDetailResponse {
  task_id: string;
  status: string;
  task: string;
  budget_usdc: string;
  budget_atomic?: number;
  reserved_usdc?: string;
  spent_usdc?: string;
  spent_atomic?: number;
  actual_spent_atomic?: number;
  remaining_usdc?: string;
  remaining_atomic?: number;
  max_concurrency?: number;
  plan_summary?: Record<string, any> | null;
  calls: ServiceCallRecord[];
  result?: {
    summary?: string;
    market_data?: Record<string, any>;
    web_sources?: any[];
    rejected_outputs?: any[];
    failed_calls?: any[];
    provenance?: any[];
    [key: string]: any;
  } | null;
  final_result?: string | null;
  explanation?: {
    task_interpretation?: string;
    selected_services?: Array<{
      service_id: string;
      category: string;
      reason: string;
      listed_price_usdc: string;
      amount_paid_usdc: string;
      reputation_score?: number;
      median_latency_ms?: number;
      relevance?: number;
    }>;
    call_executions?: any[];
    outputs_accepted?: string[];
    outputs_rejected?: string[];
    fallback_attempts?: string[];
    spending_summary?: {
      budget_allocated_usdc: string;
      estimated_cost_usdc: string;
      verified_spent_usdc: string;
      reserved_budget_usdc?: string;
      uncertain_pending_usdc?: string;
      refunded_amount_usdc?: string;
      remaining_budget_usdc?: string;
    };
    verified_total_spend_usdc?: string;
    remaining_budget_usdc?: string;
    transaction_references?: string[];
    warnings?: string[];
    [key: string]: any;
  } | null;
  cost_explanation?: string | null;
  failure_reason?: string | null;
  created_at: string;
  completed_at?: string | null;
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

export interface WalletBalanceInfo {
  address: string;
  network: string;
  chain_id: number;
  token: string;
  token_address: string;
  balance_base_units: number;
  balance_usdc: string;
  native_balance_wei: string;
  native_balance_eth: string;
  is_verified_onchain: boolean;
  source: string;
  cached?: boolean;
}

export interface TxVerificationInfo {
  tx_hash: string;
  network: string;
  service_id: string;
  amount_usdc: string;
  amount_units: number;
  is_confirmed: boolean;
  status: string;
  evidence_type: string;
  explorer_url: string | null;
  settlement_proof: string | null;
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

