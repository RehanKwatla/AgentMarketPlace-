import { describe, it, expect, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Marketplace } from '../pages/Marketplace';
import { ServiceCard } from '../components/ServiceCard';
import { ServiceDetailModal } from '../components/ServiceDetailModal';
import { ServiceDefinition } from '../types';

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
    description: 'Provides real-time crypto asset market data.',
    input_schema: { type: 'object', properties: { symbol: { type: 'string' } } },
    output_schema: { type: 'object', properties: { price: { type: 'number' } } },
    is_active: true,
    enabled: true,
    capabilities: ['data.lookup.v1', 'crypto.market.rates'],
    reputation: {
      service_id: 'data_001',
      reputation_score: 98.5,
      success_rate: 0.99,
      median_latency_ms: 120,
      total_calls: 120,
      successful_calls: 119,
      listed_price_usdc: '0.002',
    },
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
    description: 'Fetches remote web content and outputs clean markdown.',
    input_schema: { type: 'object', properties: { url: { type: 'string' } } },
    output_schema: { type: 'object', properties: { content: { type: 'string' } } },
    is_active: true,
    enabled: true,
    capabilities: ['scraping.extract.v1', 'web.markdown.fetch'],
    reputation: {
      service_id: 'scraping_001',
      reputation_score: 96.0,
      success_rate: 0.96,
      median_latency_ms: 450,
      total_calls: 45,
      successful_calls: 43,
      listed_price_usdc: '0.003',
    },
  },
  {
    service_id: 'inference_001',
    name: 'LLM Synthesis Engine',
    category: 'inference',
    endpoint_url: 'http://localhost:8000/api/v1/seller/inference',
    price_usdc: '0.005',
    price_atomic: 5000,
    price_base_units: 5000,
    network: 'eip155:84532',
    pay_to: '0x0000000000000000000000000000000000000003',
    description: 'Analytical reasoning and summarization synthesis.',
    input_schema: { type: 'object', properties: { prompt: { type: 'string' } } },
    output_schema: { type: 'object', properties: { response: { type: 'string' } } },
    is_active: true,
    enabled: true,
    capabilities: ['inference.summarize.v1', 'ai.reasoning.synthesis'],
    reputation: {
      service_id: 'inference_001',
      reputation_score: 99.0,
      success_rate: 0.99,
      median_latency_ms: 620,
      total_calls: 80,
      successful_calls: 79,
      listed_price_usdc: '0.005',
    },
  },
];

describe('Marketplace Component & Filtering Suite', () => {
  const mockSetSelectedService = vi.fn();
  const mockUseServiceInTask = vi.fn();
  const mockRefreshData = vi.fn();
  const mockSetSearchQuery = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseMarketplace.mockReturnValue({
      services: mockServices,
      reputations: {},
      setSelectedService: mockSetSelectedService,
      useServiceInTask: mockUseServiceInTask,
      fetchError: null,
      refreshData: mockRefreshData,
      searchQuery: '',
      setSearchQuery: mockSetSearchQuery,
    });
  });

  it('renders all services by default in the registry', () => {
    render(
      <MemoryRouter>
        <Marketplace />
      </MemoryRouter>
    );

    expect(screen.getByText('Alpha Financial Market Data')).toBeInTheDocument();
    expect(screen.getByText('Web Markdown Extractor')).toBeInTheDocument();
    expect(screen.getByText('LLM Synthesis Engine')).toBeInTheDocument();
  });

  it('filters services by category tab (Data Providers)', () => {
    render(
      <MemoryRouter>
        <Marketplace />
      </MemoryRouter>
    );

    // Click Data Providers category tab
    const dataTab = screen.getByRole('button', { name: /Data Providers/i });
    fireEvent.click(dataTab);

    // Should show Alpha Financial Market Data
    expect(screen.getByText('Alpha Financial Market Data')).toBeInTheDocument();
    // Should NOT show Web Markdown Extractor or LLM Synthesis Engine
    expect(screen.queryByText('Web Markdown Extractor')).not.toBeInTheDocument();
    expect(screen.queryByText('LLM Synthesis Engine')).not.toBeInTheDocument();
  });

  it('filters services by maximum price threshold', () => {
    render(
      <MemoryRouter>
        <Marketplace />
      </MemoryRouter>
    );

    // Select max price ≤ 0.003 USDC
    const maxPriceSelect = screen.getByDisplayValue('Any Price');
    fireEvent.change(maxPriceSelect, { target: { value: '0.003' } });

    // 0.002 and 0.003 should be visible
    expect(screen.getByText('Alpha Financial Market Data')).toBeInTheDocument();
    expect(screen.getByText('Web Markdown Extractor')).toBeInTheDocument();
    // 0.005 exceeds cap
    expect(screen.queryByText('LLM Synthesis Engine')).not.toBeInTheDocument();
  });

  it('filters services by search query matching capabilities or text', () => {
    render(
      <MemoryRouter>
        <Marketplace />
      </MemoryRouter>
    );

    const searchInput = screen.getByPlaceholderText(/Search by service name/i);
    fireEvent.change(searchInput, { target: { value: 'markdown' } });

    expect(screen.getByText('Web Markdown Extractor')).toBeInTheDocument();
    expect(screen.queryByText('Alpha Financial Market Data')).not.toBeInTheDocument();
    expect(screen.queryByText('LLM Synthesis Engine')).not.toBeInTheDocument();
  });

  it('clearing filters restores the full service set', () => {
    render(
      <MemoryRouter>
        <Marketplace />
      </MemoryRouter>
    );

    // Apply category filter
    const dataTab = screen.getByRole('button', { name: /Data Providers/i });
    fireEvent.click(dataTab);
    expect(screen.queryByText('Web Markdown Extractor')).not.toBeInTheDocument();

    // Click Reset Filters
    const resetBtn = screen.getByRole('button', { name: /Reset Filters/i });
    fireEvent.click(resetBtn);

    // All services restored
    expect(screen.getByText('Alpha Financial Market Data')).toBeInTheDocument();
    expect(screen.getByText('Web Markdown Extractor')).toBeInTheDocument();
    expect(screen.getByText('LLM Synthesis Engine')).toBeInTheDocument();
  });

  it('displays honest empty state when no services match criteria', () => {
    render(
      <MemoryRouter>
        <Marketplace />
      </MemoryRouter>
    );

    const searchInput = screen.getByPlaceholderText(/Search by service name/i);
    fireEvent.change(searchInput, { target: { value: 'nonexistent-query-xyz' } });

    expect(screen.getByText('No services match your filters')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Clear All Filters/i })).toBeInTheDocument();
  });

  it('triggers useServiceInTask and navigates to /buyer on "Use Service" action', () => {
    render(
      <MemoryRouter>
        <Marketplace />
      </MemoryRouter>
    );

    const useButtons = screen.getAllByRole('button', { name: /Use Service/i });
    fireEvent.click(useButtons[0]);

    expect(mockUseServiceInTask).toHaveBeenCalledWith(mockServices[0]);
    expect(mockNavigate).toHaveBeenCalledWith('/buyer');
  });

  it('triggers setSelectedService on "View Details" action', () => {
    render(
      <MemoryRouter>
        <Marketplace />
      </MemoryRouter>
    );

    const detailButtons = screen.getAllByRole('button', { name: /View Details/i });
    fireEvent.click(detailButtons[0]);

    expect(mockSetSelectedService).toHaveBeenCalledWith(mockServices[0]);
  });
});

describe('ServiceCard Component', () => {
  it('renders service information, price in USDC, and provider address', () => {
    const handleSelect = vi.fn();
    const handleDetail = vi.fn();

    render(
      <ServiceCard
        service={mockServices[0]}
        onSelect={handleSelect}
        onViewDetail={handleDetail}
      />
    );

    expect(screen.getByText('Alpha Financial Market Data')).toBeInTheDocument();
    expect(screen.getByText('0.002')).toBeInTheDocument();
    expect(screen.getByText('USDC')).toBeInTheDocument();
    expect(screen.getByText('data')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('shows honest "No call history yet" state when total calls is 0', () => {
    const freshService: ServiceDefinition = {
      ...mockServices[0],
      reputation: undefined,
    };

    render(<ServiceCard service={freshService} />);

    expect(screen.getByText('No call history yet')).toBeInTheDocument();
  });
});

describe('ServiceDetailModal Component', () => {
  it('displays full capabilities, schemas, and provider pay_to recipient', () => {
    const handleClose = vi.fn();
    const handleUse = vi.fn();

    render(
      <ServiceDetailModal
        service={mockServices[0]}
        onClose={handleClose}
        onUseInTask={handleUse}
      />
    );

    expect(screen.getByText('Alpha Financial Market Data')).toBeInTheDocument();
    expect(screen.getByText('ID: data_001')).toBeInTheDocument();
    expect(screen.getByText('0x0000000000000000000000000000000000000001')).toBeInTheDocument();
    expect(screen.getByText('Input JSON Schema')).toBeInTheDocument();
    expect(screen.getByText('Output JSON Schema')).toBeInTheDocument();
    expect(screen.getByText('data.lookup.v1')).toBeInTheDocument();
  });

  it('triggers onUseInTask and onClose when "Use in Buyer Task" is clicked', () => {
    const handleClose = vi.fn();
    const handleUse = vi.fn();

    render(
      <ServiceDetailModal
        service={mockServices[0]}
        onClose={handleClose}
        onUseInTask={handleUse}
      />
    );

    const useTaskBtn = screen.getByRole('button', { name: /Use in Buyer Task/i });
    fireEvent.click(useTaskBtn);

    expect(handleUse).toHaveBeenCalledWith(mockServices[0]);
    expect(handleClose).toHaveBeenCalled();
  });
});
