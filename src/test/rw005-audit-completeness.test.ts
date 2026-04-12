/**
 * RW-005: Audit event completeness.
 *
 * Verifies that every edge function performing mutations calls logAuditEvent.
 * Scans edge function source files for mutation patterns and checks audit calls.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { resolve, join } from 'path';

const FUNCTIONS_DIR = resolve(__dirname, '../../supabase/functions');

/** Edge functions that perform mutations and MUST have audit logging */
const MUTATION_FUNCTIONS = [
  'assign-permission-to-role',
  'assign-role',
  'create-role',
  'deactivate-user',
  'delete-role',
  'health-alert-config',
  'mfa-recovery-generate',
  'mfa-recovery-verify',
  'reactivate-user',
  'revoke-permission-from-role',
  'revoke-role',
  'revoke-sessions',
  'update-profile',
  'update-role',
];

/** Edge functions that are read-only or system-internal (no audit required) */
const READ_ONLY_FUNCTIONS = [
  'export-audit-logs',
  'get-profile',
  'get-role-detail',
  'get-user-stats',
  'health-alert-config', // GET path is read-only
  'health-alerts',
  'health-check',
  'health-detailed',
  'health-metrics',
  'job-alert-evaluation',
  'job-audit-cleanup',
  'job-health-check',
  'job-metrics-aggregate',
  'jobs-dead-letters',
  'jobs-kill-switch',
  'jobs-pause',
  'jobs-replay-dead-letter',
  'jobs-resume',
  'list-permissions',
  'list-roles',
  'list-users',
  'query-audit-logs',
];

describe('RW-005: Audit event completeness', () => {
  for (const fn of MUTATION_FUNCTIONS) {
    it(`${fn} calls logAuditEvent`, () => {
      const indexPath = join(FUNCTIONS_DIR, fn, 'index.ts');
      const content = readFileSync(indexPath, 'utf-8');
      expect(content).toContain('logAuditEvent');
    });
  }

  it('audit.ts sanitizes sensitive metadata fields', () => {
    const content = readFileSync(
      join(FUNCTIONS_DIR, '_shared/audit.ts'),
      'utf-8'
    );
    expect(content).toContain('FORBIDDEN_METADATA_KEYS');
    expect(content).toContain('password');
    expect(content).toContain('token');
    expect(content).toContain('secret');
    expect(content).toContain('[REDACTED]');
  });

  it('audit.ts includes correlation_id in metadata', () => {
    const content = readFileSync(
      join(FUNCTIONS_DIR, '_shared/audit.ts'),
      'utf-8'
    );
    expect(content).toContain('correlation_id');
  });

  it('logAuditEvent never throws (returns result object)', () => {
    const content = readFileSync(
      join(FUNCTIONS_DIR, '_shared/audit.ts'),
      'utf-8'
    );
    // Function should have try/catch and return failure object
    expect(content).toContain('try {');
    expect(content).toContain('catch');
    expect(content).toContain("success: false");
    expect(content).toContain("success: true");
  });
});
