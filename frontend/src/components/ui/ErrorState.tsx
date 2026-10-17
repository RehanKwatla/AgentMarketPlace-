import React from 'react';
import { AlertCircle, RotateCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Service Unavailable',
  message,
  onRetry,
  className = '',
}) => {
  return (
    <div className={`p-4 rounded-xl bg-[#FDE8E8] border border-[#F8B4B4] text-[#7D292D] text-xs font-mono flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs ${className}`}>
      <div className="flex items-start gap-2.5">
        <AlertCircle className="w-4 h-4 text-[#B84040] shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-[#7D292D] block font-sans">{title}</span>
          <p className="text-[11px] text-[#7D292D]/80 mt-0.5 font-sans">{message}</p>
        </div>
      </div>

      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 rounded-lg bg-[#7D292D] hover:bg-[#612024] text-[#F7F4EE] text-xs font-mono border border-[#612024] transition-colors flex items-center gap-1.5 self-start sm:self-auto cursor-pointer shadow-xs"
        >
          <RotateCw className="w-3.5 h-3.5" />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
};
export default ErrorState;
