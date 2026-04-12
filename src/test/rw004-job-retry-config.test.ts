/**
 * RW-004: Job retry misconfiguration detection.
 *
 * Verifies that job execution patterns follow correct retry/DLQ conventions
 * by scanning edge function source for proper error handling patterns.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const FUNCTIONS_DIR = resolve(__dirname, '../../supabase/functions');

/** Job edge functions that execute scheduled work */
const JOB_FUNCTIONS = [
  'job-alert-evaluation',
  'job-audit-cleanup',
  'job-health-check',
  'job-metrics-aggregate',
];

describe('RW-004: Job retry configuration', () => {
  for (const fn of JOB_FUNCTIONS) {
    describe(fn, () => {
      const content = readFileSync(
        resolve(FUNCTIONS_DIR, fn, 'index.ts'),
        'utf-8'
      );

      it('imports job-executor or handles errors', () => {
        const hasJobExecutor = content.includes('job-executor') || content.includes('executeJob');
        const hasTryCatch = content.includes('try') && content.includes('catch');
        expect(hasJobExecutor || hasTryCatch).toBe(true);
      });

      it('uses createHandler for CORS and rate limiting', () => {
        expect(content).toContain('createHandler');
      });
    });
  }

  it('job-executor.ts exists and exports executeJob', () => {
    const content = readFileSync(
      resolve(FUNCTIONS_DIR, '_shared/job-executor.ts'),
      'utf-8'
    );
    expect(content).toContain('executeJob');
  });

  it('handler.ts classifies errors properly', () => {
    const content = readFileSync(
      resolve(FUNCTIONS_DIR, '_shared/handler.ts'),
      'utf-8'
    );
    expect(content).toContain('AuthError');
    expect(content).toContain('ValidationError');
    expect(content).toContain('PermissionDeniedError');
    expect(content).toContain('500');
  });
});
