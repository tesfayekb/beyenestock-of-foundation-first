import { type LucideIcon, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AppBrandProps {
  appName?: string;
  appIcon?: LucideIcon;
  showName?: boolean;
  className?: string;
}

export function AppBrand({
  appName = 'Foundation First',
  appIcon: Icon = Shield,
  showName = true,
  className,
}: AppBrandProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <Icon className="h-4 w-4" />
      </div>
      {showName && (
        <span className="truncate font-display text-sm font-semibold">
          {appName}
        </span>
      )}
    </div>
  );
}
