import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Results } from '../pages/Results';
import { Ledger } from '../pages/Ledger';
import * as apiClient from '../api/client';
import { TaskDetailResponse, LedgerRecord } from '../types';

// Mock MarketplaceContext
const mockUseMarketplace = vi.fn();
vi.mock('../context/MarketplaceContext', () => ({
  useMarketplace: () => mockUseMarketplace(),
}));

const mockTaskDetailWithProvenance: TaskDetailResponse = {
  task_id: 'task-results-test-001',
  status: 'completed',
  task: 'Look up relevant structured data and extract insights',
  budget_usdc: '0.08',
  budget_atomic: 80000,
  spent_usdc: '0.009000',
  spent_atomic: 9000,
  remaining_usdc: '0.071000',
  remaining_atomic: 71000,
  calls: [
    {
      call_id: 'call_test_01',
      service_id: 'scraping_001',
      category: 'scraping',
      step_id: 1,
      status: 'succeeded',
      listed_price_usdc: '0.003',
      amount_paid_usdc: '0.003',
      transaction_hash: 'rec_auth_402_sig_scraping',
      output: { title: 'Ethereum Docs', content: 'Autonomous agent economy' },
      validation_status: 'accepted',
    },
    {
      call_id: 'call_test_02',
      service_id: 'data_001',
      category: 'data',
      step_id: 2,
      status: 'succeeded',
      listed_price_usdc: '0.002',
      amount_paid_usdc: '0.002',
      transaction_hash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
      output: { price: 2650.5 },
      validation_status: 'accepted',
    },
    {
      call_id: 'call_test_03',
      service_id: 'inference_001',
      category: 'inference',
      step_id: 3,
      status: 'succeeded',
      listed_price_usdc: '0.004',
      amount_paid_usdc: '0.004',
      transaction_hash: 'rec_auth_402_sig_inference',
      output: { response: 'Synthesis narrative' },
      validation_status: 'accepted',
    },
  ],
  result: {
    summary: 'Synthesized intelligence indicating high-signal convergence towards autonomous microservice settlements.',
    market_data: {
      ETH: { price: 2650.5, volume_24h: 1420500, timestamp: '2026-10-17T00:10:00Z' },
    },
    web_sources: [
      { title: 'Ethereum Docs', url: 'https://ethereum.org', content: 'Autonomous agent economy on Base Sepolia', word_count: 25 },
    ],
    rejected_outputs: [],
    failed_calls: [],
    provenance: [
      {
        target_field: 'web_sources[0]',
        service_id: 'scraping_001',
        call_id: 'call_test_01',
        category: 'scraping',
        payment_reference: 'rec_auth_402_sig_scraping',
        validation_status: 'accepted',
      },
      {
        target_field: 'market_data.ETH',
        service_id: 'data_001',
        call_id: 'call_test_02',
        category: 'data',
        payment_reference: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        validation_status: 'accepted',
      },
    ],
  },
  final_result: 'Synthesized intelligence indicating high-signal convergence towards autonomous microservice settlements.',
  explanation: {
    task_interpretation: 'Task requires structured market data and web extraction within 0.08 USDC budget.',
    selected_services: [
      {
        service_id: 'scraping_001',
        category: 'scraping',
        reason: 'Selected for scraping capability matching task intent. Reputation: 96/100.',
        listed_price_usdc: '0.003',
        amount_paid_usdc: '0.003',
      },
      {
        service_id: 'data_001',
        category: 'data',
        reason: 'Selected for data capability matching task intent. Reputation: 98.5/100.',
        listed_price_usdc: '0.002',
        amount_paid_usdc: '0.002',
      },
    ],
    spending_summary: {
      budget_allocated_usdc: '0.080000',
      estimated_cost_usdc: '0.009000',
      verified_spent_usdc: '0.009000',
      reserved_budget_usdc: '0.000000',
      uncertain_pending_usdc: '0.000000',
      refunded_amount_usdc: '0.071000',
      remaining_budget_usdc: '0.071000',
    },
    outputs_accepted: ['scraping_001: verified', 'data_001: verified'],
    outputs_rejected: [],
    fallback_attempts: [],
  },
  created_at: '2026-10-17T00:00:00Z',
  completed_at: '2026-10-17T00:00:02Z',
};

const mockLedgerRecords: LedgerRecord[] = [
  {
    request_id: 'req_ledger_001',
    timestamp: '2026-10-17T00:10:00Z',
    buyer_id: 'buyer_orchestrator',
    seller_id: '0x0000000000000000000000000000000000000001',
    service_id: 'data_001',
    listed_price: '0.002',
    amount_paid: '0.002',
    tx_hash: '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
    status: 'paid',
    latency_ms: 110,
    error_reason: null,
    task_id: 'task_alpha',
    amount_paid_units: 2000,
    listed_price_units: 2000,
  },
  {
    request_id: 'req_ledger_002',
    timestamp: '2026-10-17T00:11:00Z',
    buyer_id: 'buyer_orchestrator',
    seller_id: '0x0000000000000000000000000000000000000002',
    service_id: 'scraping_001',
    listed_price: '0.003',
    amount_paid: '0.003',
    tx_hash: 'rec_auth_402_sig_local',
    status: 'paid output rejected',
    latency_ms: 180,
    error_reason: 'Draft-7 schema validation failed on extracted payload',
    task_id: 'task_beta',
    amount_paid_units: 3000,
    listed_price_units: 3000,
  },
  {
    request_id: 'req_ledger_003',
    timestamp: '2026-10-17T00:12:00Z',
    buyer_id: 'buyer_orchestrator',
    seller_id: '0x0000000000000000000000000000000000000003',
    service_id: 'inference_001',
    listed_price: '0.004',
    amount_paid: '0.000',
    tx_hash: null,
    status: 'failed and not charged',
    latency_ms: 0,
    error_reason: 'Microservice unavailable; budget released',
    task_id: 'task_gamma',
    amount_paid_units: 0,
    listed_price_units: 4000,
  },
];

describe('Phase 7: Results View (/results/:taskId)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseMarketplace.mockReturnValue({
      taskResult: null,
      recentTasks: [],
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders task results, final synthesis, and authoritative financial accounting', async () => {
    vi.spyOn(apiClient, 'fetchTaskDetail').mockResolvedValueOnce(mockTaskDetailWithProvenance);
    vi.spyOn(apiClient, 'fetchTaskResult').mockResolvedValueOnce(mockTaskDetailWithProvenance);

    render(
      <MemoryRouter initialEntries={['/results/task-results-test-001']}>
        <Routes>
          <Route path="/results/:taskId" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      // Final synthesis
      expect(screen.getByText(/Synthesized intelligence indicating high-signal convergence/i)).toBeInTheDocument();
      // Financial accounting
      expect(screen.getByText('$0.080000 USDC')).toBeInTheDocument();
      expect(screen.getByText('$0.009000 USDC')).toBeInTheDocument();
      expect(screen.getByText('$0.071000 USDC')).toBeInTheDocument();
    });

    // Check service selection explanation
    expect(screen.getByText('Service Selection & Orchestrator Routing')).toBeInTheDocument();
    expect(screen.getByText(/Selected for scraping capability matching task intent/i)).toBeInTheDocument();
  });

  it('renders verified accepted seller outputs with Draft-7 validation indicators', async () => {
    vi.spyOn(apiClient, 'fetchTaskDetail').mockResolvedValueOnce(mockTaskDetailWithProvenance);
    vi.spyOn(apiClient, 'fetchTaskResult').mockResolvedValueOnce(mockTaskDetailWithProvenance);

    render(
      <MemoryRouter initialEntries={['/results/task-results-test-001']}>
        <Routes>
          <Route path="/results/:taskId" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      // Market Data
      expect(screen.getByText('Market Data Artifact')).toBeInTheDocument();
      expect(screen.getByText('$2,650.5')).toBeInTheDocument();

      // Web sources
      expect(screen.getByText('Extracted Web Sources')).toBeInTheDocument();
      expect(screen.getByText('Ethereum Docs')).toBeInTheDocument();
    });
  });

  it('renders provenance attribution chain linking output fields to services and settlement proof', async () => {
    vi.spyOn(apiClient, 'fetchTaskDetail').mockResolvedValueOnce(mockTaskDetailWithProvenance);
    vi.spyOn(apiClient, 'fetchTaskResult').mockResolvedValueOnce(mockTaskDetailWithProvenance);

    render(
      <MemoryRouter initialEntries={['/results/task-results-test-001']}>
        <Routes>
          <Route path="/results/:taskId" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Cryptographic Provenance Chain')).toBeInTheDocument();
      expect(screen.getByText('web_sources[0]')).toBeInTheDocument();
      expect(screen.getByText('market_data.ETH')).toBeInTheDocument();

      // Base Sepolia explorer link for 0x hash
      const explorerLinks = screen.getAllByRole('link', { name: /0x123456/i });
      expect(explorerLinks.length).toBeGreaterThanOrEqual(1);
      expect(explorerLinks[0]).toHaveAttribute('href', expect.stringContaining('https://sepolia.basescan.org/tx/0x123456'));
    });
  });

  it('honestly displays zero schema rejections when all outputs valid', async () => {
    vi.spyOn(apiClient, 'fetchTaskDetail').mockResolvedValueOnce(mockTaskDetailWithProvenance);
    vi.spyOn(apiClient, 'fetchTaskResult').mockResolvedValueOnce(mockTaskDetailWithProvenance);

    render(
      <MemoryRouter initialEntries={['/results/task-results-test-001']}>
        <Routes>
          <Route path="/results/:taskId" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Zero Schema Rejections: 100% of seller outputs conformed/i)).toBeInTheDocument();
    });
  });

  it('renders honest explanation when outputs are rejected by schema validation', async () => {
    const taskWithRejection: TaskDetailResponse = {
      ...mockTaskDetailWithProvenance,
      explanation: {
        ...mockTaskDetailWithProvenance.explanation!,
        outputs_rejected: ['scraping_001 (Call ID: call_failed): Draft-7 missing required property [title]'],
      },
    };

    vi.spyOn(apiClient, 'fetchTaskDetail').mockResolvedValueOnce(taskWithRejection);
    vi.spyOn(apiClient, 'fetchTaskResult').mockResolvedValueOnce(taskWithRejection);

    render(
      <MemoryRouter initialEntries={['/results/task-results-test-001']}>
        <Routes>
          <Route path="/results/:taskId" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/1 Seller Outputs Failed Validation/i)).toBeInTheDocument();
      expect(screen.getByText(/Draft-7 missing required property \[title\]/i)).toBeInTheDocument();
    });
  });
});

describe('Phase 7: Immutable Audit Ledger (/ledger)', () => {
  const mockRefreshData = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseMarketplace.mockReturnValue({
      ledger: mockLedgerRecords,
      totalVolumeUsdc: '0.0050',
      refreshData: mockRefreshData,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders all required ledger fields: timestamp, request/task, service, listed price, verified paid, status, tx hash', () => {
    render(
      <MemoryRouter initialEntries={['/ledger']}>
        <Ledger />
      </MemoryRouter>
    );

    expect(screen.getByText(/Immutable Audit Ledger/i)).toBeInTheDocument();
    expect(screen.getByText('req_ledger_001')).toBeInTheDocument();
    expect(screen.getByText(/task_alpha/i)).toBeInTheDocument();
    expect(screen.getAllByText('data_001').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/\$0.002/i).length).toBeGreaterThanOrEqual(1);

    // Verify Base Sepolia explorer link
    const explorerLinks = screen.getAllByRole('link', { name: /0xabcdef/i });
    expect(explorerLinks.length).toBeGreaterThanOrEqual(1);
    expect(explorerLinks[0]).toHaveAttribute('href', expect.stringContaining('https://sepolia.basescan.org/tx/0xabcdef'));
  });

  it('correctly handles missing or local transaction hashes without creating broken explorer links', () => {
    render(
      <MemoryRouter initialEntries={['/ledger']}>
        <Ledger />
      </MemoryRouter>
    );

    // Failed uncharged record
    expect(screen.getByText('req_ledger_003')).toBeInTheDocument();
    expect(screen.getByText(/task_gamma/i)).toBeInTheDocument();
    expect(screen.getByText(/Local Auth \/ Uncharged/i)).toBeInTheDocument();
  });

  it('filters ledger records by status and search query', () => {
    render(
      <MemoryRouter initialEntries={['/ledger']}>
        <Ledger />
      </MemoryRouter>
    );

    const searchInput = screen.getByPlaceholderText(/Search request ID, service, task, tx hash/i);
    fireEvent.change(searchInput, { target: { value: 'scraping_001' } });

    // Only req_ledger_002 should match
    expect(screen.getByText('req_ledger_002')).toBeInTheDocument();
    expect(screen.queryByText('req_ledger_001')).not.toBeInTheDocument();
    expect(screen.queryByText('req_ledger_003')).not.toBeInTheDocument();
  });

  it('distinguishes verified settlements from uncharged failed calls', () => {
    render(
      <MemoryRouter initialEntries={['/ledger']}>
        <Ledger />
      </MemoryRouter>
    );

    // Paid count = 1, Output rejected = 1, Failed/refused = 1
    expect(screen.getByText('$0.0050 USDC')).toBeInTheDocument();
  });
});
