import React from 'react';
import { LedgerStatus } from '../../types';

interface StatusBadgeProps {
  status: LedgerStatus | 'operational' | 'offline' | 'pending' | 'completed' | 'refused' | 'failed' | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const norm = status.toLowerCase();

  let style = 'bg-[#DED8CD]/60 text-[#82786F] border-[#CFC7BB]';
  let dotColor = 'bg-[#82786F]';

  if (norm === 'paid' || norm === 'operational' || norm === 'completed' || norm === 'success') {
    style = 'bg-[#E4EFE8] text-[#38865B] border-[#A8B3A1]/70';
    dotColor = 'bg-[#38865B]';
  } else if (norm === 'paid output rejected' || norm === 'pending' || norm === 'pending_reconciliation') {
    style = 'bg-[#FBF2E5] text-[#A86E24] border-[#DED8CD]';
    dotColor = 'bg-[#A86E24]';
  } else if (norm === 'refused' || norm === 'failed and not charged' || norm === 'failed' || norm === 'offline') {
    style = 'bg-[#F4ECEB] text-[#7D292D] border-[#CFC7BB]';
    dotColor = 'bg-[#7D292D]';
  }

  const sizeClasses = size === 'sm' ? 'px-1.5 py-0.2 text-[10px]' : 'px-2 py-0.5 text-[11px]';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono rounded font-medium border shadow-xs ${sizeClasses} ${style}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      <span className="capitalize">{status}</span>
    </span>
  );
};
export default StatusBadge;
