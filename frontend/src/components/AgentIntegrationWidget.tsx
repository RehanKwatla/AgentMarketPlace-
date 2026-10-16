import React, { useState } from 'react';
import { Terminal, Copy, Check, ExternalLink, Code2 } from 'lucide-react';

export const AgentIntegrationWidget: React.FC = () => {
  const [copied, setCopied] = useState(false);

  const snippet = `import requests

# 1. Call any registered service endpoint
response = requests.post(
    "http://localhost:8000/api/v1/seller/data",
    json={"symbol": "ETH"}
)

# 2. Inspect x402 challenge header
if response.status_code == 402:
    requirement = response.headers.get("X-402-Requirement")
    print(f"Payment Required via x402: {requirement}")

    # 3. Supply signed EIP-712 payload for Base Sepolia USDC
    # headers={"X-402-Payment-Payload": payment_json}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-slate-800 bg-slate-900/60 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center">
            <Code2 className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white font-sans">Connect Your Agent</h3>
            <p className="text-xs text-slate-400">Discover and purchase services programmatically using standard HTTP 402</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-colors border border-slate-700"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
            <span>{copied ? 'Copied' : 'Copy Code'}</span>
          </button>
        </div>
      </div>

      <div className="relative rounded-xl overflow-hidden bg-slate-950 border border-slate-800">
        <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800/80 bg-slate-900/80 text-[11px] font-mono text-slate-400">
          <span className="flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-blue-400" />
            <span>python_client.py</span>
          </span>
          <span className="text-[10px] text-slate-500 uppercase">Base Sepolia USDC</span>
        </div>
        <pre className="p-4 text-xs font-mono text-slate-300 overflow-x-auto leading-relaxed">
          {snippet}
        </pre>
      </div>

      <div className="flex items-center justify-between text-xs text-slate-400 font-sans pt-1">
        <span>No API keys or vendor accounts required. Micropayments settle automatically per call.</span>
        <a 
          href="/docs" 
          target="_blank" 
          rel="noopener noreferrer" 
          className="text-blue-400 hover:underline inline-flex items-center gap-1 font-mono text-[11px]"
        >
          <span>FastAPI Specs</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
};
