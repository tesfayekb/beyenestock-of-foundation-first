import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle } from 'lucide-react';

interface PredictionConfidenceProps {
  pBull: number | null;
  pBear: number | null;
  pNeutral: number | null;
  direction: string | null;
  confidence: number | null;
  noTradeSignal: boolean | null;
  noTradeReason: string | null;
}

function directionBadgeClass(direction: string | null): string {
  if (!direction) return 'bg-muted text-muted-foreground border-border';
  const d = direction.toLowerCase();
  if (d === 'bull' || d === 'bullish') return 'bg-success/10 text-success border-success/20';
  if (d === 'bear' || d === 'bearish') return 'bg-destructive/10 text-destructive border-destructive/20';
  return 'bg-muted text-muted-foreground border-border';
}

interface ProbBarProps {
  label: string;
  value: number | null;
  barClass: string;
}

function ProbBar({ label, value, barClass }: ProbBarProps) {
  const pct = ((value ?? 0) * 100).toFixed(1);
  const width = Math.min(100, Math.max(0, (value ?? 0) * 100));
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono font-semibold">{pct}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${barClass}`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}

export function PredictionConfidence({
  pBull,
  pBear,
  pNeutral,
  direction,
  confidence,
  noTradeSignal,
  noTradeReason,
}: PredictionConfidenceProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Prediction</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <ProbBar label="P(Bull)" value={pBull} barClass="bg-success" />
          <ProbBar label="P(Bear)" value={pBear} barClass="bg-destructive" />
          <ProbBar label="P(Neutral)" value={pNeutral} barClass="bg-muted-foreground" />
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <Badge variant="outline" className={`capitalize ${directionBadgeClass(direction)}`}>
            {direction ?? 'None'}
          </Badge>
          <span className="text-xs text-muted-foreground">
            Confidence:{' '}
            <span className="font-mono font-semibold text-foreground">
              {confidence != null ? `${(confidence * 100).toFixed(1)}%` : '—'}
            </span>
          </span>
        </div>

        {noTradeSignal && (
          <Alert className="border-amber-500/30 bg-amber-500/10 py-2">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-700 text-xs font-medium">
              No-trade: {noTradeReason ?? 'signal active'}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
