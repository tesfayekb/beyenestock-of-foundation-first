import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { AlertTriangle, ShieldOff } from 'lucide-react';

interface KillSwitchButtonProps {
  sessionId: string | null;
  sessionStatus: string | null;
}

export function KillSwitchButton({ sessionId, sessionStatus }: KillSwitchButtonProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();

  const isHalted = sessionStatus === 'halted';

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
          body: { session_id: sessionId, action: 'halt' },
        },
      );

      if (error) throw error;
      const payload = data as { ok?: boolean; error?: string } | null;
      if (!payload?.ok) {
        throw new Error(payload?.error ?? 'Kill switch failed');
      }

      toast({
        title: 'Session halted',
        description: 'All trading has been halted for today.',
      });
      setShowConfirm(false);
    } catch (err) {
      toast({
        title: 'Kill switch failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isHalted) {
    return (
      <Badge
        variant="outline"
        className="bg-muted text-muted-foreground border-border px-3 py-1"
      >
        <ShieldOff className="mr-1.5 h-3.5 w-3.5" />
        Session Already Halted
      </Badge>
    );
  }

  if (showConfirm) {
    return (
      <div className="flex flex-col gap-3 rounded-md border border-destructive/30 bg-destructive/5 p-3">
        <Alert className="border-0 bg-transparent p-0">
          <AlertTriangle className="h-4 w-4 text-destructive" />
          <AlertTitle className="text-destructive text-sm font-semibold">
            Confirm Kill Switch
          </AlertTitle>
          <AlertDescription className="text-xs">
            This will immediately halt all trading for today&apos;s session.
            The session will be halted. You can resume trading from this page.
          </AlertDescription>
        </Alert>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="destructive"
            onClick={handleConfirm}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Halting…' : 'Confirm Halt'}
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

  return (
    <Button
      variant="destructive"
      size="sm"
      onClick={() => setShowConfirm(true)}
      disabled={!sessionId}
    >
      <ShieldOff className="mr-1.5 h-4 w-4" />
      KILL SWITCH — Halt All Trading
    </Button>
  );
}
