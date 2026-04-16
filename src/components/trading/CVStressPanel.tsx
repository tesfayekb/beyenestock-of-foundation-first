import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, XCircle } from 'lucide-react';

interface CVStressPanelProps {
  cvStress: number | null;
  charmVelocity: number | null;
  vannaVelocity: number | null;
}

function cvStressBarClass(score: number): string {
  if (score >= 80) return 'bg-destructive';
  if (score >= 60) return 'bg-orange-500';
  if (score >= 30) return 'bg-amber-500';
  return 'bg-success';
}

function cvStressTextClass(score: number): string {
  if (score >= 80) return 'text-destructive';
  if (score >= 60) return 'text-orange-500';
  if (score >= 30) return 'text-amber-500';
  return 'text-success';
}

export function CVStressPanel({
  cvStress,
  charmVelocity,
  vannaVelocity,
}: CVStressPanelProps) {
  const score = cvStress ?? 0;
  const isCritical = score >= 85;
  const isBlocked = score >= 70;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">CV_Stress</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className={`text-3xl font-bold font-mono ${cvStressTextClass(score)}`}>
          {score.toFixed(0)}
          <span className="text-base font-normal text-muted-foreground ml-1">/ 100</span>
        </div>

        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${cvStressBarClass(score)}`}
            style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
          />
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground">
          <div>
            <p className="font-medium">Charm Velocity</p>
            <p className="font-mono text-foreground">
              {charmVelocity != null ? charmVelocity.toFixed(4) : '—'}
            </p>
          </div>
          <div>
            <p className="font-medium">Vanna Velocity</p>
            <p className="font-mono text-foreground">
              {vannaVelocity != null ? vannaVelocity.toFixed(4) : '—'}
            </p>
          </div>
        </div>

        {isCritical && (
          <Alert className="border-destructive/30 bg-destructive/10 py-2">
            <XCircle className="h-4 w-4 text-destructive" />
            <AlertDescription className="text-destructive text-xs font-medium">
              Critical — no new entries
            </AlertDescription>
          </Alert>
        )}

        {!isCritical && isBlocked && (
          <Alert className="border-amber-500/30 bg-amber-500/10 py-2">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-700 text-xs font-medium">
              Short-gamma blocked
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
