/**
 * Authoritative status mapping utility for DI-06 Pay-per-Call Agent Economy.
 * Maps actual backend states to human-readable labels and tracks terminal states.
 * Unknown states remain visible as unknown rather than incorrectly mapped to success.
 */

export type StatusVariant = 
  | 'success' 
  | 'running' 
  | 'warning' 
  | 'error' 
  | 'pending' 
  | 'neutral' 
  | 'unknown';

export interface StatusDisplayInfo {
  label: string;
  variant: StatusVariant;
  isTerminal: boolean;
  description: string;
}

/**
 * Maps task-level execution status returned by backend API.
 */
export function mapTaskStatus(rawStatus?: string | null): StatusDisplayInfo {
  if (!rawStatus) {
    return {
      label: 'Unknown',
      variant: 'unknown',
      isTerminal: false,
      description: 'Task state is currently unavailable',
    };
  }

  const s = rawStatus.toLowerCase().trim();

  switch (s) {
    case 'planning':
      return {
        label: 'Planning',
        variant: 'pending',
        isTerminal: false,
        description: 'Analyzing requirements and planning service dependency sequence',
      };
    case 'ready':
      return {
        label: 'Ready',
        variant: 'pending',
        isTerminal: false,
        description: 'Plan formulated, awaiting service execution',
      };
    case 'accepted':
      return {
        label: 'Accepted',
        variant: 'pending',
        isTerminal: false,
        description: 'Task received by orchestrator, starting dependency routing',
      };
    case 'running':
    case 'in_progress':
    case 'executing':
      return {
        label: 'Running',
        variant: 'running',
        isTerminal: false,
        description: 'Autonomous microservice calls currently executing',
      };
    case 'payment_required':
      return {
        label: 'Payment Required',
        variant: 'warning',
        isTerminal: false,
        description: 'Microservice issued an HTTP 402 payment challenge',
      };
    case 'payment_processing':
    case 'settling':
      return {
        label: 'Payment Processing',
        variant: 'running',
        isTerminal: false,
        description: 'Authorizing EIP-712 payment authorization for settlement',
      };
    case 'pending_reconciliation':
      return {
        label: 'Pending Reconciliation',
        variant: 'warning',
        isTerminal: false,
        description: 'Suspense queue reconciliation in progress',
      };
    case 'output_rejected':
    case 'paid output rejected':
      return {
        label: 'Output Rejected',
        variant: 'warning',
        isTerminal: true,
        description: 'Service was paid but output schema validation failed',
      };
    case 'completed':
    case 'success':
    case 'succeeded':
      return {
        label: 'Completed',
        variant: 'success',
        isTerminal: true,
        description: 'All steps verified and settled cryptographically',
      };
    case 'failed':
    case 'failed and not charged':
    case 'refused':
      return {
        label: 'Failed',
        variant: 'error',
        isTerminal: true,
        description: 'Task execution failed or was refused by orchestrator',
      };
    default:
      return {
        label: `Unknown (${rawStatus})`,
        variant: 'unknown',
        isTerminal: false,
        description: 'Unrecognized state returned by backend API',
      };
  }
}

/**
 * Maps step/call-level execution and validation status.
 */
export function mapCallStatus(
  rawStatus?: string | null, 
  validationStatus?: string | null
): StatusDisplayInfo {
  if (!rawStatus) {
    return {
      label: 'Unknown',
      variant: 'unknown',
      isTerminal: false,
      description: 'Call state unavailable',
    };
  }

  const s = rawStatus.toLowerCase().trim();
  const v = (validationStatus || '').toLowerCase().trim();

  // Handle output rejected state
  if (v === 'rejected' || s === 'output_rejected' || s === 'paid output rejected') {
    return {
      label: 'Output Rejected',
      variant: 'warning',
      isTerminal: true,
      description: 'Microservice response failed Draft-7 schema validation',
    };
  }

  switch (s) {
    case 'planning':
      return {
        label: 'Planning',
        variant: 'pending',
        isTerminal: false,
        description: 'Step scheduled in dependency plan',
      };
    case 'ready':
      return {
        label: 'Ready',
        variant: 'pending',
        isTerminal: false,
        description: 'Dependencies satisfied, ready to invoke',
      };
    case 'running':
    case 'in_progress':
      return {
        label: 'Running',
        variant: 'running',
        isTerminal: false,
        description: 'Calling remote microservice endpoint',
      };
    case 'payment_required':
      return {
        label: 'Payment Required',
        variant: 'warning',
        isTerminal: false,
        description: 'HTTP 402 payment challenge issued',
      };
    case 'payment_processing':
      return {
        label: 'Payment Processing',
        variant: 'running',
        isTerminal: false,
        description: 'Generating and dispatching EIP-712 authorization',
      };
    case 'succeeded':
    case 'completed':
    case 'paid':
      return {
        label: 'Completed',
        variant: 'success',
        isTerminal: true,
        description: 'Output verified and payment committed',
      };
    case 'failed':
    case 'failed and not charged':
    case 'refused':
      return {
        label: 'Failed',
        variant: 'error',
        isTerminal: true,
        description: 'Microservice call failed and was not charged',
      };
    default:
      return {
        label: `Unknown (${rawStatus})`,
        variant: 'unknown',
        isTerminal: false,
        description: 'Unrecognized call status from backend',
      };
  }
}

/**
 * Maps payment lifecycle and settlement states supported by backend contracts.
 */
export function mapPaymentStatus(rawStatus?: string | null): StatusDisplayInfo {
  if (!rawStatus) {
    return {
      label: 'Unknown',
      variant: 'unknown',
      isTerminal: false,
      description: 'Payment state is currently unavailable',
    };
  }

  const s = rawStatus.toLowerCase().trim();

  switch (s) {
    case 'payment_required':
    case 'payment required':
      return {
        label: 'Payment Required',
        variant: 'warning',
        isTerminal: false,
        description: 'HTTP 402 challenge issued with cryptographic payment requirements',
      };
    case 'awaiting_authorization':
    case 'awaiting authorization':
      return {
        label: 'Awaiting Authorization',
        variant: 'pending',
        isTerminal: false,
        description: 'Generating EIP-712 micropayment authorization payload',
      };
    case 'processing':
    case 'payment_processing':
    case 'settling':
      return {
        label: 'Processing',
        variant: 'running',
        isTerminal: false,
        description: 'Submitting payment authorization to settlement facilitator bridge',
      };
    case 'paid':
    case 'settled':
    case 'settled and verified':
    case 'settled & verified':
      return {
        label: 'Settled & Verified',
        variant: 'success',
        isTerminal: true,
        description: 'Micropayment settled and cryptographically verified on-chain',
      };
    case 'paid output rejected':
    case 'output_rejected':
    case 'paid, but output rejected':
      return {
        label: 'Paid, but Output Rejected',
        variant: 'warning',
        isTerminal: true,
        description: 'Payment settled, but microservice response failed Draft-7 schema validation',
      };
    case 'pending reconciliation':
    case 'pending_reconciliation':
      return {
        label: 'Pending Reconciliation',
        variant: 'warning',
        isTerminal: false,
        description: 'Payment outcome uncertain; held in suspense pending on-chain reconciliation',
      };
    case 'refused':
      return {
        label: 'Refused (Uncharged)',
        variant: 'error',
        isTerminal: true,
        description: 'Task execution refused prior to payment; zero funds deducted',
      };
    case 'failed':
    case 'failed and not charged':
      return {
        label: 'Failed (Uncharged)',
        variant: 'error',
        isTerminal: true,
        description: 'Service call failed during execution; payment not claimed and budget released',
      };
    default:
      return {
        label: `Unknown (${rawStatus})`,
        variant: 'unknown',
        isTerminal: false,
        description: 'Unrecognized payment state returned by backend API',
      };
  }
}

