import { describe, it, expect, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BuyerAgent } from '../pages/BuyerAgent';
import { toAtomicUnits, fromAtomicUnits, validateBudget, validateTaskPrompt } from '../utils/monetary';
import { ServiceDefinition, TaskResponse } from '../types';

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

const mockServices: ServiceDefinition[] = [
  {
    service_id: 'data_001',
    name: 'Alpha Financial Market Data',
    category: 'data',
    endpoint_url: 'http://localhost:8000/api/v1/seller/data',
    price_usdc: '0.002',
    price_atomic: 2000,
    price_base_units: 2000,
    network: 'eip155:84532',
    pay_to: '0x0000000000000000000000000000000000000001',
    description: 'Crypto market rates',
    input_schema: {},
    output_schema: {},
    is_active: true,
  },
  {
    service_id: 'scraping_001',
    name: 'Web Markdown Extractor',
    category: 'scraping',
    endpoint_url: 'http://localhost:8000/api/v1/seller/scraping',
    price_usdc: '0.003',
    price_atomic: 3000,
    price_base_units: 3000,
    network: 'eip155:84532',
    pay_to: '0x0000000000000000000000000000000000000002',
    description: 'Clean markdown extractor',
    input_schema: {},
    output_schema: {},
    is_active: true,
  },
];

describe('Buyer Console (Phase 4)', () => {
  let promptState = 'Look up relevant structured data and summarize findings';
  let budgetState = '0.08';
  const mockSetTaskPrompt = vi.fn((p) => { promptState = p; });
  const mockSetBudgetUsdc = vi.fn((b) => { budgetState = b; });
  const mockHandleExecuteConfirmedTask = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    promptState = 'Look up relevant structured data and summarize findings';
    budgetState = '0.08';

    mockUseMarketplace.mockReturnValue({
      taskPrompt: promptState,
      setTaskPrompt: mockSetTaskPrompt,
      budgetUsdc: budgetState,
      setBudgetUsdc: mockSetBudgetUsdc,
      isSubmitting: false,
      taskError: null,
      services: mockServices,
      selectedService: null,
      handleExecuteConfirmedTask: mockHandleExecuteConfirmedTask,
    });
  });

  it('renders task composer with natural-language prompt, budget input, and atomic calculation', () => {
    render(
      <MemoryRouter>
        <BuyerAgent />
      </MemoryRouter>
    );

    expect(screen.getByText('Buyer Console')).toBeInTheDocument();
    expect(screen.getByLabelText(/Natural-Language Objective Prompt/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Maximum Budget Cap/i)).toBeInTheDocument();
    expect(screen.getByText(/Atomic: 80,000 base units/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Task/i })).toBeInTheDocument();
  });

  it('validates empty task prompt and prevents submission', async () => {
    mockUseMarketplace.mockReturnValue({
      taskPrompt: '  ',
      setTaskPrompt: mockSetTaskPrompt,
      budgetUsdc: '0.05',
      setBudgetUsdc: mockSetBudgetUsdc,
      isSubmitting: false,
      taskError: null,
      services: mockServices,
      selectedService: null,
      handleExecuteConfirmedTask: mockHandleExecuteConfirmedTask,
    });

    render(
      <MemoryRouter>
        <BuyerAgent />
      </MemoryRouter>
    );

    const submitBtn = screen.getByRole('button', { name: /Run Task/i });
    fireEvent.click(submitBtn);

    expect(mockHandleExecuteConfirmedTask).not.toHaveBeenCalled();
  });

  it('validates budget > 0 against backend requirements', async () => {
    mockUseMarketplace.mockReturnValue({
      taskPrompt: 'Valid task description',
      setTaskPrompt: mockSetTaskPrompt,
      budgetUsdc: '0',
      setBudgetUsdc: mockSetBudgetUsdc,
      isSubmitting: false,
      taskError: null,
      services: mockServices,
      selectedService: null,
      handleExecuteConfirmedTask: mockHandleExecuteConfirmedTask,
    });

    render(
      <MemoryRouter>
        <BuyerAgent />
      </MemoryRouter>
    );

    const submitBtn = screen.getByRole('button', { name: /Run Task/i });
    fireEvent.click(submitBtn);

    expect(mockHandleExecuteConfirmedTask).not.toHaveBeenCalled();
  });

  it('submits valid task and navigates to /execution/:taskId upon receiving real task ID', async () => {
    const mockSuccessResponse: TaskResponse = {
      task_id: 'task-auth-987654',
      status: 'accepted',
      budget_allocated_usdc: '0.08',
      total_cost_usdc: '0.005',
      cost_explanation: 'Executed 2 steps',
      selected_services: ['data_001', 'scraping_001'],
      executions: [],
      final_result: 'Synthesized data findings',
      errors_and_fallbacks: [],
    };

    mockHandleExecuteConfirmedTask.mockResolvedValueOnce(mockSuccessResponse);

    render(
      <MemoryRouter>
        <BuyerAgent />
      </MemoryRouter>
    );

    const submitBtn = screen.getByRole('button', { name: /Run Task/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockHandleExecuteConfirmedTask).toHaveBeenCalledWith(
        'Look up relevant structured data and summarize findings',
        '0.08'
      );
      expect(mockNavigate).toHaveBeenCalledWith('/execution/task-auth-987654');
    });
  });

  it('prevents accidental duplicate clicks when isSubmitting is true', () => {
    mockUseMarketplace.mockReturnValue({
      taskPrompt: 'Valid task description',
      setTaskPrompt: mockSetTaskPrompt,
      budgetUsdc: '0.08',
      setBudgetUsdc: mockSetBudgetUsdc,
      isSubmitting: true,
      taskError: null,
      services: mockServices,
      selectedService: null,
      handleExecuteConfirmedTask: mockHandleExecuteConfirmedTask,
    });

    render(
      <MemoryRouter>
        <BuyerAgent />
      </MemoryRouter>
    );

    const submitBtn = screen.getByRole('button', { name: /Dispatching Task to Orchestrator/i });
    expect(submitBtn).toBeDisabled();

    fireEvent.click(submitBtn);
    expect(mockHandleExecuteConfirmedTask).not.toHaveBeenCalled();
  });

  it('displays API error states when backend rejects request', async () => {
    mockHandleExecuteConfirmedTask.mockRejectedValueOnce(
      new Error('Value error, budget_usdc must be strictly positive (> 0).')
    );

    render(
      <MemoryRouter>
        <BuyerAgent />
      </MemoryRouter>
    );

    const submitBtn = screen.getByRole('button', { name: /Run Task/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Validation or API Error/i)).toBeInTheDocument();
      expect(screen.getByText(/budget_usdc must be strictly positive/i)).toBeInTheDocument();
    });
  });

  it('displays preselected service indicator when arriving from Marketplace', () => {
    mockUseMarketplace.mockReturnValue({
      taskPrompt: promptState,
      setTaskPrompt: mockSetTaskPrompt,
      budgetUsdc: budgetState,
      setBudgetUsdc: mockSetBudgetUsdc,
      isSubmitting: false,
      taskError: null,
      services: mockServices,
      selectedService: mockServices[0],
      handleExecuteConfirmedTask: mockHandleExecuteConfirmedTask,
    });

    render(
      <MemoryRouter>
        <BuyerAgent />
      </MemoryRouter>
    );

    expect(screen.getByText(/Marketplace Pre-Selection Active/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Alpha Financial Market Data/i).length).toBeGreaterThanOrEqual(1);
  });
});

describe('Monetary Correctness & Atomic Conversion Suite', () => {
  it('converts USDC strings to exact 6-decimal integer atomic base units without float error', () => {
    expect(toAtomicUnits('0.002')).toBe(2000);
    expect(toAtomicUnits('0.003')).toBe(3000);
    expect(toAtomicUnits('0.05')).toBe(50000);
    expect(toAtomicUnits('0.08')).toBe(80000);
    expect(toAtomicUnits('1.000000')).toBe(1000000);
    expect(toAtomicUnits('0')).toBe(0);
    expect(toAtomicUnits('invalid')).toBe(0);
  });

  it('converts integer atomic base units back to formatted USDC string', () => {
    expect(fromAtomicUnits(2000)).toBe('0.002000');
    expect(fromAtomicUnits(50000)).toBe('0.050000');
    expect(fromAtomicUnits(1000000)).toBe('1.000000');
  });

  it('validates task prompt length requirements (>= 3 chars)', () => {
    expect(validateTaskPrompt('').isValid).toBe(false);
    expect(validateTaskPrompt('ab').isValid).toBe(false);
    expect(validateTaskPrompt('abc').isValid).toBe(true);
    expect(validateTaskPrompt('Valid research goal').isValid).toBe(true);
  });

  it('validates budget values (> 0 USDC)', () => {
    expect(validateBudget('').isValid).toBe(false);
    expect(validateBudget('0').isValid).toBe(false);
    expect(validateBudget('-0.5').isValid).toBe(false);
    expect(validateBudget('abc').isValid).toBe(false);
    expect(validateBudget('0.05').isValid).toBe(true);
    expect(validateBudget('0.05').atomicUnits).toBe(50000);
  });
});
