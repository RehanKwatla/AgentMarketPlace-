import React, { useState } from 'react';
import { Copy, Check, Terminal } from 'lucide-react';

export const IntegrationBanner: React.FC = () => {
  const [copied, setCopied] = useState(false);
  const command = 'npx agentic-market install --network base-sepolia';

  const handleCopy = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="wallet-card rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono border border-[rgba(120,160,153,0.20)]">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-[#141A19] border border-[rgba(54,214,200,0.3)] flex items-center justify-center shrink-0 text-[#36D6C8]">
          <Terminal className="w-4 h-4" />
        </div>
        <div>
          <span className="font-bold text-[#F4F7F6] font-sans text-sm">Install the Agentic Market Skill</span>
          <span className="text-[#A0AAA7] ml-2 hidden lg:inline font-sans text-xs">
            Run once in your agent runtime to enable autonomous x402 discovery and payment settlement.
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="bg-[#0D1111] border border-[rgba(120,160,153,0.20)] rounded-lg px-3 py-1.5 text-[#F4F7F6] text-[11px] truncate max-w-xs sm:max-w-md font-mono">
          {command}
        </div>
        <button
          onClick={handleCopy}
          className="px-3.5 py-1.5 rounded-lg bg-[#36D6C8] hover:bg-[#53E3D6] text-[#0B0D0D] font-bold text-xs flex items-center gap-1.5 shrink-0 transition-all cursor-pointer shadow-sm shadow-[#36D6C8]/20"
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
    </div>
  );
};
