import { useState } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { toast } from 'sonner';

interface ExportParams {
  action?: string;
  actor_id?: string;
  target_type?: string;
  date_from?: string;
  date_to?: string;
}

/**
 * Triggers a CSV download of audit logs via the export-audit-logs edge function.
 * Uses direct fetch + blob (not apiClient) because the response is CSV, not JSON.
 */
export function useAuditExport() {
  const [exporting, setExporting] = useState(false);

  async function exportCsv(params: ExportParams = {}) {
    setExporting(true);
    try {
      const session = (await supabase.auth.getSession()).data.session;
      if (!session) throw new Error('Not authenticated');

      const url = new URL(`${import.meta.env.VITE_SUPABASE_URL}/functions/v1/export-audit-logs`);
      for (const [key, value] of Object.entries(params)) {
        if (value != null && value !== '') url.searchParams.set(key, String(value));
      }

      const res = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'apikey': import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
        },
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error ?? `Export failed (${res.status})`);
      }

      const blob = await res.blob();
      const disposition = res.headers.get('Content-Disposition');
      const filenameMatch = disposition?.match(/filename="?([^"]+)"?/);
      const filename = filenameMatch?.[1] ?? `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`;

      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(a.href);

      const rowCount = res.headers.get('X-Row-Count');
      toast.success(`Exported ${rowCount ?? ''} audit log entries`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  }

  return { exportCsv, exporting };
}
