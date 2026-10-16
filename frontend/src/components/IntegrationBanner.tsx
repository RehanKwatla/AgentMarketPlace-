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
    <div className="wallet-card rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono border border-[rgba(255, 255, 255,0.20)]">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-[#141414] border border-[rgba(255, 255, 255,0.3)] flex items-center justify-center shrink-0 text-[#FFFFFF]">
          <Terminal className="w-4 h-4" />
        </div>
        <div>
          <span className="font-bold text-[#FAFAFA] font-sans text-sm">Install the Agentic Market Skill</span>
          <span className="text-[#A3A3A3] ml-2 hidden lg:inline font-sans text-xs">
            Run once in your agent runtime to enable autonomous x402 discovery and payment settlement.
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.20)] rounded-lg px-3 py-1.5 text-[#FAFAFA] text-[11px] truncate max-w-xs sm:max-w-md font-mono">
          {command}
        </div>
        <button
          onClick={handleCopy}
          className="px-3.5 py-1.5 rounded-lg bg-[#FFFFFF] hover:bg-[#D4D4D4] text-[#0A0A0A] font-bold text-xs flex items-center gap-1.5 shrink-0 transition-all cursor-pointer shadow-sm shadow-[#FFFFFF]/20"
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
    </div>
  );
};
