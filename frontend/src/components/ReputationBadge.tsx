import React from 'react';
import { LedgerStatus } from '../types';

interface StatusBadgeProps {
  status: LedgerStatus | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'sm' }) => {
  let badgeStyle = 'bg-slate-800/80 text-slate-300 border-slate-700/60';
  let dotStyle = 'bg-slate-400';
  let label = status;

  if (status === 'paid' || status === 'completed') {
    badgeStyle = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    dotStyle = 'bg-emerald-400 shadow-sm shadow-emerald-500/50';
    label = 'Verified Paid / Settled';
  } else if (status === 'paid output rejected') {
    badgeStyle = 'bg-amber-500/10 text-amber-300 border-amber-500/30';
    dotStyle = 'bg-amber-400';
    label = 'Paid (Output Rejected)';
  } else if (status === 'refused') {
    badgeStyle = 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    dotStyle = 'bg-rose-400';
    label = 'Refused Before Payment';
  } else if (status === 'failed and not charged') {
    badgeStyle = 'bg-slate-800 text-slate-400 border-slate-700';
    dotStyle = 'bg-slate-500';
    label = 'Failed (No Charge)';
  } else if (status === 'pending' || status === 'in_progress') {
    badgeStyle = 'bg-blue-500/10 text-blue-400 border-blue-500/30';
    dotStyle = 'bg-blue-400 animate-ping';
    label = 'Reconciling / In Flight';
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-mono font-medium border transition-colors ${badgeStyle} ${sizeClasses}`}
      title={`Contract Status: ${status}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotStyle}`} />
      <span>{label}</span>
    </span>
  );
};
