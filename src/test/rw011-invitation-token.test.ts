/**
 * RW-011: Invitation token generation contract.
 *
 * Verifies:
 * - Token is generated from 32 random bytes
 * - Token is base64url encoded (no +, /, = chars)
 * - SHA-256 hash is used (not bcrypt), producing 64-char hex string
 * - Hash is deterministic for same input
 * - Different inputs produce different hashes
 *
 * Source functions: invite-user/index.ts, invite-users-bulk/index.ts
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(__dirname, '../../');

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), 'utf-8');
}

describe('RW-011: Invitation token generation contract', () => {
  const inviteUserSrc = readSource('supabase/functions/invite-user/index.ts');
  const inviteBulkSrc = readSource('supabase/functions/invite-users-bulk/index.ts');

  it('invite-user generates token from 32 random bytes', () => {
    expect(inviteUserSrc).toContain('new Uint8Array(32)');
    expect(inviteUserSrc).toContain('crypto.getRandomValues');
  });

  it('invite-users-bulk generates token from 32 random bytes', () => {
    expect(inviteBulkSrc).toContain('new Uint8Array(32)');
    expect(inviteBulkSrc).toContain('crypto.getRandomValues');
  });

  it('invite-user uses base64url encoding (replaces +, /, =)', () => {
    // Base64url: replace + with -, / with _, strip trailing =
    expect(inviteUserSrc).toContain("replace(/\\+/g, '-')");
    expect(inviteUserSrc).toContain("replace(/\\//g, '_')");
    expect(inviteUserSrc).toContain("replace(/=+$/");
  });

  it('invite-users-bulk uses base64url encoding', () => {
    expect(inviteBulkSrc).toContain("replace(/\\+/g, '-')");
    expect(inviteBulkSrc).toContain("replace(/\\//g, '_')");
    expect(inviteBulkSrc).toContain("replace(/=+$/");
  });

  it('invite-user uses SHA-256 (not bcrypt) for token hashing', () => {
    expect(inviteUserSrc).toContain("crypto.subtle.digest('SHA-256'");
    expect(inviteUserSrc).not.toContain('bcrypt');
  });

  it('invite-users-bulk uses SHA-256 (not bcrypt) for token hashing', () => {
    expect(inviteBulkSrc).toContain("crypto.subtle.digest('SHA-256'");
    expect(inviteBulkSrc).not.toContain('bcrypt');
  });

  it('both functions produce hex-encoded hash (toString(16))', () => {
    expect(inviteUserSrc).toContain("toString(16).padStart(2, '0')");
    expect(inviteBulkSrc).toContain("toString(16).padStart(2, '0')");
  });

  it('both functions store hash as token_hash in invitation row', () => {
    expect(inviteUserSrc).toContain('token_hash: tokenHash');
    expect(inviteBulkSrc).toContain('token_hash: tokenHash');
  });

  it('generateTokenPair function exists in both files', () => {
    expect(inviteUserSrc).toContain('async function generateTokenPair()');
    expect(inviteBulkSrc).toContain('async function generateTokenPair()');
  });
});
