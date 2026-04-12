/**
 * RW-006: Health monitoring blind spot detection.
 *
 * Verifies that health check infrastructure exists and covers
 * all required subsystems.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const FUNCTIONS_DIR = resolve(__dirname, '../../supabase/functions');

describe('RW-006: Health monitoring completeness', () => {
  it('health-checks.ts covers database, auth, and audit checks', () => {
    const content = readFileSync(
      resolve(FUNCTIONS_DIR, '_shared/health-checks.ts'),
      'utf-8'
    );
    expect(content).toContain('checkDatabase');
    expect(content).toContain('checkAuth');
    expect(content).toContain('checkAuditPipeline');
    expect(content).toContain('deriveOverallStatus');
  });

  it('health-check edge function exists', () => {
    const content = readFileSync(
      resolve(FUNCTIONS_DIR, 'health-check/index.ts'),
      'utf-8'
    );
    expect(content).toContain('createHandler');
  });

  it('health-detailed edge function exists', () => {
    const content = readFileSync(
      resolve(FUNCTIONS_DIR, 'health-detailed/index.ts'),
      'utf-8'
    );
    expect(content).toContain('createHandler');
  });

  it('health-alerts edge function exists and processes alerts', () => {
    const content = readFileSync(
      resolve(FUNCTIONS_DIR, 'health-alerts/index.ts'),
      'utf-8'
    );
    expect(content).toContain('alert');
  });

  it('job-health-check exists for scheduled monitoring', () => {
    const content = readFileSync(
      resolve(FUNCTIONS_DIR, 'job-health-check/index.ts'),
      'utf-8'
    );
    expect(content).toContain('health');
  });
});
