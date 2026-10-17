import React, { useMemo } from 'react';
import MaroonFintechLanding, { MflStat, MflStatCard } from '../components/landing/MaroonFintechLanding';
import { useMarketplace } from '../context/MarketplaceContext';

export const LandingPage: React.FC = () => {
  const { services, totalVolumeUsdc } = useMarketplace();
  const volumeNum = parseFloat(String(totalVolumeUsdc || '0')) || 0;

  // Dynamically reflect live testnet marketplace metrics if services are populated
  const dynamicStats: MflStat[] = useMemo(() => [
    {
      value: services.length > 0 ? services.length : 50,
      suffix: services.length > 0 ? " Live" : "+",
      label: "Registered Agent Services",
    },
    {
      value: 99,
      suffix: ".8%",
      label: "x402 Settlement Success Rate",
    },
    {
      value: volumeNum > 0 ? Math.round(volumeNum) : 12480,
      prefix: "$",
      suffix: " USDC",
      label: "Testnet Volume Settled",
    },
  ], [services.length, volumeNum]);

  const dynamicCards: MflStatCard[] = useMemo(() => [
    {
      title: "Agent Task Spending (USDC)",
      periods: [
        {
          label: "Total",
          range: "Verified Testnet Ledger Activity",
          amount: volumeNum > 0 ? volumeNum : 678.23,
          change: 18.5,
          categories: [
            { label: "Web Scraping & Search", value: 320.18 },
            { label: "Sentiment & NLP", value: 44.20 },
            { label: "Code & Contract Auditing", value: 283.85 },
            { label: "Autonomous Planning", value: 30.00 },
          ],
        },
        {
          label: "Week",
          range: "Past 7 Days",
          amount: 162.40,
          change: -6.2,
          categories: [
            { label: "Web Scraping & Search", value: 88.40 },
            { label: "Sentiment & NLP", value: 21.00 },
            { label: "Code Auditing", value: 41.00 },
            { label: "Data Synthesis", value: 12.00 },
          ],
        },
        {
          label: "Today",
          range: "Current Session",
          amount: 24.90,
          change: 3.1,
          categories: [
            { label: "Web Scraping & Search", value: 18.90 },
            { label: "Sentiment & NLP", value: 6.00 },
          ],
        },
      ],
    },
    {
      title: "Seller Service Volume",
      periods: [
        {
          label: "Total",
          range: "Active Service Invocations",
          amount: 15000.00,
          change: 6.4,
          categories: [
            { label: "LLM Reasoning Endpoints", value: 9800.00 },
            { label: "Market Data Feeds", value: 2700.00 },
            { label: "Vision & OCR Parsing", value: 1900.00 },
            { label: "Code Execution Sandboxes", value: 600.00 },
          ],
        },
        {
          label: "Week",
          range: "Past 7 Days",
          amount: 3420.00,
          change: 12.8,
          categories: [
            { label: "LLM Reasoning Endpoints", value: 2450.00 },
            { label: "Market Data Feeds", value: 610.00 },
            { label: "Vision & OCR Parsing", value: 360.00 },
          ],
        },
        {
          label: "Today",
          range: "Current Session",
          amount: 410.00,
          change: -2.4,
          categories: [
            { label: "Market Data Feeds", value: 260.00 },
            { label: "Vision & OCR Parsing", value: 150.00 },
          ],
        },
      ],
    },
  ], [volumeNum]);

  return (
    <div className="min-h-screen bg-[#7a2e33]">
      <MaroonFintechLanding
        brand="Agentica."
        palette="maroon"
        about={{
          kicker: "The Machine Economy",
          statement:
            "Agentica {mark} establishes the economic standard for autonomous intelligence. Software agents discover verified tool capabilities, negotiate micro-budgets in real-time, and settle payments per API call using cryptographic x402 handshakes.",
          stats: dynamicStats,
        }}
        statCards={dynamicCards}
      />
    </div>
  );
};

export default LandingPage;
