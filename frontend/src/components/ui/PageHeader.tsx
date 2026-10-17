import React, { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  badge?: ReactNode;
  actions?: ReactNode;
  icon?: ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  badge,
  actions,
  icon,
}) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#CFC7BB]">
      <div className="space-y-1">
        <div className="flex items-center gap-2.5">
          {icon && <span className="text-[#7D292D] shrink-0">{icon}</span>}
          <h1 className="text-2xl sm:text-3xl font-serif font-bold tracking-tight text-[#241B19]">
            {title}
          </h1>
          {badge}
        </div>
        {description && (
          <p className="text-xs text-[#82786F] font-sans leading-relaxed">
            {description}
          </p>
        )}
      </div>

      {actions && (
        <div className="flex items-center gap-2 shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
};
export default PageHeader;
