import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MarketplaceProvider } from './context/MarketplaceContext';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import { Marketplace } from './pages/Marketplace';
import { Payments } from './pages/Payments';
import { BuyerAgent } from './pages/BuyerAgent';
import { SellerTools } from './pages/SellerTools';
import { Analytics } from './pages/Analytics';
import { About } from './pages/About';
import { Docs } from './pages/Docs';

export const App: React.FC = () => {
  return (
    <MarketplaceProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="marketplace" element={<Marketplace />} />
            <Route path="payments" element={<Payments />} />
            <Route path="buyer" element={<BuyerAgent />} />
            <Route path="seller" element={<SellerTools />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="about" element={<About />} />
            <Route path="docs" element={<Docs />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </MarketplaceProvider>
  );
};

export default App;
