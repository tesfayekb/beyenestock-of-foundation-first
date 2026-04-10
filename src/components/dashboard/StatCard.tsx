import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: { value: string; direction: 'up' | 'down' | 'neutral' };
  className?: string;
}

export function StatCard({ title, value, icon: Icon, trend, className }: StatCardProps) {
  const TrendIcon = trend?.direction === 'up' ? TrendingUp : trend?.direction === 'down' ? TrendingDown : Minus;

  return (
    <Card className={cn('shadow-sm', className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {title}
            </p>
            <p className="font-display text-2xl font-bold">{value}</p>
          </div>
          <div className="rounded-lg bg-muted p-3">
            <Icon className="h-5 w-5 text-muted-foreground" />
          </div>
        </div>
        {trend && (
          <div className="mt-3 flex items-center gap-1 text-xs">
            <TrendIcon className={cn(
              'h-3 w-3',
              trend.direction === 'up' && 'text-success',
              trend.direction === 'down' && 'text-destructive',
              trend.direction === 'neutral' && 'text-muted-foreground',
            )} />
            <span className={cn(
              trend.direction === 'up' && 'text-success',
              trend.direction === 'down' && 'text-destructive',
              trend.direction === 'neutral' && 'text-muted-foreground',
            )}>
              {trend.value}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
