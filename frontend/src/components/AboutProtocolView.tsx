import React from 'react';
import { 
  Zap, 
  FileText, 
  ShieldCheck, 
  ArrowRight, 
  Cpu, 
  Lock
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
      {/* Hero section */}
      <div className="bg-[#171819] p-8 rounded-lg border border-[#303133] text-center space-y-3">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-[#FF982E]/10 text-[#FF982E] border border-[#FF982E]/30 text-xs font-mono">
          <Zap className="w-3.5 h-3.5" />
          <span>DI-06 Specification</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-[#F5F5F5] tracking-tight font-sans">
          Pay-Per-Call Agent Economy Architecture
        </h2>
        <p className="text-[#A0A1A5] text-xs sm:text-sm max-w-2xl mx-auto leading-relaxed font-sans">
          An autonomous marketplace orchestrating agent-to-agent micropayments on Base Sepolia. Buyer agents decompose goals into microtasks, negotiate cryptographic payment terms, and verify outputs on an immutable audit ledger.
        </p>
      </div>

      {/* Protocol Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-[#171819] p-5 rounded-lg border border-[#303133] space-y-2">
          <div className="flex items-center gap-2 text-[#FF982E] font-bold font-mono text-xs">
            <Lock className="w-4 h-4" />
            <span>x402 v2 Challenge-Response</span>
          </div>
          <p className="text-xs text-[#A0A1A5] font-sans leading-relaxed">
            The standard HTTP 402 Payment Required flow guarantees that agents never pay for unavailable endpoints. The seller issues a nonced cryptographic requirement, and the buyer submits a signed EIP-712 payment authorization.
          </p>
        </div>

        <div className="bg-[#171819] p-5 rounded-lg border border-[#303133] space-y-2">
          <div className="flex items-center gap-2 text-[#58B779] font-bold font-mono text-xs">
            <ShieldCheck className="w-4 h-4" />
            <span>Integer Atomic Units Money Math</span>
          </div>
          <p className="text-xs text-[#A0A1A5] font-sans leading-relaxed">
            Floating-point money arithmetic is strictly prohibited across the system. All internal balances, pricing calculations, and ledger records use integer base units (1 USDC = 1,000,000 base units).
          </p>
        </div>

        <div className="bg-[#171819] p-5 rounded-lg border border-[#303133] space-y-2">
          <div className="flex items-center gap-2 text-[#FF982E] font-bold font-mono text-xs">
            <FileText className="w-4 h-4" />
            <span>Immutable Audit Ledger</span>
          </div>
          <p className="text-xs text-[#A0A1A5] font-sans leading-relaxed">
            Every transaction, output rejection, or refusal is persisted with roundtrip latency, buyer/seller IDs, and Base Sepolia transaction hashes. Statuses distinguish verified payment, refusal, and uncharged errors.
          </p>
        </div>

        <div className="bg-[#171819] p-5 rounded-lg border border-[#303133] space-y-2">
          <div className="flex items-center gap-2 text-[#52758D] font-bold font-mono text-xs">
            <Cpu className="w-4 h-4" />
            <span>Dynamic Reputation Scoring</span>
          </div>
          <p className="text-xs text-[#A0A1A5] font-sans leading-relaxed">
            Seller agents build reputation strictly from genuine transaction outcomes: successful completion rates, schema conformance, and median execution latency.
          </p>
        </div>
      </div>

      {/* Contract Reference */}
      <div className="bg-[#171819] p-5 rounded-lg border border-[#303133] space-y-3 text-xs font-mono">
        <h3 className="text-xs font-bold text-[#F5F5F5] font-sans uppercase">Network Configuration</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[#A0A1A5]">
          <div className="bg-[#111214] p-3 rounded border border-[#303133]">
            <span className="text-[#777980] text-[10px] block uppercase">Chain Identifier</span>
            <span className="text-[#FF982E] font-bold">eip155:84532</span> (Base Sepolia)
          </div>
          <div className="bg-[#111214] p-3 rounded border border-[#303133]">
            <span className="text-[#777980] text-[10px] block uppercase">USDC Contract Address</span>
            <span className="text-[#F5F5F5] text-[11px] break-all font-mono">0x036CbD53842c5426634e7929541eC2318f3dCF7e</span>
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="text-center pt-2 flex justify-center gap-3">
        <button
          onClick={onGoToMarketplace}
          className="px-4 py-2 rounded-lg bg-[#202123] hover:bg-[#303133] text-[#A0A1A5] hover:text-[#F5F5F5] text-xs font-semibold font-mono transition-colors border border-[#303133]"
        >
          Explore Services
        </button>
        <button
          onClick={onGoToConsole}
          className="px-5 py-2 rounded-lg bg-[#FF982E] hover:bg-[#E98522] text-[#101112] text-xs font-bold font-mono uppercase tracking-wide transition-all shadow-sm shadow-[#FF982E]/30 flex items-center gap-1.5"
        >
          <span>Launch Buyer Task Console</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
