import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  subtext?: string;
  minHeight?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading data...',
  subtext,
  minHeight = 'min-h-[240px]',
}) => {
  return (
    <div className={`wallet-card rounded-xl border border-[#CFC7BB] p-8 flex flex-col items-center justify-center text-center ${minHeight} bg-[#F7F4EE] shadow-xs`}>
      <Loader2 className="w-8 h-8 text-[#7D292D] animate-spin mb-3" />
      <p className="text-sm font-medium text-[#241B19] font-sans">{message}</p>
      {subtext && (
        <p className="text-xs text-[#82786F] mt-1 font-mono max-w-sm">
          {subtext}
        </p>
      )}
    </div>
  );
};
export default LoadingState;
