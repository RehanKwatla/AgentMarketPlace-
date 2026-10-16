import React from 'react';
import { LedgerStatus } from '../types';

interface StatusBadgeProps {
  status: LedgerStatus | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm' }) => {
  let badgeStyle = 'bg-[#141A19] text-[#A0AAA7] border-[rgba(120,160,153,0.20)]';
  let dotStyle = 'bg-[#6F7C78]';
  let label = status;

  if (status === 'paid' || status === 'completed') {
    badgeStyle = 'bg-[rgba(66,201,149,0.12)] text-[#42C995] border-[rgba(66,201,149,0.3)]';
    dotStyle = 'bg-[#42C995]';
    label = 'Verified Paid / Settled';
  } else if (status === 'paid output rejected') {
    badgeStyle = 'bg-[rgba(231,185,106,0.12)] text-[#E7B96A] border-[rgba(231,185,106,0.3)]';
    dotStyle = 'bg-[#E7B96A]';
    label = 'Paid (Output Rejected)';
  } else if (status === 'refused') {
    badgeStyle = 'bg-[rgba(225,109,109,0.12)] text-[#E16D6D] border-[rgba(225,109,109,0.3)]';
    dotStyle = 'bg-[#E16D6D]';
    label = 'Refused Before Payment';
  } else if (status === 'failed and not charged') {
    badgeStyle = 'bg-[#141A19] text-[#6F7C78] border-[rgba(120,160,153,0.20)]';
    dotStyle = 'bg-[#6F7C78]';
    label = 'Failed (No Charge)';
  } else if (status === 'pending' || status === 'in_progress') {
    badgeStyle = 'bg-[rgba(54,214,200,0.12)] text-[#36D6C8] border-[rgba(54,214,200,0.3)]';
    dotStyle = 'bg-[#36D6C8] animate-ping';
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
