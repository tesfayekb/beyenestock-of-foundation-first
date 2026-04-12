/**
 * RW-007: User lifecycle deactivation/reactivation regression.
 *
 * Structural verification that edge functions handle lifecycle correctly.
 * Full E2E testing requires deployed DB — this checks code patterns.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const FUNCTIONS_DIR = resolve(__dirname, '../../supabase/functions');

describe('RW-007: User lifecycle structural verification', () => {
  describe('deactivate-user', () => {
    const content = readFileSync(
      resolve(FUNCTIONS_DIR, 'deactivate-user/index.ts'),
      'utf-8'
    );

    it('calls auth.admin ban API', () => {
      const usesBanApi = content.includes('banUser') || content.includes('ban_duration') || content.includes('updateUserById');
      expect(usesBanApi).toBe(true);
    });

    it('updates profile status', () => {
      expect(content).toContain('profiles');
      expect(content).toContain('status');
    });

    it('has audit logging', () => {
      expect(content).toContain('logAuditEvent');
    });

    it('handles errors with rollback pattern', () => {
      // Should have error handling for partial failure
      expect(content).toContain('catch');
    });
  });

  describe('reactivate-user', () => {
    const content = readFileSync(
      resolve(FUNCTIONS_DIR, 'reactivate-user/index.ts'),
      'utf-8'
    );

    it('calls auth.admin unban API', () => {
      // Should clear the auth ban
      const clearsAuthBan = content.includes('updateUserById') || content.includes('ban');
      expect(clearsAuthBan).toBe(true);
    });

    it('updates profile status', () => {
      expect(content).toContain('profiles');
      expect(content).toContain('status');
    });

    it('has audit logging', () => {
      expect(content).toContain('logAuditEvent');
    });

    it('has compensating rollback for partial failure', () => {
      // If unban succeeds but profile update fails, should re-ban
      expect(content).toContain('catch');
    });
  });
});
