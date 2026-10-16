import React from 'react';
import { Navigate } from 'react-router-dom';

// Note: Dashboard.tsx has been refactored into dedicated modular routes:
// - Home (/): pages/Home.tsx
// - Marketplace (/marketplace): pages/Marketplace.tsx
// - Payments (/payments): pages/Payments.tsx
// - Buyer Agent (/buyer): pages/BuyerAgent.tsx
// - Seller Tools (/seller): pages/SellerTools.tsx
// - Analytics (/analytics): pages/Analytics.tsx
// - About (/about): pages/About.tsx
// - Docs (/docs): pages/Docs.tsx

export const Dashboard: React.FC = () => {
  return <Navigate to="/" replace />;
};

export default Dashboard;
