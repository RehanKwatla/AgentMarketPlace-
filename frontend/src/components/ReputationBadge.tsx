import React from 'react';
import { LedgerStatus } from '../types';

interface StatusBadgeProps {
  status: LedgerStatus | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm' }) => {
  let badgeStyle = 'bg-[#141414] text-[#A3A3A3] border-[rgba(255, 255, 255,0.20)]';
  let dotStyle = 'bg-[#737373]';
  let label = status;

  if (status === 'paid' || status === 'completed') {
    badgeStyle = 'bg-[rgba(163, 163, 163,0.12)] text-[#A3A3A3] border-[rgba(163, 163, 163,0.3)]';
    dotStyle = 'bg-[#A3A3A3]';
    label = 'Verified Paid / Settled';
  } else if (status === 'paid output rejected') {
    badgeStyle = 'bg-[rgba(163, 163, 163,0.12)] text-[#A3A3A3] border-[rgba(163, 163, 163,0.3)]';
    dotStyle = 'bg-[#A3A3A3]';
    label = 'Paid (Output Rejected)';
  } else if (status === 'refused') {
    badgeStyle = 'bg-[rgba(115, 115, 115,0.12)] text-[#737373] border-[rgba(115, 115, 115,0.3)]';
    dotStyle = 'bg-[#737373]';
    label = 'Refused Before Payment';
  } else if (status === 'failed and not charged') {
    badgeStyle = 'bg-[#141414] text-[#737373] border-[rgba(255, 255, 255,0.20)]';
    dotStyle = 'bg-[#737373]';
    label = 'Failed (No Charge)';
  } else if (status === 'pending' || status === 'in_progress') {
    badgeStyle = 'bg-[rgba(255, 255, 255,0.12)] text-[#FFFFFF] border-[rgba(255, 255, 255,0.3)]';
    dotStyle = 'bg-[#FFFFFF] animate-ping';
    label = 'Reconciling / In Flight';
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md font-mono font-medium border transition-colors ${badgeStyle} ${sizeClasses}`}
      title={`Contract Status: ${status}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotStyle}`} />
      <span>{label}</span>
    </span>
  );
};
