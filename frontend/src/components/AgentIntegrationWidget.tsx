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
    <div className="p-6 rounded-2xl border border-[#CFC7BB] bg-[#F7F4EE] space-y-4 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#7D292D] text-[#F7F4EE] flex items-center justify-center">
            <Code2 className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#241B19] font-serif">Connect Your Agent</h3>
            <p className="text-xs text-[#82786F]">Discover and purchase services programmatically using standard HTTP 402</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 text-[#241B19] text-xs font-mono transition-colors border border-[#CFC7BB] shadow-sm cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-[#38865B]" /> : <Copy className="w-3.5 h-3.5 text-[#82786F]" />}
            <span>{copied ? 'Copied' : 'Copy Code'}</span>
          </button>
        </div>
      </div>

      <div className="relative rounded-xl overflow-hidden bg-[#FFFFFF] border border-[#CFC7BB] shadow-inner">
        <div className="flex items-center justify-between px-4 py-2 border-b border-[#CFC7BB] bg-[#DED8CD]/40 text-[11px] font-mono text-[#82786F]">
          <span className="flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-[#7D292D]" />
            <span className="text-[#241B19]">python_client.py</span>
          </span>
          <span className="text-[10px] text-[#82786F] uppercase">Base Sepolia USDC</span>
        </div>
        <pre className="p-4 text-xs font-mono text-[#241B19] overflow-x-auto leading-relaxed bg-[#FFFFFF]">
          {snippet}
        </pre>
      </div>

      <div className="flex items-center justify-between text-xs text-[#82786F] font-sans pt-1">
        <span>No API keys or vendor accounts required. Micropayments settle automatically per call.</span>
        <a 
          href="http://localhost:8000/docs" 
          target="_blank" 
          rel="noopener noreferrer" 
          className="text-[#7D292D] hover:underline inline-flex items-center gap-1 font-mono text-[11px]"
        >
          <span>FastAPI Specs</span>
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
};
