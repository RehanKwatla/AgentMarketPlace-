import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MarketplaceProvider } from './context/MarketplaceContext';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Marketplace } from './pages/Marketplace';
import { BuyerAgent } from './pages/BuyerAgent';
import { AgentExecution } from './pages/AgentExecution';
import { PaymentProcessing } from './pages/PaymentProcessing';
import { Results } from './pages/Results';
import { Ledger } from './pages/Ledger';
import { SellerTools } from './pages/SellerTools';
import { Analytics } from './pages/Analytics';
import { About } from './pages/About';
import { Docs } from './pages/Docs';
import { NotFound } from './pages/NotFound';

import { LandingPage } from './pages/LandingPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* 1. Standalone Landing Page Experience */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/landing" element={<LandingPage />} />

      {/* 2. Main Application Workspace wrapped inside persistent Layout */}
      <Route element={<Layout />}>
        <Route path="app" element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="marketplace" element={<Marketplace />} />
        <Route path="buyer" element={<BuyerAgent />} />
        
        {/* Agent Execution routes with and without taskId param */}
        <Route path="execution" element={<AgentExecution />} />
        <Route path="execution/:taskId" element={<AgentExecution />} />
        
        <Route path="payments" element={<PaymentProcessing />} />
        
        {/* Results routes with and without taskId param */}
        <Route path="results" element={<Results />} />
        <Route path="results/:taskId" element={<Results />} />
        
        <Route path="ledger" element={<Ledger />} />
        <Route path="seller" element={<SellerTools />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="about" element={<About />} />
        <Route path="docs" element={<Docs />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
};

export const App: React.FC = () => {
  return (
    <MarketplaceProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </MarketplaceProvider>
  );
};

export default App;
