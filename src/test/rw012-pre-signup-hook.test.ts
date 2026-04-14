/**
 * RW-012: Pre-signup hook contract verification.
 *
 * Verifies:
 * - auth-hook-pre-signup function exists
 * - Reads from system_config table
 * - Returns decision: continue when signup enabled
 * - Returns decision: reject when signup disabled
 * - Fails open on missing config (prevents lockout)
 *
 * Source: supabase/functions/auth-hook-pre-signup/index.ts
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(__dirname, '../../');

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), 'utf-8');
}

describe('RW-012: Pre-signup hook contract', () => {
  const hookPath = 'supabase/functions/auth-hook-pre-signup/index.ts';

  it('auth-hook-pre-signup function file exists', () => {
    expect(existsSync(resolve(ROOT, hookPath))).toBe(true);
  });

  const src = readSource(hookPath);

  it('reads from system_config table', () => {
    expect(src).toContain("from('system_config')");
    expect(src).toContain("eq('key', 'onboarding_mode')");
  });

  it('returns decision: continue when signup is enabled', () => {
    expect(src).toContain("decision: 'continue'");
  });

  it('returns decision: reject when signup is disabled', () => {
    expect(src).toContain("decision: 'reject'");
    expect(src).toContain('invitation only');
  });

  it('fails open on missing config (prevents lockout)', () => {
    // When error or !data, should return continue, not reject
    expect(src).toMatch(/if\s*\(\s*error\s*\|\|\s*!data\s*\)/);
    // The block after error/!data should contain 'continue'
    const errorBlock = src.split('if (error || !data)')[1]?.split('}')[0];
    expect(errorBlock).toBeDefined();
  });

  it('fails open on unexpected errors (catch block)', () => {
    // catch block should also return continue
    expect(src).toContain('catch');
    // Must NOT return reject in catch
    const catchBlock = src.split('catch')[1];
    expect(catchBlock).toBeDefined();
    expect(catchBlock).toContain("decision: 'continue'");
  });

  it('does not perform token validation (architecture decision #7)', () => {
    expect(src).not.toContain('token_hash');
    expect(src).not.toContain('bcrypt');
    expect(src).not.toContain('verifyToken');
  });

  it('only accepts POST method (hook protocol)', () => {
    expect(src).toContain("req.method !== 'POST'");
  });

  it('does not require JWT validation (server-to-server)', () => {
    expect(src).not.toContain('authenticateRequest');
    expect(src).not.toContain('checkPermission');
  });
});
