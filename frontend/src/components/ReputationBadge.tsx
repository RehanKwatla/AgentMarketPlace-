import React from 'react';
import { LedgerStatus } from '../types';

interface StatusBadgeProps {
  status: LedgerStatus | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm' }) => {
  let badgeStyle = 'bg-[#202123] text-[#A0A1A5] border-[#303133]';
  let dotStyle = 'bg-[#777980]';
  let label = status;

  if (status === 'paid' || status === 'completed') {
    badgeStyle = 'bg-[#58B779]/10 text-[#58B779] border-[#58B779]/30';
    dotStyle = 'bg-[#58B779]';
    label = 'Verified Paid / Settled';
  } else if (status === 'paid output rejected') {
    badgeStyle = 'bg-[#FF982E]/10 text-[#FF982E] border-[#FF982E]/30';
    dotStyle = 'bg-[#FF982E]';
    label = 'Paid (Output Rejected)';
  } else if (status === 'refused') {
    badgeStyle = 'bg-[#E15D52]/10 text-[#E15D52] border-[#E15D52]/30';
    dotStyle = 'bg-[#E15D52]';
    label = 'Refused Before Payment';
  } else if (status === 'failed and not charged') {
    badgeStyle = 'bg-[#202123] text-[#777980] border-[#303133]';
    dotStyle = 'bg-[#777980]';
    label = 'Failed (No Charge)';
  } else if (status === 'pending' || status === 'in_progress') {
    badgeStyle = 'bg-[#FF982E]/10 text-[#FF982E] border-[#FF982E]/30';
    dotStyle = 'bg-[#FF982E] animate-ping';
    label = 'Reconciling / In Flight';
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded font-mono font-medium border transition-colors ${badgeStyle} ${sizeClasses}`}
      title={`Contract Status: ${status}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotStyle}`} />
      <span>{label}</span>
    </span>
  );
};
