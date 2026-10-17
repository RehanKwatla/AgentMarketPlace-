import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PaymentProcessing } from '../pages/PaymentProcessing';
import { mapPaymentStatus } from '../utils/statusMapping';
import { LedgerRecord } from '../types';

// Mock MarketplaceContext
const mockUseMarketplace = vi.fn();
vi.mock('../context/MarketplaceContext', () => ({
  useMarketplace: () => mockUseMarketplace(),
}));

const mockLedger: LedgerRecord[] = [
  {
    request_id: 'req_settled_001',
    timestamp: '2026-10-17T00:10:00Z',
    buyer_id: 'buyer_orchestrator',
    seller_id: '0x0000000000000000000000000000000000000001',
    service_id: 'data_001',
    listed_price: '0.002',
    amount_paid: '0.002',
    tx_hash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
    status: 'paid',
    latency_ms: 120,
    error_reason: null,
    amount_paid_units: 2000,
    listed_price_units: 2000,
  },
  {
    request_id: 'req_rejected_002',
    timestamp: '2026-10-17T00:11:00Z',
    buyer_id: 'buyer_orchestrator',
    seller_id: '0x0000000000000000000000000000000000000002',
    service_id: 'scraping_001',
    listed_price: '0.003',
    amount_paid: '0.003',
    tx_hash: 'rec_auth_402_sig_local_proof',
    status: 'paid output rejected',
    latency_ms: 210,
    error_reason: 'Draft-7 schema validation failed: missing field [title]',
    amount_paid_units: 3000,
    listed_price_units: 3000,
  },
  {
    request_id: 'req_failed_003',
    timestamp: '2026-10-17T00:12:00Z',
    buyer_id: 'buyer_orchestrator',
    seller_id: '0x0000000000000000000000000000000000000003',
    service_id: 'inference_001',
    listed_price: '0.004',
    amount_paid: '0.000',
    tx_hash: null,
    status: 'failed and not charged',
    latency_ms: 0,
    error_reason: 'Remote microservice returned HTTP 503 Service Unavailable',
    amount_paid_units: 0,
    listed_price_units: 4000,
  },
  {
    request_id: 'req_refused_004',
    timestamp: '2026-10-17T00:13:00Z',
    buyer_id: 'buyer_orchestrator',
    seller_id: '0x0000000000000000000000000000000000000001',
    service_id: 'data_001',
    listed_price: '0.002',
    amount_paid: '0.000',
    tx_hash: null,
    status: 'refused',
    latency_ms: 0,
    error_reason: 'Task budget constraint prevented invocation',
    amount_paid_units: 0,
    listed_price_units: 2000,
  },
];

const mockPendingReconciliations = {
  req_suspense_001: {
    task_id: 'task_006',
    call_id: 'call_006',
    service_id: 'test_service_001',
    request_id: 'req_suspense_001',
    status: 'pending reconciliation',
    amount_base_units: 0,
    amount_usdc: '0.000000',
    seller_recipient: '0x0000000000000000000000000000000000000001',
    tx_hash: null,
    error_message: "Payment operation timed out. Outcome uncertain; marked pending reconciliation.",
  },
};

const mockPaymentStatus = {
  module: 'payments',
  status: 'operational',
  protocol_version: '2.0',
  network: 'eip155:84532',
  facilitator_configured: true,
  pending_reconciliations_count: 1,
};

describe('Payment Status Mapping Utility', () => {
  it('maps authoritative payment states to human-readable labels', () => {
    expect(mapPaymentStatus('paid').label).toBe('Settled & Verified');
    expect(mapPaymentStatus('settled and verified').label).toBe('Settled & Verified');
    expect(mapPaymentStatus('paid output rejected').label).toBe('Paid, but Output Rejected');
    expect(mapPaymentStatus('pending_reconciliation').label).toBe('Pending Reconciliation');
    expect(mapPaymentStatus('pending reconciliation').label).toBe('Pending Reconciliation');
    expect(mapPaymentStatus('payment_required').label).toBe('Payment Required');
    expect(mapPaymentStatus('payment required').label).toBe('Payment Required');
    expect(mapPaymentStatus('awaiting_authorization').label).toBe('Awaiting Authorization');
    expect(mapPaymentStatus('processing').label).toBe('Processing');
    expect(mapPaymentStatus('failed and not charged').label).toBe('Failed (Uncharged)');
    expect(mapPaymentStatus('refused').label).toBe('Refused (Uncharged)');
  });

  it('preserves unknown payment states visibly as unknown rather than assuming success', () => {
    const unknown = mapPaymentStatus('mysterious_arbitrary_state');
    expect(unknown.label).toBe('Unknown (mysterious_arbitrary_state)');
    expect(unknown.variant).toBe('unknown');
    expect(unknown.isTerminal).toBe(false);
  });

  it('correctly tracks terminal states for payment lifecycle', () => {
    expect(mapPaymentStatus('paid').isTerminal).toBe(true);
    expect(mapPaymentStatus('paid output rejected').isTerminal).toBe(true);
    expect(mapPaymentStatus('failed and not charged').isTerminal).toBe(true);
    expect(mapPaymentStatus('refused').isTerminal).toBe(true);

    expect(mapPaymentStatus('payment_required').isTerminal).toBe(false);
    expect(mapPaymentStatus('awaiting_authorization').isTerminal).toBe(false);
    expect(mapPaymentStatus('processing').isTerminal).toBe(false);
    expect(mapPaymentStatus('pending_reconciliation').isTerminal).toBe(false);
  });
});

describe('PaymentProcessing Component', () => {
  const mockHandleReconcileAttempt = vi.fn();
  const mockRefreshData = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseMarketplace.mockReturnValue({
      ledger: mockLedger,
      totalVolumeUsdc: '0.0050',
      paymentStatus: mockPaymentStatus,
      pendingReconciliations: mockPendingReconciliations,
      handleReconcileAttempt: mockHandleReconcileAttempt,
      refreshData: mockRefreshData,
      fetchError: null,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders operational payment engine status and financial metrics', () => {
    render(
      <MemoryRouter initialEntries={['/payments']}>
        <PaymentProcessing />
      </MemoryRouter>
    );

    expect(screen.getByText(/x402 Payment Processing & Settlement/i)).toBeInTheDocument();
    expect(screen.getByText('OPERATIONAL')).toBeInTheDocument();
    expect(screen.getByText('Active & Ready')).toBeInTheDocument();
    expect(screen.getAllByText('$0.0050 USDC').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/1 held in suspense/i)).toBeInTheDocument();
  });

  it('renders verified settlements and clearly distinguishes listed price from amount paid', () => {
    render(
      <MemoryRouter initialEntries={['/payments']}>
        <PaymentProcessing />
      </MemoryRouter>
    );

    // Settled record
    expect(screen.getByText('req_settled_001')).toBeInTheDocument();
    expect(screen.getAllByText('$0.002 USDC').length).toBeGreaterThanOrEqual(1);

    // Verify Base Sepolia explorer link exists for real 0x transaction hash
    const explorerLinks = screen.getAllByRole('link', { name: /0x123456/i });
    expect(explorerLinks.length).toBeGreaterThanOrEqual(1);
    expect(explorerLinks[0]).toHaveAttribute(
      'href',
      expect.stringContaining('https://sepolia.basescan.org/tx/0x1234567890abcdef')
    );
  });

  it('renders missing transaction hashes safely without broken links', () => {
    render(
      <MemoryRouter initialEntries={['/payments']}>
        <PaymentProcessing />
      </MemoryRouter>
    );

    // Failed uncharged record with tx_hash === null
    expect(screen.getByText('req_failed_003')).toBeInTheDocument();
    expect(screen.getAllByText(/Uncharged \/ Local/i).length).toBeGreaterThanOrEqual(1);
  });

  it('renders suspense queue and allows triggering authoritative reconciliation', async () => {
    mockHandleReconcileAttempt.mockResolvedValueOnce({
      outcome: 'SETTLED',
      status: 'paid',
    });

    render(
      <MemoryRouter initialEntries={['/payments']}>
        <PaymentProcessing />
      </MemoryRouter>
    );

    expect(screen.getByText('req_suspense_001')).toBeInTheDocument();
    expect(screen.getByText(/Payment operation timed out/i)).toBeInTheDocument();

    const reconcileBtn = screen.getByRole('button', { name: /Authoritative Reconcile/i });
    expect(reconcileBtn).toBeInTheDocument();

    fireEvent.click(reconcileBtn);

    await waitFor(() => {
      expect(mockHandleReconcileAttempt).toHaveBeenCalledWith('req_suspense_001');
      expect(screen.getByText(/Attempt req_suspense_001 reconciled successfully: SETTLED/i)).toBeInTheDocument();
    });
  });

  it('filters payments when tab is clicked', () => {
    render(
      <MemoryRouter initialEntries={['/payments']}>
        <PaymentProcessing />
      </MemoryRouter>
    );

    // Click Output Rejected tab
    const rejectedTab = screen.getByRole('button', { name: /Output Rejected \(1\)/i });
    fireEvent.click(rejectedTab);

    // Only req_rejected_002 should remain visible
    expect(screen.getByText('req_rejected_002')).toBeInTheDocument();
    expect(screen.queryByText('req_settled_001')).not.toBeInTheDocument();
    expect(screen.queryByText('req_failed_003')).not.toBeInTheDocument();
  });

  it('opens x402 details modal when Inspect x402 button is clicked', async () => {
    render(
      <MemoryRouter initialEntries={['/payments']}>
        <PaymentProcessing />
      </MemoryRouter>
    );

    const inspectButtons = screen.getAllByRole('button', { name: /Inspect x402/i });
    expect(inspectButtons.length).toBeGreaterThanOrEqual(1);

    fireEvent.click(inspectButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('x402 Payment Lifecycle Detail')).toBeInTheDocument();
      expect(screen.getByText('HTTP 402 Challenge')).toBeInTheDocument();
      expect(screen.getByText('EIP-712 Specification')).toBeInTheDocument();
    });
  });

  it('renders backend API error notification when fetch fails', () => {
    mockUseMarketplace.mockReturnValue({
      ledger: [],
      totalVolumeUsdc: '0.0000',
      paymentStatus: null,
      pendingReconciliations: {},
      handleReconcileAttempt: mockHandleReconcileAttempt,
      refreshData: mockRefreshData,
      fetchError: 'Failed to connect to payment engine at localhost:8000',
    });

    render(
      <MemoryRouter initialEntries={['/payments']}>
        <PaymentProcessing />
      </MemoryRouter>
    );

    expect(screen.getByText(/Failed to connect to payment engine/i)).toBeInTheDocument();
  });
});
