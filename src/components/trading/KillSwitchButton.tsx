import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/components/ui/alert';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { AlertTriangle, ShieldOff, Play } from 'lucide-react';

interface KillSwitchButtonProps {
  sessionId: string | null;
  sessionStatus: string | null;
}

// The kill-switch Edge Function accepts both 'halt' and 'resume' actions.
// Previously this component rendered a dead "Session Already Halted" Badge
// when the session was halted, leaving operators with no way to resume
// trading from the UI. Now halted sessions get a Resume button that
// toggles session_status back to 'active'.
export function KillSwitchButton({ sessionId, sessionStatus }: KillSwitchButtonProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();

  const isHalted = sessionStatus === 'halted';
  const action: 'halt' | 'resume' = isHalted ? 'resume' : 'halt';

  async function handleConfirm() {
    if (!sessionId) return;
    setIsSubmitting(true);
    try {
      // C-1 fix: route through the kill-switch Edge Function. Direct
      // UPDATE on trading_sessions is denied by RLS for authenticated
      // users (only service_role can write); the Edge Function uses
      // the service role server-side after verifying trading.configure.
      const { data, error } = await supabase.functions.invoke(
        'kill-switch',
        {
          body: { session_id: sessionId, action },
        },
      );

      if (error) throw error;
      const payload = data as { ok?: boolean; error?: string } | null;
      if (!payload?.ok) {
        throw new Error(
          payload?.error ?? `${action === 'halt' ? 'Kill switch' : 'Resume'} failed`,
        );
      }

      toast({
        title: action === 'halt' ? 'Session halted' : 'Session resumed',
        description:
          action === 'halt'
            ? 'All trading has been halted for today.'
            : 'Trading has been resumed for today\u2019s session.',
      });
      setShowConfirm(false);
    } catch (err) {
      toast({
        title: action === 'halt' ? 'Kill switch failed' : 'Resume failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  if (showConfirm) {
    const isHaltConfirm = action === 'halt';
    return (
      <div
        className={
          isHaltConfirm
            ? 'flex flex-col gap-3 rounded-md border border-destructive/30 bg-destructive/5 p-3'
            : 'flex flex-col gap-3 rounded-md border border-success/30 bg-success/5 p-3'
        }
      >
        <Alert className="border-0 bg-transparent p-0">
          {isHaltConfirm ? (
            <AlertTriangle className="h-4 w-4 text-destructive" />
          ) : (
            <Play className="h-4 w-4 text-success" />
          )}
          <AlertTitle
            className={
              isHaltConfirm
                ? 'text-destructive text-sm font-semibold'
                : 'text-success text-sm font-semibold'
            }
          >
            {isHaltConfirm ? 'Confirm Kill Switch' : 'Confirm Resume'}
          </AlertTitle>
          <AlertDescription className="text-xs">
            {isHaltConfirm
              ? 'This will immediately halt all trading for today\u2019s session. You can resume trading from this page.'
              : 'This will resume trading for today\u2019s session. New predictions and positions will be allowed again.'}
          </AlertDescription>
        </Alert>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant={isHaltConfirm ? 'destructive' : 'default'}
            className={isHaltConfirm ? undefined : 'bg-success hover:bg-success/90 text-success-foreground'}
            onClick={handleConfirm}
            disabled={isSubmitting}
          >
            {isSubmitting
              ? isHaltConfirm ? 'Halting\u2026' : 'Resuming\u2026'
              : isHaltConfirm ? 'Confirm Halt' : 'Confirm Resume'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowConfirm(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  if (isHalted) {
    return (
      <Button
        variant="default"
        size="sm"
        className="bg-success hover:bg-success/90 text-success-foreground"
        onClick={() => setShowConfirm(true)}
        disabled={!sessionId}
      >
        <Play className="mr-1.5 h-4 w-4" />
        RESUME TRADING
      </Button>
    );
  }

  return (
    <Button
      variant="destructive"
      size="sm"
      onClick={() => setShowConfirm(true)}
      disabled={!sessionId}
    >
      <ShieldOff className="mr-1.5 h-4 w-4" />
      KILL SWITCH &mdash; Halt All Trading
    </Button>
  );
}
