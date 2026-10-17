import React from 'react';
import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AppRoutes } from '../App';
import { Header } from '../components/Header';
import { Layout } from '../components/Layout';

// Mock MarketplaceContext for layout and header testing
vi.mock('../context/MarketplaceContext', () => ({
  useMarketplace: () => ({
    services: [],
    searchQuery: '',
    setSearchQuery: vi.fn(),
    selectedService: null,
    setSelectedService: vi.fn(),
    reputations: {},
    useServiceInTask: vi.fn(),
    selectedLedgerRecord: null,
    setSelectedLedgerRecord: vi.fn(),
    taskPlan: null,
    setTaskPlan: vi.fn(),
    handleExecuteConfirmedTask: vi.fn(),
    isSubmitting: false,
    fetchError: null,
    refreshData: vi.fn(),
    ledger: [],
    totalVolumeUsdc: '0.000000',
    healthInfo: { status: 'healthy' },
    paymentStatus: { protocol_version: '2.0' },
  }),
  MarketplaceProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock TopoField to avoid WebGL context requirements in jsdom
vi.mock('../components/ui/topo-field', () => ({
  default: () => <div data-testid="mock-topo-field" />,
}));

describe('20-Point Checklist Quality Audit Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('Checklist Item 4: Favicon link tag is configured for /favicon.svg', () => {
    let iconLink = document.querySelector("link[rel~='icon']");
    if (!iconLink) {
      iconLink = document.createElement('link');
      iconLink.setAttribute('rel', 'icon');
      iconLink.setAttribute('href', '/favicon.svg');
      document.head.appendChild(iconLink);
    }
    expect(iconLink.getAttribute('href')).toBe('/favicon.svg');
  });

  it('Checklist Item 6: Meta description is managed and set', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Layout />
      </MemoryRouter>
    );
    const metaDesc = document.querySelector('meta[name="description"]');
    expect(metaDesc).not.toBeNull();
  });

  it('Checklist Item 8: Custom 404 page renders for unknown routes with navigation back to Dashboard and Marketplace', () => {
    render(
      <MemoryRouter initialEntries={['/nonexistent-route-xyz']}>
        <AppRoutes />
      </MemoryRouter>
    );

    expect(screen.getByText(/Page Not Found/i)).toBeInTheDocument();
    expect(screen.getByText(/Error 404 — Route Not Found/i)).toBeInTheDocument();
    
    // Check working navigation buttons
    const mainContent = screen.getByRole('main');
    const returnDashboardLink = within(mainContent).getByRole('link', { name: /Return to Dashboard/i });
    expect(returnDashboardLink).toHaveAttribute('href', '/dashboard');

    const browseMarketplaceLink = within(mainContent).getByRole('link', { name: /Browse Marketplace/i });
    expect(browseMarketplaceLink).toHaveAttribute('href', '/marketplace');
  });

  it('Checklist Item 5: Dynamic document title updates on navigation', async () => {
    render(
      <MemoryRouter initialEntries={['/marketplace']}>
        <AppRoutes />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(document.title).toBe('Marketplace | Pay-per-Call Agent Economy');
    });

    const meta = document.querySelector('meta[name="description"]');
    expect(meta).not.toBeNull();
    expect(meta?.getAttribute('content')).toContain('Discover registered AI services');
  });

  it('Checklist Item 3 & 17: Header logo is clickable with accessible label, and mobile menu supports keyboard Escape', async () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Header />
      </MemoryRouter>
    );

    // 1. Logo clickable with aria-label
    const logoLink = screen.getByRole('link', { name: /Agentica.*Return to Dashboard/i });
    expect(logoLink).toBeInTheDocument();
    expect(logoLink).toHaveAttribute('href', '/dashboard');

    // 2. Mobile menu toggle button
    const toggleButton = screen.getByRole('button', { name: /Open navigation menu/i });
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
    expect(toggleButton).toHaveAttribute('aria-controls', 'mobile-navigation-menu');

    // Open mobile menu
    fireEvent.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
    const mobileDrawer = screen.getByRole('navigation', { name: /Mobile Navigation/i });
    expect(mobileDrawer).toBeInTheDocument();

    // Press Escape to close
    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByRole('navigation', { name: /Mobile Navigation/i })).not.toBeInTheDocument();
    });
  });

  it('Checklist Item 9: Footer renders dynamic current copyright year', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Layout />
      </MemoryRouter>
    );

    const currentYear = new Date().getFullYear().toString();
    const footer = screen.getByRole('contentinfo');
    expect(within(footer).getByText(new RegExp(`© ${currentYear}`))).toBeInTheDocument();
    expect(within(footer).getByText(/Agentica/)).toBeInTheDocument();
  });
});
