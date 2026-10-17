import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AgentExecution } from '../pages/AgentExecution';
import { mapTaskStatus, mapCallStatus } from '../utils/statusMapping';
import * as apiClient from '../api/client';
import { TaskDetailResponse } from '../types';

// Mock MarketplaceContext
const mockUseMarketplace = vi.fn();
vi.mock('../context/MarketplaceContext', () => ({
  useMarketplace: () => mockUseMarketplace(),
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockTaskDetail: TaskDetailResponse = {
  task_id: 'test-task-123456',
  status: 'completed',
  task: 'Look up relevant structured data and extract details',
  budget_usdc: '0.08',
  budget_atomic: 80000,
  spent_usdc: '0.009000',
  spent_atomic: 9000,
  remaining_usdc: '0.071000',
  remaining_atomic: 71000,
  calls: [
    {
      call_id: 'call_step1_scraping',
      service_id: 'scraping_001',
      category: 'scraping',
      step_id: 1,
      depends_on: [],
      status: 'succeeded',
      listed_price_usdc: '0.003',
      amount_paid_usdc: '0.003',
      latency_ms: 150,
      transaction_hash: 'tx_hash_step_1',
      payment_reference: 'ref_step_1',
      output: { content: 'extracted text' },
      validation_status: 'accepted',
      source_metadata: {
        endpoint_url: 'http://localhost:8000/api/v1/seller/scraping',
        seller_pay_to: '0x0000000000000000000000000000000000000002',
        network: 'eip155:84532',
      },
    },
    {
      call_id: 'call_step2_data',
      service_id: 'data_001',
      category: 'data',
      step_id: 2,
      depends_on: [],
      status: 'succeeded',
      listed_price_usdc: '0.002',
      amount_paid_usdc: '0.002',
      latency_ms: 110,
      transaction_hash: 'tx_hash_step_2',
      payment_reference: 'ref_step_2',
      output: { price: 2650.5 },
      validation_status: 'accepted',
      source_metadata: {
        endpoint_url: 'http://localhost:8000/api/v1/seller/data',
        seller_pay_to: '0x0000000000000000000000000000000000000001',
        network: 'eip155:84532',
      },
    },
    {
      call_id: 'call_step3_inference',
      service_id: 'inference_001',
      category: 'inference',
      step_id: 3,
      depends_on: [1, 2],
      status: 'succeeded',
      listed_price_usdc: '0.004',
      amount_paid_usdc: '0.004',
      latency_ms: 220,
      transaction_hash: 'tx_hash_step_3',
      payment_reference: 'ref_step_3',
      output: { response: 'synthesis result' },
      validation_status: 'accepted',
      source_metadata: {
        endpoint_url: 'http://localhost:8000/api/v1/seller/inference',
        seller_pay_to: '0x0000000000000000000000000000000000000003',
        network: 'eip155:84532',
      },
    },
  ],
  result: {
    summary: 'Synthesis completed successfully',
  },
  final_result: 'Final synthesized insights',
  created_at: '2026-10-17T00:00:00Z',
  completed_at: '2026-10-17T00:00:02Z',
};

describe('Status Mapping Utilities', () => {
  it('maps known backend task states to human-readable labels', () => {
    expect(mapTaskStatus('planning').label).toBe('Planning');
    expect(mapTaskStatus('ready').label).toBe('Ready');
    expect(mapTaskStatus('running').label).toBe('Running');
    expect(mapTaskStatus('payment_required').label).toBe('Payment Required');
    expect(mapTaskStatus('payment_processing').label).toBe('Payment Processing');
    expect(mapTaskStatus('completed').label).toBe('Completed');
    expect(mapTaskStatus('failed').label).toBe('Failed');
    expect(mapTaskStatus('output_rejected').label).toBe('Output Rejected');
    expect(mapTaskStatus('pending_reconciliation').label).toBe('Pending Reconciliation');
  });

  it('preserves unknown states as unknown rather than mapping to success', () => {
    const unknownStatus = mapTaskStatus('custom_unsupported_state');
    expect(unknownStatus.label).toContain('Unknown (custom_unsupported_state)');
    expect(unknownStatus.variant).toBe('unknown');
    expect(unknownStatus.isTerminal).toBe(false);
  });

  it('correctly classifies terminal states vs active running states', () => {
    expect(mapTaskStatus('completed').isTerminal).toBe(true);
    expect(mapTaskStatus('failed').isTerminal).toBe(true);
    expect(mapTaskStatus('output_rejected').isTerminal).toBe(true);

    expect(mapTaskStatus('running').isTerminal).toBe(false);
    expect(mapTaskStatus('planning').isTerminal).toBe(false);
    expect(mapTaskStatus('payment_processing').isTerminal).toBe(false);
  });

  it('maps step/call level states with Draft-7 validation support', () => {
    expect(mapCallStatus('succeeded', 'accepted').label).toBe('Completed');
    expect(mapCallStatus('paid', 'rejected').label).toBe('Output Rejected');
    expect(mapCallStatus('payment_required').label).toBe('Payment Required');
  });
});

describe('AgentExecution Console Component', () => {
  const mockSetSelectedLedgerRecord = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseMarketplace.mockReturnValue({
      taskResult: null,
      setSelectedLedgerRecord: mockSetSelectedLedgerRecord,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads and renders task details from real taskId parameter', async () => {
    vi.spyOn(apiClient, 'fetchTaskDetail').mockResolvedValueOnce(mockTaskDetail);

    render(
      <MemoryRouter initialEntries={['/execution/test-task-123456']}>
        <Routes>
          <Route path="/execution/:taskId" element={<AgentExecution />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('test-task-123456')).toBeInTheDocument();
      expect(screen.getByText(/Look up relevant structured data/i)).toBeInTheDocument();
      expect(screen.getByText('$0.08 USDC')).toBeInTheDocument();
      expect(screen.getByText('$0.009000 USDC')).toBeInTheDocument();
      expect(screen.getByText('$0.071000 USDC')).toBeInTheDocument();
    });

    // Check dependency sequence rendered
    expect(screen.getByText(/Autonomous Dependency Sequence/i)).toBeInTheDocument();
    expect(screen.getAllByText('scraping_001').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('data_001').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('inference_001').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Depends on Step 1, 2/i)).toBeInTheDocument();
  });

  it('renders View Results action and navigates to /results/:taskId when results exist', async () => {
    vi.spyOn(apiClient, 'fetchTaskDetail').mockResolvedValueOnce(mockTaskDetail);

    render(
      <MemoryRouter initialEntries={['/execution/test-task-123456']}>
        <Routes>
          <Route path="/execution/:taskId" element={<AgentExecution />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const resultsBtn = screen.getByRole('button', { name: /Proceed to Synthesis Results/i });
      expect(resultsBtn).toBeInTheDocument();
      fireEvent.click(resultsBtn);
      expect(mockNavigate).toHaveBeenCalledWith('/results/test-task-123456');
    });
  });

  it('displays API error states when task fetch fails', async () => {
    vi.spyOn(apiClient, 'fetchTaskDetail').mockRejectedValueOnce(
      new Error('Task test-task-123456 not found on server')
    );

    render(
      <MemoryRouter initialEntries={['/execution/test-task-123456']}>
        <Routes>
          <Route path="/execution/:taskId" element={<AgentExecution />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to Retrieve Task/i)).toBeInTheDocument();
      expect(screen.getByText(/Task test-task-123456 not found on server/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    });
  });

  it('stops polling when task reaches a terminal state', async () => {
    const fetchSpy = vi.spyOn(apiClient, 'fetchTaskDetail').mockResolvedValue(mockTaskDetail);

    render(
      <MemoryRouter initialEntries={['/execution/test-task-123456']}>
        <Routes>
          <Route path="/execution/:taskId" element={<AgentExecution />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('test-task-123456');
    });

    // Initial load occurs
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });
});
