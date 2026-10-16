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
    <div className="bg-[#171819] border border-[#303133] rounded-lg p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 rounded bg-[#FF982E]/10 border border-[#FF982E]/30 flex items-center justify-center shrink-0">
          <Terminal className="w-3.5 h-3.5 text-[#FF982E]" />
        </div>
        <div>
          <span className="font-bold text-[#F5F5F5] font-sans">Install the Agentic Market skill.</span>
          <span className="text-[#96989D] ml-2 hidden lg:inline">Paste once. Your agent can discover and pay for services.</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="bg-[#101112] border border-[#303133] rounded px-3 py-1.5 text-[#F5F5F5] text-[11px] truncate max-w-xs sm:max-w-md">
          {command}
        </div>
        <button
          onClick={handleCopy}
          className="px-3 py-1.5 rounded bg-[#FF982E] hover:bg-[#FF982E]/90 text-[#101112] font-bold text-xs flex items-center gap-1 shrink-0 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
    </div>
  );
};
