import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MarketplaceProvider } from './context/MarketplaceContext';
import { AuthProvider } from './context/AuthContext';
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
import { 
  LoginPage, 
  SignupPage, 
  VerifyEmailPage, 
  ForgotPasswordPage, 
  ResetPasswordPage 
} from './pages/AuthFlow';
import { KycPage } from './pages/KycPage';
import { WalletManagementPage } from './pages/WalletManagement';
import { ProfilePage } from './pages/Profile';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* 1. Standalone Authentication & Landing Experience */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/landing" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

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

        {/* Phase 3 Authenticated Workspace Routes */}
        <Route path="profile" element={<ProfilePage />} />
        <Route path="wallets" element={<WalletManagementPage />} />
        <Route path="kyc" element={<KycPage />} />

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MarketplaceProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </MarketplaceProvider>
    </AuthProvider>
  );
};

export default App;
