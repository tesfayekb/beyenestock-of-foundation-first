import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle } from 'lucide-react';

interface RegimePanelProps {
  regime: string | null;
  rcs: number | null;
  regimeAgreement: boolean | null;
  allocationTier: string | null;
}

function regimeBadgeClass(regime: string | null): string {
  if (!regime) return 'bg-muted text-muted-foreground border-border';
  const r = regime.toLowerCase();
  if (r.includes('bull')) return 'bg-success/10 text-success border-success/20';
  if (r.includes('bear')) return 'bg-destructive/10 text-destructive border-destructive/20';
  if (r.includes('range') || r.includes('pin'))
    return 'bg-blue-500/10 text-blue-600 border-blue-500/20';
  if (r.includes('crisis') || r.includes('volatile'))
    return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
  return 'bg-muted text-muted-foreground border-border';
}

function rcsBarClass(rcs: number): string {
  if (rcs >= 80) return 'bg-success';
  if (rcs >= 60) return 'bg-blue-500';
  if (rcs >= 40) return 'bg-amber-500';
  return 'bg-destructive';
}

export function RegimePanel({
  regime,
  rcs,
  regimeAgreement,
  allocationTier,
}: RegimePanelProps) {
  const rcsValue = rcs ?? 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Regime</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={`text-base px-3 py-1 font-semibold capitalize ${regimeBadgeClass(regime)}`}
          >
            {regime ?? 'Unknown'}
          </Badge>
        </div>

        {regimeAgreement === false && (
          <Alert className="border-amber-500/30 bg-amber-500/10 py-2">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-700 text-xs font-medium">
              Regime disagreement — size reduced 50%
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">RCS Score</span>
            <span className="font-mono font-semibold">{rcsValue.toFixed(0)}</span>
          </div>
          <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${rcsBarClass(rcsValue)}`}
              style={{ width: `${Math.min(100, Math.max(0, rcsValue))}%` }}
            />
          </div>
        </div>

        {allocationTier && (
          <Badge variant="outline" className="text-xs">
            Tier: {allocationTier}
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}
