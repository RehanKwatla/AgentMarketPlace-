import React from 'react';
import { LedgerStatus } from '../types';

interface StatusBadgeProps {
  status: LedgerStatus | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  let badgeStyle = 'bg-slate-800 text-slate-300 border-slate-700';

  if (status === 'paid') {
    badgeStyle = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
  } else if (status === 'paid output rejected') {
    badgeStyle = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  } else if (status === 'refused') {
    badgeStyle = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
  } else if (status === 'failed and not charged') {
    badgeStyle = 'bg-slate-700/50 text-slate-400 border-slate-600/30';
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium border ${badgeStyle}`}>
      {status}
    </span>
  );
};
