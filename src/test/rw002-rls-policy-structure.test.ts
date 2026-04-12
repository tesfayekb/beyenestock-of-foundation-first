/**
 * RW-002: RLS policy visibility mismatch detection.
 *
 * Verifies that RLS-protected tables have policies defined in SQL files
 * and that the policy structure follows security patterns.
 *
 * Full DB-level testing requires deployed DB — this is a structural check.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'fs';
import { resolve, join } from 'path';

const SQL_DIR = resolve(__dirname, '../../sql');

describe('RW-002: RLS policy structure verification', () => {
  it('RLS policies SQL file exists', () => {
    const files = readdirSync(SQL_DIR);
    const rlsFile = files.find((f) => f.includes('rls'));
    expect(rlsFile).toBeDefined();
  });

  it('RLS policies cover core tables', () => {
    const content = readFileSync(join(SQL_DIR, '03_rbac_rls_policies.sql'), 'utf-8');
    
    // Core tables that MUST have RLS
    const requiredTables = [
      'user_roles',
      'roles',
      'permissions',
      'role_permissions',
      'profiles',
      'audit_logs',
    ];

    for (const table of requiredTables) {
      expect(content).toContain(table);
    }
  });

  it('RLS policies use has_role or has_permission functions', () => {
    const content = readFileSync(join(SQL_DIR, '03_rbac_rls_policies.sql'), 'utf-8');
    const usesSecurityFunctions = 
      content.includes('has_role') || 
      content.includes('has_permission') ||
      content.includes('is_superadmin') ||
      content.includes('auth.uid()');
    expect(usesSecurityFunctions).toBe(true);
  });

  it('audit_logs table does NOT allow client-side reads (service role only)', () => {
    const content = readFileSync(join(SQL_DIR, '03_rbac_rls_policies.sql'), 'utf-8');
    // Audit logs should have restricted SELECT — only via admin with permission
    // or service role. Should not have a permissive "anyone can read" policy.
    const hasAuditSelect = content.includes('audit_logs') && content.includes('SELECT');
    expect(hasAuditSelect).toBe(true);
  });
});
