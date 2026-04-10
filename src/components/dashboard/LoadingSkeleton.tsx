import { cn } from '@/lib/utils';

interface LoadingSkeletonProps {
  /** Number of skeleton rows to render */
  rows?: number;
  /** Variant shape */
  variant?: 'table' | 'card' | 'page';
  className?: string;
}

function SkeletonLine({ className }: { className?: string }) {
  return <div className={cn('h-4 rounded-md bg-muted animate-pulse', className)} />;
}

function TableSkeleton({ rows }: { rows: number }) {
  return (
    <div className="rounded-lg border border-border">
      {/* Header */}
      <div className="flex gap-4 bg-muted/50 px-4 py-3">
        <SkeletonLine className="h-3 w-24" />
        <SkeletonLine className="h-3 w-32" />
        <SkeletonLine className="h-3 w-20" />
        <SkeletonLine className="h-3 w-16" />
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 border-t px-4 py-3">
          <SkeletonLine className="h-4 w-24" />
          <SkeletonLine className="h-4 w-32" />
          <SkeletonLine className="h-4 w-20" />
          <SkeletonLine className="h-4 w-16" />
        </div>
      ))}
    </div>
  );
}

function CardSkeleton({ rows }: { rows: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="rounded-lg border p-6 space-y-3">
          <SkeletonLine className="h-3 w-20" />
          <SkeletonLine className="h-6 w-16" />
        </div>
      ))}
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <SkeletonLine className="h-8 w-48" />
        <SkeletonLine className="h-4 w-64" />
      </div>
      <CardSkeleton rows={4} />
      <TableSkeleton rows={5} />
    </div>
  );
}

export function LoadingSkeleton({ rows = 5, variant = 'table', className }: LoadingSkeletonProps) {
  return (
    <div className={className}>
      {variant === 'table' && <TableSkeleton rows={rows} />}
      {variant === 'card' && <CardSkeleton rows={rows} />}
      {variant === 'page' && <PageSkeleton />}
    </div>
  );
}
