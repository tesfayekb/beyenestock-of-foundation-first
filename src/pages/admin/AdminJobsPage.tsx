import { useState, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatCard } from '@/components/dashboard/StatCard';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { ConfirmActionDialog } from '@/components/dashboard/ConfirmActionDialog';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { supabase } from '@/integrations/supabase/client';
import { apiClient } from '@/lib/api-client';
import {
  Cog, Play, Pause, AlertOctagon, RotateCcw, Inbox,
  AlertTriangle,
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';

type JobRegistry = {
  id: string;
  version: string;
  owner_module: string;
  description: string | null;
  schedule: string;
  class: string;
  priority: string;
  enabled: boolean;
  status: string;
  max_retries: number;
  timeout_seconds: number;
};

type JobExecution = {
  id: string;
  job_id: string;
  state: string;
  attempt: number;
  duration_ms: number | null;
  failure_type: string | null;
  error: unknown;
  created_at: string;
  completed_at: string | null;
};

function stateColor(state: string) {
  switch (state) {
    case 'succeeded': return 'bg-success/10 text-success border-success/20';
    case 'running': return 'bg-primary/10 text-primary border-primary/20';
    case 'failed': case 'dead_lettered': return 'bg-destructive/10 text-destructive border-destructive/20';
    case 'paused': case 'cancelled': return 'bg-warning/10 text-warning border-warning/20';
    case 'poison': return 'bg-destructive/10 text-destructive border-destructive/20';
    default: return 'bg-muted text-muted-foreground';
  }
}

export default function AdminJobsPage() {
  const queryClient = useQueryClient();
  const { context } = useUserRoles();
  const canKillSwitch = checkPermission(context, 'jobs.emergency');
  const canPause = checkPermission(context, 'jobs.pause');
  const canResume = checkPermission(context, 'jobs.resume');
  const canReplay = checkPermission(context, 'jobs.deadletter.manage');
  const [tab, setTab] = useState('registry');
  const [killSwitchDialog, setKillSwitchDialog] = useState(false);
  const [pauseDialog, setPauseDialog] = useState<{ jobId: string } | null>(null);
  const [resumeDialog, setResumeDialog] = useState<{ jobId: string } | null>(null);
  const [replayDialog, setReplayDialog] = useState<{ executionId: string } | null>(null);

  // Job registry
  const { data: jobs, isLoading: loadingJobs, error: jobsError } = useQuery({
    queryKey: ['admin', 'job-registry'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('job_registry')
        .select('*')
        .order('id');
      if (error) throw error;
      return (data ?? []) as JobRegistry[];
    },
  });

  // Recent executions
  const { data: executions } = useQuery({
    queryKey: ['admin', 'job-executions'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('job_executions')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(50);
      if (error) throw error;
      return (data ?? []) as JobExecution[];
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  // Dead letters
  const { data: deadLetters, refetch: refetchDeadLetters } = useQuery({
    queryKey: ['admin', 'dead-letters'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('job_executions')
        .select('*')
        .eq('state', 'dead_lettered')
        .order('created_at', { ascending: false })
        .limit(50);
      if (error) throw error;
      return (data ?? []) as JobExecution[];
    },
  });

  // Memoized derived state
  const { killSwitch, realJobs } = useMemo(() => ({
    killSwitch: jobs?.find(j => j.id === '__kill_switch__'),
    realJobs: jobs?.filter(j => !j.id.startsWith('__')) ?? [],
  }), [jobs]);

  const isKillSwitchActive = useMemo(
    () => killSwitch ? !killSwitch.enabled : false,
    [killSwitch],
  );

  const activeJobCount = useMemo(
    () => realJobs.filter(j => j.enabled && j.status === 'registered').length,
    [realJobs],
  );

  const pausedPoisonCount = useMemo(
    () => realJobs.filter(j => j.status === 'paused' || j.status === 'poison').length,
    [realJobs],
  );

  // Memoized callbacks
  const handleOpenKillSwitch = useCallback(() => setKillSwitchDialog(true), []);
  const handleOpenPause = useCallback((jobId: string) => setPauseDialog({ jobId }), []);
  const handleOpenResume = useCallback((jobId: string) => setResumeDialog({ jobId }), []);
  const handleOpenReplay = useCallback((executionId: string) => setReplayDialog({ executionId }), []);

  // Mutations
  const killSwitchMutation = useMutation({
    mutationFn: (reason: string) =>
      apiClient.post('jobs-kill-switch', {
        activate: !isKillSwitchActive,
        scope: 'global',
        reason,
      }),
    onSuccess: () => {
      toast.success(isKillSwitchActive ? 'Kill switch deactivated' : 'Kill switch activated');
      queryClient.invalidateQueries({ queryKey: ['admin', 'job-registry'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const pauseMutation = useMutation({
    mutationFn: ({ jobId, reason }: { jobId: string; reason: string }) =>
      apiClient.post('jobs-pause', { job_id: jobId, reason }),
    onSuccess: () => {
      toast.success('Job paused');
      queryClient.invalidateQueries({ queryKey: ['admin', 'job-registry'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const resumeMutation = useMutation({
    mutationFn: ({ jobId, reason }: { jobId: string; reason: string }) =>
      apiClient.post('jobs-resume', { job_id: jobId, reason }),
    onSuccess: () => {
      toast.success('Job resumed');
      queryClient.invalidateQueries({ queryKey: ['admin', 'job-registry'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const replayMutation = useMutation({
    mutationFn: ({ executionId, reason }: { executionId: string; reason: string }) =>
      apiClient.post('jobs-replay-dead-letter', { execution_id: executionId, reason }),
    onSuccess: () => {
      toast.success('Execution replayed');
      refetchDeadLetters();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleKillSwitchConfirm = useCallback((reason?: string) => {
    killSwitchMutation.mutate(reason ?? 'No reason provided');
    setKillSwitchDialog(false);
  }, [killSwitchMutation]);

  const handlePauseConfirm = useCallback((reason?: string) => {
    if (pauseDialog) pauseMutation.mutate({ jobId: pauseDialog.jobId, reason: reason ?? '' });
    setPauseDialog(null);
  }, [pauseDialog, pauseMutation]);

  const handleResumeConfirm = useCallback((reason?: string) => {
    if (resumeDialog) resumeMutation.mutate({ jobId: resumeDialog.jobId, reason: reason ?? '' });
    setResumeDialog(null);
  }, [resumeDialog, resumeMutation]);

  const handleReplayConfirm = useCallback((reason?: string) => {
    if (replayDialog) replayMutation.mutate({ executionId: replayDialog.executionId, reason: reason ?? '' });
    setReplayDialog(null);
  }, [replayDialog, replayMutation]);

  return (
    <div className="space-y-6">
      <PageHeader title="Job Management" subtitle="Scheduled jobs, executions, and emergency controls" />

      {jobsError ? (
        <ErrorState message="Failed to load job data" />
      ) : loadingJobs ? (
        <LoadingSkeleton variant="card" rows={3} />
      ) : (
        <>
          {/* Emergency Controls */}
          <Card className={isKillSwitchActive ? 'border-destructive' : ''}>
             <CardHeader className="p-4 pb-3 sm:p-6 sm:pb-3">
               <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <AlertOctagon className="h-4 w-4" />
                    Emergency Controls
                  </CardTitle>
                  <CardDescription>Global kill switch and emergency actions</CardDescription>
                </div>
                <Badge variant="outline" className={isKillSwitchActive
                  ? 'bg-destructive/10 text-destructive border-destructive/20'
                  : 'bg-success/10 text-success border-success/20'
                }>
                  {isKillSwitchActive ? 'KILL SWITCH ACTIVE' : 'Normal Operation'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0 sm:p-6 sm:pt-0">
              {canKillSwitch && (
                <Button
                  variant={isKillSwitchActive ? 'default' : 'destructive'}
                  size="sm"
                  onClick={handleOpenKillSwitch}
                >
                  {isKillSwitchActive ? 'Deactivate Kill Switch' : 'Activate Kill Switch'}
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Stats */}
          <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
            <StatCard title="Registered Jobs" value={realJobs.length} icon={Cog} />
            <StatCard title="Active" value={activeJobCount} icon={Play} />
            <StatCard title="Paused / Poison" value={pausedPoisonCount} icon={Pause} />
            <StatCard title="Dead Letters" value={deadLetters?.length ?? 0} icon={Inbox} />
          </div>

          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="registry">Job Registry</TabsTrigger>
              <TabsTrigger value="executions">Recent Executions</TabsTrigger>
              <TabsTrigger value="dead-letters">Dead Letters ({deadLetters?.length ?? 0})</TabsTrigger>
            </TabsList>

            <TabsContent value="registry" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left text-xs text-muted-foreground">
                          <th className="pb-2 pr-4">Job ID</th>
                          <th className="pb-2 pr-4">Class</th>
                          <th className="pb-2 pr-4">Schedule</th>
                          <th className="pb-2 pr-4">Status</th>
                          <th className="pb-2 pr-4">Retries</th>
                          <th className="pb-2">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {realJobs.map((job) => (
                          <tr key={job.id} className="border-b last:border-0">
                            <td className="py-3 pr-4 font-mono text-xs">{job.id}</td>
                            <td className="py-3 pr-4">
                              <Badge variant="outline" className="text-xs">{job.class}</Badge>
                            </td>
                            <td className="py-3 pr-4 font-mono text-xs">{job.schedule}</td>
                            <td className="py-3 pr-4">
                              <Badge variant="outline" className={stateColor(job.status)}>
                                {job.status}
                              </Badge>
                            </td>
                            <td className="py-3 pr-4">{job.max_retries}</td>
                            <td className="py-3">
                              {job.enabled && job.status === 'registered' && job.class !== 'system_critical' && canPause ? (
                                <Button variant="ghost" size="sm" onClick={() => handleOpenPause(job.id)}>
                                  <Pause className="h-3 w-3 mr-1" /> Pause
                                </Button>
                              ) : job.status === 'paused' && canResume ? (
                                <Button variant="ghost" size="sm" onClick={() => handleOpenResume(job.id)}>
                                  <Play className="h-3 w-3 mr-1" /> Resume
                                </Button>
                              ) : job.status === 'poison' ? (
                                <Badge variant="outline" className="bg-destructive/10 text-destructive">
                                  <AlertTriangle className="h-3 w-3 mr-1" /> Poison
                                </Badge>
                              ) : null}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="executions" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left text-xs text-muted-foreground">
                          <th className="pb-2 pr-4">Job</th>
                          <th className="pb-2 pr-4">State</th>
                          <th className="pb-2 pr-4">Attempt</th>
                          <th className="pb-2 pr-4">Duration</th>
                          <th className="pb-2 pr-4">Failure Type</th>
                          <th className="pb-2">Started</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(executions ?? []).map((ex) => (
                          <tr key={ex.id} className="border-b last:border-0">
                            <td className="py-2 pr-4 font-mono text-xs">{ex.job_id}</td>
                            <td className="py-2 pr-4">
                              <Badge variant="outline" className={stateColor(ex.state)}>{ex.state}</Badge>
                            </td>
                            <td className="py-2 pr-4">{ex.attempt}</td>
                            <td className="py-2 pr-4">{ex.duration_ms != null ? `${ex.duration_ms}ms` : '—'}</td>
                            <td className="py-2 pr-4 text-xs">{ex.failure_type ?? '—'}</td>
                            <td className="py-2 text-xs text-muted-foreground">
                              {format(new Date(ex.created_at), 'MMM d, HH:mm:ss')}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="dead-letters" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  {deadLetters && deadLetters.length > 0 ? (
                    <div className="space-y-3">
                      {deadLetters.map((dl) => (
                        <div key={dl.id} className="flex items-center justify-between rounded-md border p-3">
                          <div className="space-y-1">
                            <p className="text-sm font-medium font-mono">{dl.job_id}</p>
                            <p className="text-xs text-muted-foreground">
                              Attempt {dl.attempt} · {dl.failure_type ?? 'unknown'} ·{' '}
                              {format(new Date(dl.created_at), 'MMM d, HH:mm')}
                            </p>
                            {dl.error && typeof dl.error === 'object' && (dl.error as Record<string, unknown>).message && (
                              <p className="text-xs text-destructive truncate max-w-md">
                                {String((dl.error as Record<string, unknown>).message)}
                              </p>
                            )}
                          </div>
                          {canReplay && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleOpenReplay(dl.id)}
                            >
                              <RotateCcw className="h-3 w-3 mr-1" /> Replay
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No dead-lettered executions.</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}

      {/* Dialogs */}
      <ConfirmActionDialog
        open={killSwitchDialog}
        onOpenChange={setKillSwitchDialog}
        title={isKillSwitchActive ? 'Deactivate Kill Switch' : 'Activate Global Kill Switch'}
        description={isKillSwitchActive
          ? 'This will allow all jobs to resume execution.'
          : 'This will immediately halt ALL job execution system-wide. Use only in emergencies.'}
        confirmLabel={isKillSwitchActive ? 'Deactivate' : 'Activate Kill Switch'}
        destructive={!isKillSwitchActive}
        requireReason
        onConfirm={handleKillSwitchConfirm}
        loading={killSwitchMutation.isPending}
      />
      <ConfirmActionDialog
        open={!!pauseDialog}
        onOpenChange={(open) => !open && setPauseDialog(null)}
        title="Pause Job"
        description={`Pause job "${pauseDialog?.jobId}"? It will stop executing until resumed.`}
        confirmLabel="Pause"
        destructive={false}
        requireReason
        onConfirm={handlePauseConfirm}
        loading={pauseMutation.isPending}
      />
      <ConfirmActionDialog
        open={!!resumeDialog}
        onOpenChange={(open) => !open && setResumeDialog(null)}
        title="Resume Job"
        description={`Resume job "${resumeDialog?.jobId}"?`}
        confirmLabel="Resume"
        destructive={false}
        requireReason
        onConfirm={handleResumeConfirm}
        loading={resumeMutation.isPending}
      />
      <ConfirmActionDialog
        open={!!replayDialog}
        onOpenChange={(open) => !open && setReplayDialog(null)}
        title="Replay Dead-Lettered Execution"
        description="This will create a new execution record and schedule it for the next run cycle."
        confirmLabel="Replay"
        destructive={false}
        requireReason
        onConfirm={handleReplayConfirm}
        loading={replayMutation.isPending}
      />
    </div>
  );
}