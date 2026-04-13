/**
 * RW-005: Audit event completeness.
 *
 * Verifies that every edge function performing mutations calls logAuditEvent.
 * Scans edge function source files for mutation patterns and checks audit calls.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
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
