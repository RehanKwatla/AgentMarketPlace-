import React, { useState, useRef, useEffect } from 'react';
import { 
  Copy, 
  Check, 
  ChevronDown, 
  ExternalLink, 
  ShieldCheck, 
  RotateCcw
} from 'lucide-react';

import { useMarketplace } from '../../context/MarketplaceContext';

export const ProfileMenu: React.FC = () => {
  const { healthInfo, paymentStatus, refreshData } = useMarketplace();
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const address = '0x71C83eB5187A24B9E38Ea47e62a26c04f901139B';
  const shortAddress = `${address.slice(0, 6)}...${address.slice(-4)}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const isConnected = healthInfo?.status === 'healthy';

  return (
    <div className="relative font-mono" ref={menuRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="flex items-center gap-2 p-1 pl-2 pr-2.5 rounded-lg bg-[#FFFFFF] hover:bg-[#DED8CD]/60 border border-[#CFC7BB] text-xs text-[#241B19] transition-colors cursor-pointer select-none shadow-sm"
      >
        {/* Generative Avatar */}
        <div className="w-6 h-6 rounded-md bg-gradient-to-tr from-[#7D292D] to-[#612024] flex items-center justify-center text-[#F7F4EE] font-bold text-[11px] shadow-sm">
          0x
        </div>

        <div className="hidden sm:flex flex-col text-left">
          <span className="text-[11px] font-semibold text-[#241B19] leading-tight">
            {shortAddress}
          </span>
          <span className="text-[9px] text-[#82786F] leading-none">
            Buyer Account
          </span>
        </div>

        <ChevronDown className={`w-3.5 h-3.5 text-[#82786F] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 rounded-xl bg-[#F7F4EE] border border-[#CFC7BB] shadow-xl p-3 z-50 space-y-3 text-xs animate-in fade-in zoom-in-95 duration-100">
          {/* Account Details Header */}
          <div className="p-2.5 rounded-lg bg-[#DED8CD]/50 border border-[#CFC7BB] space-y-1.5">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#82786F]">Connected Wallet</span>
              <span className="flex items-center gap-1 text-[#38865B] font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-[#38865B] animate-pulse" />
                Base Sepolia
              </span>
            </div>

            <div className="flex items-center justify-between font-mono bg-[#FFFFFF] p-1.5 rounded border border-[#CFC7BB]">
              <span className="text-[#241B19] text-[11px] truncate">{shortAddress}</span>
              <button
                onClick={handleCopy}
                className="p-1 text-[#82786F] hover:text-[#241B19] transition-colors"
                title="Copy full address"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-[#38865B]" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Testnet Balance Details */}
          <div className="px-1 space-y-1">
            <div className="flex justify-between py-1 text-[11px] text-[#82786F]">
              <span>Testnet Allowance:</span>
              <span className="text-[#241B19] font-bold">100.00 USDC</span>
            </div>
            <div className="flex justify-between py-1 text-[11px] text-[#82786F]">
              <span>Backend Connectivity:</span>
              <span className={isConnected ? 'text-[#38865B] font-semibold' : 'text-[#B84040] font-semibold'}>
                {isConnected ? 'Connected (:8000)' : 'Offline'}
              </span>
            </div>
            <div className="flex justify-between py-1 text-[11px] text-[#82786F]">
              <span>x402 Protocol:</span>
              <span className="text-[#241B19]">
                v{paymentStatus?.protocol_version || '2.0'}
              </span>
            </div>
          </div>

          <div className="border-t border-[#CFC7BB] pt-2 space-y-1">
            <button
              onClick={() => {
                refreshData();
                setIsOpen(false);
              }}
              className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-[#DED8CD]/60 text-[#241B19] flex items-center gap-2 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5 text-[#82786F]" />
              <span>Resync Network State</span>
            </button>

            <a
              href="https://sepolia.basescan.org"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-[#DED8CD]/60 text-[#82786F] hover:text-[#241B19] flex items-center justify-between transition-colors"
            >
              <span className="flex items-center gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-[#82786F]" />
                <span>Base Sepolia Explorer</span>
              </span>
              <ExternalLink className="w-3 h-3 text-[#82786F]" />
            </a>
          </div>
        </div>
      )}
    </div>
  );
};
export default ProfileMenu;
