import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface CapitalPreservationStatusProps {
  consecutiveLossesToday: number | null;
  capitalPreservationActive: boolean | null;
  virtualTradesCount: number | null;
}

export function CapitalPreservationStatus({
  consecutiveLossesToday,
  capitalPreservationActive,
  virtualTradesCount,
}: CapitalPreservationStatusProps) {
  const losses = consecutiveLossesToday ?? 0;
  const MAX_LOSSES = 5;
  const isHalted = losses >= MAX_LOSSES;
  const isSizeReduced = losses >= 3 && !isHalted;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Capital Preservation</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">Consecutive Losses</p>
          <div className="flex items-center gap-1.5">
            {Array.from({ length: MAX_LOSSES }).map((_, i) => (
              <span
                key={i}
                className={`h-3 w-3 rounded-full border transition-colors ${
                  i < losses
                    ? 'bg-destructive border-destructive'
                    : 'bg-muted border-border'
                }`}
              />
            ))}
            <span className="ml-2 text-sm font-mono font-semibold">
              {losses} / {MAX_LOSSES}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {isHalted && (
            <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20">
              Session halted
            </Badge>
          )}
          {isSizeReduced && (
            <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/20">
              Size reduced 50%
            </Badge>
          )}
          {capitalPreservationActive && !isHalted && !isSizeReduced && (
            <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/20">
              Capital preservation active
            </Badge>
          )}
        </div>

        <p className="text-xs text-muted-foreground">
          Virtual trades today:{' '}
          <span className="font-mono font-semibold text-foreground">
            {virtualTradesCount ?? 0}
          </span>
        </p>
      </CardContent>
    </Card>
  );
}
