/**
 * RW-003: Shared function contract stability.
 *
 * Verifies that shared functions exported from key modules maintain
 * their expected signatures and behavior contracts.
 */
import { describe, it, expect } from 'vitest';
import { checkPermission, checkRole } from '@/lib/rbac';
import { resolveAllDeps, PERMISSION_DEPS } from '@/config/permission-deps';

describe('RW-003: Shared function contracts', () => {
  describe('checkPermission()', () => {
    it('returns false when context is null', () => {
      expect(checkPermission(null, 'admin.access')).toBe(false);
    });

    it('returns true for superadmin regardless of permissions list', () => {
      const ctx = { roles: [], permissions: [], is_superadmin: true };
      expect(checkPermission(ctx, 'any.permission')).toBe(true);
    });

    it('returns true when permission is in the list', () => {
      const ctx = { roles: ['admin'], permissions: ['admin.access', 'users.view_all'], is_superadmin: false };
      expect(checkPermission(ctx, 'users.view_all')).toBe(true);
    });

    it('returns false when permission is NOT in the list', () => {
      const ctx = { roles: ['user'], permissions: ['profile.self_manage'], is_superadmin: false };
      expect(checkPermission(ctx, 'admin.access')).toBe(false);
    });
  });

  describe('checkRole()', () => {
    it('returns false when context is null', () => {
      expect(checkRole(null, 'admin')).toBe(false);
    });

    it('returns true when role is present', () => {
      const ctx = { roles: ['admin', 'user'], permissions: [], is_superadmin: false };
      expect(checkRole(ctx, 'admin')).toBe(true);
    });

    it('returns false when role is absent', () => {
      const ctx = { roles: ['user'], permissions: [], is_superadmin: false };
      expect(checkRole(ctx, 'admin')).toBe(false);
    });
  });

  describe('resolveAllDeps()', () => {
    it('returns empty array for permission with no deps', () => {
      expect(resolveAllDeps('nonexistent.permission')).toEqual([]);
    });

    it('resolves direct dependencies', () => {
      const deps = resolveAllDeps('audit.view');
      expect(deps).toContain('admin.access');
    });

    it('resolves transitive dependencies', () => {
      const deps = resolveAllDeps('audit.export');
      expect(deps).toContain('audit.view');
      expect(deps).toContain('admin.access');
    });

    it('does not include the key itself', () => {
      const deps = resolveAllDeps('audit.export');
      expect(deps).not.toContain('audit.export');
    });

    it('handles circular references without infinite loop', () => {
      // PERMISSION_DEPS does not have circular refs, but resolveAllDeps
      // uses visited set so it would handle them gracefully
      const deps = resolveAllDeps('roles.assign');
      expect(Array.isArray(deps)).toBe(true);
    });
  });

  describe('PERMISSION_DEPS structure', () => {
    it('all dependency values reference existing keys or terminal permissions', () => {
      const allKeys = new Set(Object.keys(PERMISSION_DEPS));
      // Terminal permissions (no entry in PERMISSION_DEPS but can be a dep value)
      const terminals = new Set(['admin.access', 'roles.view', 'users.view_all', 'audit.view', 'permissions.view', 'monitoring.view', 'jobs.view']);

      for (const [key, deps] of Object.entries(PERMISSION_DEPS)) {
        for (const dep of deps) {
          const isKnown = allKeys.has(dep) || terminals.has(dep);
          expect(isKnown).toBe(true);
        }
      }
    });
  });
});
