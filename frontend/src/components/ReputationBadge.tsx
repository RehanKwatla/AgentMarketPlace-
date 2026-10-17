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

  const s = String(status).toLowerCase().trim();

  if (s === 'verified on-chain') {
    badgeStyle = 'bg-[rgba(163, 163, 163,0.15)] text-[#FAFAFA] border-[rgba(255, 255, 255,0.4)]';
    dotStyle = 'bg-[#FFFFFF]';
    label = 'Verified On-Chain';
  } else if (s === 'verified facilitator receipt') {
    badgeStyle = 'bg-[rgba(163, 163, 163,0.12)] text-[#A3A3A3] border-[rgba(163, 163, 163,0.3)]';
    dotStyle = 'bg-[#A3A3A3]';
    label = 'Verified Facilitator Receipt';
  } else if (s === 'simulated' || s === 'simulated settlement') {
    badgeStyle = 'bg-[rgba(115, 115, 115,0.15)] text-[#A3A3A3] border-[rgba(115, 115, 115,0.3)]';
    dotStyle = 'bg-[#737373]';
    label = 'Simulated Settlement';
  } else if (s === 'paid' || s === 'completed') {
    badgeStyle = 'bg-[rgba(163, 163, 163,0.12)] text-[#A3A3A3] border-[rgba(163, 163, 163,0.3)]';
    dotStyle = 'bg-[#A3A3A3]';
    label = 'Verified Paid / Settled';
  } else if (s === 'paid output rejected' || s === 'paid_output_rejected') {
    badgeStyle = 'bg-[rgba(163, 163, 163,0.12)] text-[#A3A3A3] border-[rgba(163, 163, 163,0.3)]';
    dotStyle = 'bg-[#A3A3A3]';
    label = 'Paid / Output Rejected';
  } else if (s === 'refused') {
    badgeStyle = 'bg-[rgba(115, 115, 115,0.12)] text-[#737373] border-[rgba(115, 115, 115,0.3)]';
    dotStyle = 'bg-[#737373]';
    label = 'Refused Before Payment';
  } else if (s === 'failed and not charged' || s === 'failed_and_not_charged') {
    badgeStyle = 'bg-[#141414] text-[#737373] border-[rgba(255, 255, 255,0.20)]';
    dotStyle = 'bg-[#737373]';
    label = 'Failed / Not Charged';
  } else if (s === 'pending reconciliation' || s === 'pending_reconciliation') {
    badgeStyle = 'bg-[rgba(255, 255, 255,0.12)] text-[#FFFFFF] border-[rgba(255, 255, 255,0.3)]';
    dotStyle = 'bg-[#FFFFFF] animate-pulse';
    label = 'Pending Reconciliation';
  } else if (s === 'pending' || s === 'in_progress') {
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
