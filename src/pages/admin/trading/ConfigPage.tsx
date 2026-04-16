/**
 * Configuration — /admin/trading/config
 * Phase 3B deliverable TPLAN-CONSOLE-003G
 *
 * Permission: trading.configure (already gated in App.tsx).
 * Shows Tradier connection status, sizing phase, paper phase criteria, kill switch.
 */
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Settings2, AlertTriangle, CheckCircle, Clock, User } from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { KillSwitchButton } from '@/components/trading/KillSwitchButton';
import { useTradingSession } from '@/hooks/trading/useTradingSession';
import { supabase } from '@/integrations/supabase/client';

interface PaperCriterionRow {
  criterion_id: string;
  criterion_name: string;
  target_description: string;
  current_value_text: string | null;
  status: string;
  observations_count: number | null;
  is_manual: boolean | null;
  last_evaluated_at: string | null;
}

function criterionStatusBadge(status: string, observations: number | null) {
  switch (status) {
    case 'passed':
      return (
        <Badge variant="outline" className="bg-success/10 text-success border-success/20 shrink-0">
          PASSED
        </Badge>
      );
    case 'failed':
      return (
        <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20 shrink-0">
          FAILED
        </Badge>
      );
    case 'in_progress':
      return (
        <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-500/20 shrink-0">
          IN PROGRESS{observations ? ` (${observations})` : ''}
        </Badge>
      );
    case 'blocked':
      return (
        <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/20 shrink-0">
          BLOCKED
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="bg-muted text-muted-foreground border-border shrink-0">
          NOT STARTED
        </Badge>
      );
  }
}

interface OperatorConfigRow {
  id: string;
  sizing_phase: number | null;
  is_sandbox: boolean | null;
  live_trading_enabled: boolean | null;
  tradier_account_id: string | null;
  tradier_key_preview: string | null;
  account_type: string | null;
}

const SIZING_PHASES: Record<
  number,
  { label: string; description: string }
> = {
  1: {
    label: 'Phase 1 — Paper',
    description: 'Core 0.5%, satellite 0.25%',
  },
  2: {
    label: 'Phase 2 — Conservative',
    description: 'Core 0.5%, satellite 0.25%',
  },
  3: {
    label: 'Phase 3 — Standard',
    description: 'Core 1.0%, satellite 0.5%',
  },
  4: {
    label: 'Phase 4 — Margin',
    description: 'Core 1.0%, satellite 0.5% + 2:1 margin',
  },
};

function SizingPhaseIndicator({ current }: { current: number | null }) {
  const phase = current ?? 1;
  return (
    <div className="flex gap-2 flex-wrap">
      {[1, 2, 3, 4].map((n) => (
        <div
          key={n}
          className={`flex-1 min-w-[120px] rounded-md border p-3 transition-colors ${
            n === phase
              ? 'border-primary bg-primary/5'
              : 'border-border bg-muted/30 opacity-50'
          }`}
        >
          <p
            className={`text-xs font-semibold ${
              n === phase ? 'text-primary' : 'text-muted-foreground'
            }`}
          >
            {SIZING_PHASES[n]?.label}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {SIZING_PHASES[n]?.description}
          </p>
        </div>
      ))}
    </div>
  );
}

export default function TradingConfigPage() {
  const { data: config, isLoading: configLoading, error: configError } = useQuery({
    queryKey: ['trading', 'operator-config'],
    queryFn: async () => {
      const { data: row, error: err } = await supabase
        .from('trading_operator_config')
        .select(
          'id, sizing_phase, is_sandbox, live_trading_enabled, tradier_account_id, tradier_key_preview, account_type'
        )
        .maybeSingle();
      if (err) throw err;
      return (row as OperatorConfigRow | null) ?? null;
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const { data: session } = useTradingSession();

  const { data: criteriaData } = useQuery({
    queryKey: ['admin', 'trading', 'paper-criteria'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('paper_phase_criteria')
        .select(
          'criterion_id, criterion_name, target_description, current_value_text, status, observations_count, is_manual, last_evaluated_at'
        )
        .order('criterion_id', { ascending: true });
      if (error) throw error;
      return (data ?? []) as PaperCriterionRow[];
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const passedCount = useMemo(
    () => criteriaData?.filter((c) => c.status === 'passed').length ?? 0,
    [criteriaData]
  );
  const failedCount = useMemo(
    () => criteriaData?.filter((c) => c.status === 'failed').length ?? 0,
    [criteriaData]
  );
  const allPassed = passedCount === 12 && (criteriaData?.length ?? 0) === 12;

  if (configLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Configuration" subtitle="Trading system configuration" />
        <LoadingSkeleton variant="card" rows={3} />
      </div>
    );
  }

  if (configError) {
    return (
      <div className="space-y-6">
        <PageHeader title="Configuration" subtitle="Trading system configuration" />
        <ErrorState message="Failed to load configuration." />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="space-y-6">
        <PageHeader title="Configuration" subtitle="Trading system configuration" />
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <Settings2 className="h-5 w-5 text-muted-foreground mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium">No configuration found</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Configuration will appear here once the trading backend has
                  initialized. Start the Railway backend to create the initial
                  config.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configuration"
        subtitle="Trading system configuration"
      />

      {/* Section 1 — Tradier Connection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tradier Connection Status</CardTitle>
          <CardDescription>
            Live trading connection and account details
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert className="border-amber-500/30 bg-amber-500/10">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-700 text-xs">
              TRADIER_SANDBOX=true is set in Railway environment variables. Live
              trading requires funding the production Tradier account and
              changing this to false. This is controlled by D-013 and T-Rule 9.
            </AlertDescription>
          </Alert>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Sandbox Mode</p>
              <Badge
                variant="outline"
                className={
                  config.is_sandbox
                    ? 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                    : 'bg-success/10 text-success border-success/20'
                }
              >
                {config.is_sandbox ? 'Sandbox ON' : 'Production'}
              </Badge>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Account ID</p>
              <p className="font-mono text-xs">
                {config.tradier_account_id ?? 'Not configured'}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">API Key</p>
              <p className="font-mono text-xs">
                {config.tradier_key_preview ?? 'Not configured'}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Account Type</p>
              <p className="text-xs capitalize">
                {config.account_type ?? 'Unknown'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Section 2 — Sizing Phase */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sizing Phase</CardTitle>
          <CardDescription>
            Current position sizing configuration — read-only in Phase 3
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <SizingPhaseIndicator current={config.sizing_phase} />
          <p className="text-xs text-muted-foreground">
            Sizing phase advances automatically when paper phase criteria are met.
          </p>
        </CardContent>
      </Card>

      {/* Section 3 — Paper Phase Go-Live Criteria */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Paper Phase Go-Live Criteria</CardTitle>
          <CardDescription>
            All 12 criteria (D-013) must pass before live trading is enabled
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Summary bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-mono font-semibold">
                {passedCount} / 12 passed
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-success transition-all"
                style={{ width: `${(passedCount / 12) * 100}%` }}
              />
            </div>
          </div>

          {allPassed && (
            <Alert className="border-success/30 bg-success/10">
              <CheckCircle className="h-4 w-4 text-success" />
              <AlertDescription className="text-success font-medium text-sm">
                All go-live criteria met — ready for live trading review
              </AlertDescription>
            </Alert>
          )}

          {failedCount > 0 && (
            <Alert className="border-destructive/30 bg-destructive/10">
              <AlertTriangle className="h-4 w-4 text-destructive" />
              <AlertDescription className="text-destructive font-medium text-sm">
                {failedCount} {failedCount === 1 ? 'criterion' : 'criteria'} failed — live trading blocked
              </AlertDescription>
            </Alert>
          )}

          {/* Criteria list */}
          {!criteriaData || criteriaData.length === 0 ? (
            <div className="space-y-2">
              {Array.from({ length: 12 }).map((_, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between gap-3 rounded-md border p-3"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="text-sm text-muted-foreground">
                      Loading criteria...
                    </span>
                  </div>
                  <Badge
                    variant="outline"
                    className="bg-muted text-muted-foreground border-border shrink-0"
                  >
                    NOT STARTED
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {criteriaData.map((criterion) => (
                <div
                  key={criterion.criterion_id}
                  className="rounded-md border p-3 space-y-1.5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-0.5 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded text-muted-foreground shrink-0">
                          {criterion.criterion_id}
                        </span>
                        <span className="text-sm font-medium">
                          {criterion.criterion_name}
                        </span>
                        {criterion.is_manual && (
                          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                            <User className="h-3 w-3" />
                            Manual
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {criterion.target_description}
                      </p>
                      {criterion.current_value_text && (
                        <p className="text-xs text-foreground font-mono">
                          {criterion.current_value_text}
                        </p>
                      )}
                    </div>
                    {criterionStatusBadge(
                      criterion.status,
                      criterion.observations_count
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          <p className="text-xs text-muted-foreground pt-1">
            Automated criteria evaluated daily at 4:30 PM ET. Manual criteria
            (GLC-007 through GLC-010) require operator sign-off.
          </p>
        </CardContent>
      </Card>

      {/* Section 4 — Danger Zone */}
      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-destructive" />
            Danger Zone
          </CardTitle>
          <CardDescription>
            Emergency session controls — use with caution
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="text-sm">
              <p className="font-medium">Session Kill Switch</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Immediately halts all trading for today&apos;s session.
              </p>
            </div>
          </div>
          {session ? (
            <div className="flex items-center gap-3">
              <Badge
                variant="outline"
                className={
                  session.session_status === 'active'
                    ? 'bg-success/10 text-success border-success/20'
                    : session.session_status === 'halted'
                    ? 'bg-destructive/10 text-destructive border-destructive/20'
                    : 'bg-muted text-muted-foreground border-border'
                }
              >
                Session: {session.session_status}
              </Badge>
              <KillSwitchButton
                sessionId={session.id}
                sessionStatus={session.session_status}
              />
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                No active session
              </span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
