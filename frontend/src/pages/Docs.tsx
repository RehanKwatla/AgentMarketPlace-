import React, { useState } from 'react';
import { 
  ExternalLink, 
  Copy, 
  Check, 
  Code2, 
  Lock, 
  Cpu 
} from 'lucide-react';
import { getApiEndpointLabel } from '../api/client';

export const Docs: React.FC = () => {
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  const copySnippet = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedSection(id);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const curlChallengeSnippet = `curl -X POST http://localhost:8000/api/v1/seller/data \\
  -H "Content-Type: application/json" \\
  -d '{"query": "ETH"}'`;

  const headerResponseSnippet = `HTTP/1.1 402 Payment Required
X-402-Requirement: {
  "version": "2.0",
  "network": "eip155:84532",
  "token": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
  "amount": "2000",
  "payTo": "0x0000000000000000000000000000000000000001",
  "nonce": "e81d77a94f6c4989b52a1c"
}`;

  const pythonBuyerSnippet = `from backend.buyer.orchestrator import BuyerOrchestrator

orchestrator = BuyerOrchestrator()
task_result = await orchestrator.run_task(
    prompt="Collect market data on ETH and summarize key metrics",
    budget_usdc="0.05"
)
print(task_result.final_result)`;

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[rgba(255, 255, 255,0.16)] pb-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-[#FAFAFA] tracking-tight">
            Documentation & API Reference
          </h1>
          <p className="text-xs text-[#A3A3A3] mt-0.5 max-w-2xl">
            Integration guide for autonomous buyer and seller agents implementing official x402 v2 challenge flows.
          </p>
        </div>

        <a
          href={`${getApiEndpointLabel()}/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="px-3.5 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#D4D4D4] text-[#0A0A0A] font-medium text-xs transition-colors flex items-center gap-1.5 self-start md:self-auto cursor-pointer"
        >
          <span>Open Swagger UI</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>

      {/* Getting Started & Integration Guides */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#111111] p-4 rounded-xl border border-[rgba(255, 255, 255,0.16)] space-y-1.5">
          <span className="text-[11px] text-[#FFFFFF] font-medium block">
            1. Service Discovery
          </span>
          <h3 className="font-medium text-[#FAFAFA] text-xs">Discover Services</h3>
          <p className="text-xs text-[#A3A3A3] leading-relaxed">
            Query the registry at <code className="text-[#FFFFFF] font-mono text-[11px]">GET /api/v1/services</code> to explore active data, web scraping, and AI inference microservices with verifiable testnet pricing.
          </p>
        </div>

        <div className="bg-[#111111] p-4 rounded-xl border border-[rgba(255, 255, 255,0.16)] space-y-1.5">
          <span className="text-[11px] text-[#A3A3A3] font-medium block">
            2. Task Execution
          </span>
          <h3 className="font-medium text-[#FAFAFA] text-xs">Execute Buyer Tasks</h3>
          <p className="text-xs text-[#A3A3A3] leading-relaxed">
            Submit a prompt and budget to <code className="text-[#FFFFFF] font-mono text-[11px]">POST /api/v1/buyer/tasks</code>. The buyer agent negotiates x402 payment terms, locks budgets, and executes calls automatically.
          </p>
        </div>

        <div className="bg-[#111111] p-4 rounded-xl border border-[rgba(255, 255, 255,0.16)] space-y-1.5">
          <span className="text-[11px] text-[#D4D4D4] font-medium block">
            3. Seller Registration
          </span>
          <h3 className="font-medium text-[#FAFAFA] text-xs">Register a Microservice</h3>
          <p className="text-xs text-[#A3A3A3] leading-relaxed">
            Host an endpoint emitting HTTP 402 challenge requirements, register the endpoint URL, USDC price, and input/output JSON schemas via the Seller Tools tab.
          </p>
        </div>
      </div>

      {/* 1. Protocol Architecture & Header Specification */}
      <div className="bg-[#111111] p-5 rounded-xl border border-[rgba(255, 255, 255,0.16)] space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-[#FAFAFA]">
          <Lock className="w-3.5 h-3.5 text-[#FFFFFF]" />
          <h2>Official x402 v2 HTTP Headers</h2>
        </div>
        <p className="text-xs text-[#A3A3A3] leading-relaxed">
          The x402 v2 protocol enforces a strict three-phase challenge-response handshake between buyer and seller runtimes without custody risk.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="bg-[#0D0D0D] p-3 rounded-lg border border-[rgba(255, 255, 255,0.16)] space-y-1">
            <span className="text-[11px] text-[#FFFFFF] font-medium block">Phase 1: Challenge</span>
            <span className="font-mono text-[11px] text-[#FAFAFA] block font-medium">X-402-Requirement</span>
            <p className="text-[11px] text-[#A3A3A3] mt-0.5 leading-relaxed">
              Emitted with HTTP 402 by the seller containing chain network, USDC token address, price base units, and unique nonce.
            </p>
          </div>

          <div className="bg-[#0D0D0D] p-3 rounded-lg border border-[rgba(255, 255, 255,0.16)] space-y-1">
            <span className="text-[11px] text-[#A3A3A3] font-medium block">Phase 2: Payment</span>
            <span className="font-mono text-[11px] text-[#FAFAFA] block font-medium">X-402-Payment-Payload</span>
            <p className="text-[11px] text-[#A3A3A3] mt-0.5 leading-relaxed">
              Sent with HTTP 200 re-request by the buyer agent containing a signed EIP-712 payment authorization matching the requirement.
            </p>
          </div>

          <div className="bg-[#0D0D0D] p-3 rounded-lg border border-[rgba(255, 255, 255,0.16)] space-y-1">
            <span className="text-[11px] text-[#D4D4D4] font-medium block">Phase 3: Proof</span>
            <span className="font-mono text-[11px] text-[#FAFAFA] block font-medium">X-402-Settlement-Proof</span>
            <p className="text-[11px] text-[#A3A3A3] mt-0.5 leading-relaxed">
              Returned in HTTP response headers alongside the execution result as cryptographic receipt of verified settlement.
            </p>
          </div>
        </div>
      </div>

      {/* 2. Code Example: Seller Challenge Response */}
      <div className="bg-[#111111] p-5 rounded-xl border border-[rgba(255, 255, 255,0.16)] space-y-3 text-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code2 className="w-3.5 h-3.5 text-[#FFFFFF]" />
            <h3 className="font-semibold text-[#FAFAFA] text-xs">Testing HTTP 402 Endpoint Challenge</h3>
          </div>
          <button
            onClick={() => copySnippet(curlChallengeSnippet, 'curl')}
            className="flex items-center gap-1 text-[#A3A3A3] hover:text-[#FFFFFF] transition-colors cursor-pointer text-xs"
          >
            {copiedSection === 'curl' ? <Check className="w-3 h-3 text-[#A3A3A3]" /> : <Copy className="w-3 h-3" />}
            <span>{copiedSection === 'curl' ? 'Copied' : 'Copy cURL'}</span>
          </button>
        </div>

        <pre className="p-3 rounded-lg bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.16)] text-[#FAFAFA] font-mono text-[11px] overflow-x-auto leading-relaxed">
          {curlChallengeSnippet}
        </pre>

        <div className="pt-1 space-y-1">
          <span className="text-[11px] text-[#A3A3A3] block">Expected 402 Response:</span>
          <pre className="p-3 rounded-lg bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.16)] text-[#FFFFFF] font-mono text-[11px] overflow-x-auto leading-relaxed">
            {headerResponseSnippet}
          </pre>
        </div>
      </div>

      {/* 3. Python Orchestrator SDK Usage */}
      <div className="bg-[#111111] p-5 rounded-xl border border-[rgba(255, 255, 255,0.16)] space-y-3 text-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-[#A3A3A3]" />
            <h3 className="font-semibold text-[#FAFAFA] text-xs">Buyer Agent Python Orchestrator SDK</h3>
          </div>
          <button
            onClick={() => copySnippet(pythonBuyerSnippet, 'python')}
            className="flex items-center gap-1 text-[#A3A3A3] hover:text-[#A3A3A3] transition-colors cursor-pointer text-xs"
          >
            {copiedSection === 'python' ? <Check className="w-3 h-3 text-[#A3A3A3]" /> : <Copy className="w-3 h-3" />}
            <span>{copiedSection === 'python' ? 'Copied' : 'Copy Code'}</span>
          </button>
        </div>

        <pre className="p-3 rounded-lg bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.16)] text-[#FAFAFA] font-mono text-[11px] overflow-x-auto leading-relaxed">
          {pythonBuyerSnippet}
        </pre>
      </div>

      {/* 4. Live REST Endpoints Table */}
      <div className="bg-[#111111] p-5 rounded-xl border border-[rgba(255, 255, 255,0.16)] space-y-3">
        <h3 className="font-semibold text-[#FAFAFA] text-xs">FastAPI Endpoints Reference</h3>

        <div className="space-y-2 text-xs">
          <div className="p-3 rounded-lg bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.14)] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 rounded bg-[rgba(163, 163, 163,0.12)] text-[#A3A3A3] font-mono text-[11px] font-medium">GET</span>
              <span className="text-[#FAFAFA] font-mono text-[11px]">/api/v1/services</span>
            </div>
            <span className="text-[#A3A3A3] text-[11px]">Query active registered seller microservices</span>
          </div>

          <div className="p-3 rounded-lg bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.14)] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 rounded bg-[rgba(255, 255, 255,0.12)] text-[#FFFFFF] font-mono text-[11px] font-medium">POST</span>
              <span className="text-[#FAFAFA] font-mono text-[11px]">/api/v1/buyer/tasks</span>
            </div>
            <span className="text-[#A3A3A3] text-[11px]">Submit prompt and budget for autonomous multi-step execution</span>
          </div>

          <div className="p-3 rounded-lg bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.14)] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 rounded bg-[rgba(163, 163, 163,0.12)] text-[#A3A3A3] font-mono text-[11px] font-medium">GET</span>
              <span className="text-[#FAFAFA] font-mono text-[11px]">/api/v1/ledger</span>
            </div>
            <span className="text-[#A3A3A3] text-[11px]">Query immutable payment ledger audit records</span>
          </div>

          <div className="p-3 rounded-lg bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.14)] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 rounded bg-[rgba(163, 163, 163,0.12)] text-[#A3A3A3] font-mono text-[11px] font-medium">GET</span>
              <span className="text-[#FAFAFA] font-mono text-[11px]">/api/v1/reputation</span>
            </div>
            <span className="text-[#A3A3A3] text-[11px]">Fetch calculated trust scores, total calls, and median latencies</span>
          </div>
        </div>
      </div>
    </div>
  );
};
