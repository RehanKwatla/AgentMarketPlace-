import React from 'react';
import { ArrowRight, Sparkles } from 'lucide-react';

interface HeroSectionProps {
  onExplore: () => void;
  onPublish: () => void;
  serviceCount: number;
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onExplore,
  onPublish
}) => {
  return (
    <section className="pt-8 pb-4 text-center max-w-3xl mx-auto">
      {/* Restrained Status Tag */}
      <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#121212] border border-[rgba(255, 255, 255,0.2)] text-xs text-[#A3A3A3] mb-4">
        <span className="w-1.5 h-1.5 rounded-full bg-[#FFFFFF]" />
        <span>Base Sepolia</span>
        <span className="text-[#737373]">·</span>
        <span className="font-mono text-[11px]">x402 v2</span>
      </div>

      {/* Clean Heading - Inter Semibold */}
      <h1 className="text-3xl sm:text-4xl md:text-5xl font-semibold tracking-tight text-[#FAFAFA] leading-tight">
        Pay-Per-Call Autonomous <span className="text-[#FFFFFF]">Agent Economy</span>
      </h1>

      {/* Concise Description */}
      <p className="mt-3 text-sm sm:text-base text-[#A3A3A3] leading-relaxed max-w-xl mx-auto">
        Discover, integrate, and pay for AI microservices with verified x402 testnet settlement. Zero API keys.
      </p>

      {/* Action Buttons */}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3 text-xs">
        <button
          onClick={onExplore}
          className="px-4 py-2 rounded-md bg-[#FFFFFF] hover:bg-[#E5E5E5] text-[#0A0A0A] font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
        >
          <span>Explore Marketplace</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={onPublish}
          className="px-4 py-2 rounded-md bg-[#171717] hover:bg-[#1C1C1C] text-[#FAFAFA] hover:text-[#FFFFFF] border border-[rgba(255, 255, 255,0.22)] font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5 text-[#FFFFFF]" />
          <span>Launch Buyer Agent</span>
        </button>
      </div>
    </section>
  );
};
