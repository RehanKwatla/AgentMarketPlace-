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
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Hero section */}
      <div className="glass-panel p-8 rounded-2xl border border-slate-800 text-center space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-mono">
          <Zap className="w-3.5 h-3.5" />
          <span>DI-06 Specification</span>
        </div>
        <h2 className="text-3xl font-extrabold text-white tracking-tight">
          Pay-Per-Call Agent Economy Architecture
        </h2>
        <p className="text-slate-400 text-sm max-w-2xl mx-auto leading-relaxed font-sans">
          An autonomous marketplace orchestrating agent-to-agent micropayments on Base Sepolia. Buyer agents decompose goals into microtasks, negotiate cryptographic payment terms, and verify outputs on an immutable audit ledger.
        </p>
      </div>

      {/* Protocol Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center gap-2.5 text-blue-400 font-bold font-mono text-sm">
            <Lock className="w-4 h-4" />
            <span>x402 v2 Challenge-Response</span>
          </div>
          <p className="text-xs text-slate-300 font-sans leading-relaxed">
            The standard HTTP 402 Payment Required flow guarantees that agents never pay for unavailable endpoints. The seller issues a nonced cryptographic requirement, and the buyer submits a signed EIP-712 payment authorization.
          </p>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center gap-2.5 text-emerald-400 font-bold font-mono text-sm">
            <ShieldCheck className="w-4 h-4" />
            <span>Integer Atomic Units Money Math</span>
          </div>
          <p className="text-xs text-slate-300 font-sans leading-relaxed">
            Floating-point money arithmetic is strictly prohibited across the system. All internal balances, pricing calculations, and ledger records use integer base units (1 USDC = 1,000,000 base units).
          </p>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center gap-2.5 text-amber-300 font-bold font-mono text-sm">
            <FileText className="w-4 h-4" />
            <span>Immutable Audit Ledger</span>
          </div>
          <p className="text-xs text-slate-300 font-sans leading-relaxed">
            Every transaction, output rejection, or refusal is persisted with roundtrip latency, buyer/seller IDs, and Base Sepolia transaction hashes. Statuses distinguish verified payment, refusal, and uncharged errors.
          </p>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center gap-2.5 text-purple-400 font-bold font-mono text-sm">
            <Cpu className="w-4 h-4" />
            <span>Dynamic Reputation Scoring</span>
          </div>
          <p className="text-xs text-slate-300 font-sans leading-relaxed">
            Seller agents build reputation strictly from genuine transaction outcomes: successful completion rates, schema conformance, and median execution latency.
          </p>
        </div>
      </div>

      {/* Contract Reference */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3 text-xs font-mono">
        <h3 className="text-sm font-bold text-white font-sans">Network Configuration</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-slate-300">
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
            <span className="text-slate-500 text-[10px] block">CHAIN IDENTIFIER</span>
            <span className="text-blue-400 font-bold">eip155:84532</span> (Base Sepolia)
          </div>
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
            <span className="text-slate-500 text-[10px] block">USDC CONTRACT</span>
            <span className="text-slate-200 text-[10px] break-all">0x036CbD53842c5426634e7929541eC2318f3dCF7e</span>
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="text-center pt-4 flex justify-center gap-4">
        <button
          onClick={onGoToMarketplace}
          className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold font-mono transition-colors border border-slate-700"
        >
          Explore Services
        </button>
        <button
          onClick={onGoToConsole}
          className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold font-mono uppercase tracking-wide transition-colors shadow-lg shadow-blue-500/20 flex items-center gap-2"
        >
          <span>Launch Buyer Task Console</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
