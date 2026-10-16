import React from 'react';
import { 
  FileText, 
  ShieldCheck, 
  ArrowRight, 
  Cpu, 
  Lock,
  Coins
} from 'lucide-react';

interface AboutProtocolViewProps {
  onGoToConsole: () => void;
  onGoToMarketplace: () => void;
}

export const AboutProtocolView: React.FC<AboutProtocolViewProps> = ({
  onGoToConsole,
  onGoToMarketplace
}) => {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="border-b border-[rgba(120,160,153,0.16)] pb-4 space-y-1">
        <h1 className="text-xl sm:text-2xl font-semibold text-[#F4F7F6] tracking-tight">
          Protocol Architecture & Standards
        </h1>
        <p className="text-xs text-[#A0AAA7] leading-relaxed max-w-2xl">
          An autonomous marketplace orchestrating agent-to-agent micropayments on Base Sepolia via standardized HTTP 402 v2 challenge flows.
        </p>
      </div>

      {/* Protocol Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-[#101514] p-4 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-1.5">
          <div className="flex items-center gap-2 text-[#36D6C8] font-medium text-xs">
            <Lock className="w-3.5 h-3.5" />
            <span>x402 v2 Challenge-Response</span>
          </div>
          <p className="text-xs text-[#A0AAA7] leading-relaxed">
            Endpoints return HTTP 402 with signed requirements. Buyer agents submit signed EIP-712 authorizations only after validating requirements.
          </p>
        </div>

        <div className="bg-[#101514] p-4 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-1.5">
          <div className="flex items-center gap-2 text-[#42C995] font-medium text-xs">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Integer Base Units Math</span>
          </div>
          <p className="text-xs text-[#A0AAA7] leading-relaxed">
            Floating-point money arithmetic is prohibited. All calculations use exact integer base units (1 USDC = 1,000,000 base units).
          </p>
        </div>

        <div className="bg-[#101514] p-4 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-1.5">
          <div className="flex items-center gap-2 text-[#36D6C8] font-medium text-xs">
            <FileText className="w-3.5 h-3.5" />
            <span>Audit Ledger & Receipts</span>
          </div>
          <p className="text-xs text-[#A0AAA7] leading-relaxed">
            Every transaction, signature proof, and verification receipt is recorded in the audit ledger with latency and settlement status tracking.
          </p>
        </div>

        <div className="bg-[#101514] p-4 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-1.5">
          <div className="flex items-center gap-2 text-[#53E3D6] font-medium text-xs">
            <Cpu className="w-3.5 h-3.5" />
            <span>Autonomous Orchestration</span>
          </div>
          <p className="text-xs text-[#A0AAA7] leading-relaxed">
            Buyer agents automatically budget, select sellers by reputation, execute payments, and aggregate multi-service task outputs.
          </p>
        </div>
      </div>

      {/* Seller Archetypes */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold text-[#F4F7F6]">
          Seller Archetypes
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="bg-[#101514] p-4 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-1">
            <span className="text-[11px] text-[#36D6C8] font-medium block">
              Data Providers
            </span>
            <h3 className="font-medium text-[#F4F7F6]">Market Telemetry</h3>
            <p className="text-[#A0AAA7] leading-relaxed text-[11px]">
              Streaming prices, order book metrics, and on-chain oracle feeds via HTTP 402 endpoints.
            </p>
          </div>

          <div className="bg-[#101514] p-4 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-1">
            <span className="text-[11px] text-[#42C995] font-medium block">
              Web Scraping
            </span>
            <h3 className="font-medium text-[#F4F7F6]">Content Extraction</h3>
            <p className="text-[#A0AAA7] leading-relaxed text-[11px]">
              Fetches remote URLs, bypasses bot shields, and formats structured markdown.
            </p>
          </div>

          <div className="bg-[#101514] p-4 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-1">
            <span className="text-[11px] text-[#53E3D6] font-medium block">
              AI Inference
            </span>
            <h3 className="font-medium text-[#F4F7F6]">Reasoning & Synthesis</h3>
            <p className="text-[#A0AAA7] leading-relaxed text-[11px]">
              High-capacity LLM queries, multi-source summarization, and task evaluation.
            </p>
          </div>
        </div>
      </div>

      {/* Network Configuration Summary */}
      <div className="bg-[#101514] p-5 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-3 text-xs">
        <h2 className="text-xs font-semibold text-[#F4F7F6] flex items-center gap-1.5">
          <Coins className="w-3.5 h-3.5 text-[#36D6C8]" />
          <span>Active Testnet Configuration</span>
        </h2>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.14)]">
            <span className="text-[#A0AAA7] block text-[11px] mb-0.5">Network Identifier</span>
            <span className="text-[#F4F7F6] font-mono text-[11px]">Base Sepolia (eip155:84532)</span>
          </div>

          <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.14)]">
            <span className="text-[#A0AAA7] block text-[11px] mb-0.5">Payment Token</span>
            <span className="text-[#36D6C8] font-mono text-[11px]">Base Sepolia USDC (0x036CbD53...)</span>
          </div>
        </div>

        <div className="pt-2 flex flex-wrap gap-3">
          <button
            onClick={onGoToMarketplace}
            className="px-4 py-2 rounded-lg bg-[#36D6C8] hover:bg-[#53E3D6] text-[#0B0D0D] font-medium text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            <span>Explore Services</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onGoToConsole}
            className="px-4 py-2 rounded-lg bg-[#141A19] hover:bg-[#1A2221] text-[#F4F7F6] hover:text-[#36D6C8] text-xs font-medium transition-colors border border-[rgba(120,160,153,0.20)] cursor-pointer"
          >
            Launch Buyer Agent
          </button>
        </div>
      </div>
    </div>
  );
};
