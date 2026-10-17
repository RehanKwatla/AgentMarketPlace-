import React from 'react';

interface SkeletonProps {
  /** Tailwind sizing classes, e.g. "h-3 w-24" */
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = 'h-3 w-24' }) => (
  <span aria-hidden="true" className={`skeleton-block block ${className}`} />
);

/**
 * Placeholder that mirrors the geometry of a Dashboard metric card so the
 * layout does not shift when real values arrive.
 */
export const MetricCardSkeleton: React.FC = () => (
  <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-5 flex flex-col justify-between space-y-4">
    <div className="flex items-center justify-between">
      <Skeleton className="h-3 w-28" />
      <Skeleton className="h-7 w-7 rounded-md" />
    </div>
    <div className="space-y-2">
      <Skeleton className="h-8 w-24" />
      <Skeleton className="h-2.5 w-40" />
    </div>
    <div className="pt-2 border-t border-[#CFC7BB]/60 flex items-center justify-between">
      <Skeleton className="h-2.5 w-24" />
      <Skeleton className="h-2.5 w-10" />
    </div>
  </div>
);

/** Row placeholder used by activity lists on the Dashboard. */
export const ActivityRowSkeleton: React.FC = () => (
  <div className="p-3.5 flex items-center justify-between gap-3" aria-hidden="true">
    <div className="space-y-2 min-w-0 flex-1">
      <Skeleton className="h-3 w-40" />
      <Skeleton className="h-2.5 w-56" />
      <Skeleton className="h-2.5 w-28" />
    </div>
    <Skeleton className="h-4 w-20" />
  </div>
);

export default Skeleton;
