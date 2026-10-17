import React, { ReactNode } from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
  minHeight?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  minHeight = 'min-h-[260px]',
}) => {
  return (
    <div className={`wallet-card rounded-xl border border-[#CFC7BB] p-8 flex flex-col items-center justify-center text-center ${minHeight} space-y-3 bg-[#F7F4EE] shadow-xs`}>
      <div className="w-12 h-12 rounded-xl bg-[#DED8CD]/60 border border-[#CFC7BB] flex items-center justify-center text-[#82786F] mb-1">
        {icon || <Inbox className="w-6 h-6" />}
      </div>
      <div className="space-y-1 max-w-sm">
        <h3 className="text-sm font-semibold text-[#241B19] font-sans">{title}</h3>
        <p className="text-xs text-[#82786F] leading-relaxed font-sans">{description}</p>
      </div>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
};
export default EmptyState;
