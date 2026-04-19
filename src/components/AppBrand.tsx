import { TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AppBrandProps {
  appName?: string;
  showName?: boolean;
  className?: string;
}

export function AppBrand({
  appName = "Beyene Quant",
  showName = true,
  className,
}: AppBrandProps) {
  return (
    <div className={cn('flex items-center gap-2 min-w-0', className)}>
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <TrendingUp className="h-4 w-4" strokeWidth={2.5} />
      </div>
      {showName && (
        <span className="truncate font-display text-sm font-semibold">
          {appName}
        </span>
      )}
    </div>
  );
}
