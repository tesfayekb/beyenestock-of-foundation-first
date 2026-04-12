/**
 * RW-009: Admin UI component compliance.
 *
 * Verifies that admin panel pages use semantic design tokens
 * and do not contain raw color classes.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'fs';
import { resolve, join } from 'path';

const ADMIN_PAGES_DIR = resolve(__dirname, '../pages/admin');
const DASHBOARD_COMPONENTS_DIR = resolve(__dirname, '../components/dashboard');

/** Raw color classes that should NOT appear in admin pages */
const FORBIDDEN_PATTERNS = [
  /\btext-white\b/,
  /\btext-black\b/,
  /\bbg-white\b/,
  /\bbg-black\b/,
  /\bbg-gray-/,
  /\btext-gray-/,
  /\bbg-red-\d/,
  /\bbg-green-\d/,
  /\bbg-blue-\d/,
  /\btext-red-\d/,
  /\btext-green-\d/,
  /\btext-blue-\d/,
];

/** Allowed exceptions — third-party or SVG fills */
const EXCEPTION_PATTERNS = [
  /fill="/,      // SVG fills
  /viewBox/,     // SVG attributes
  /className.*?sr-only/, // screen reader
];

function getFilesRecursive(dir: string): string[] {
  const entries = readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...getFilesRecursive(fullPath));
    } else if (entry.name.endsWith('.tsx') || entry.name.endsWith('.ts')) {
      files.push(fullPath);
    }
  }
  return files;
}

describe('RW-009: Admin UI semantic token compliance', () => {
  const adminPages = readdirSync(ADMIN_PAGES_DIR)
    .filter((f) => f.endsWith('.tsx'))
    .map((f) => join(ADMIN_PAGES_DIR, f));

  for (const filePath of adminPages) {
    const fileName = filePath.split('/').pop()!;

    it(`${fileName} uses semantic tokens (no raw colors)`, () => {
      const content = readFileSync(filePath, 'utf-8');
      const lines = content.split('\n');

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // Skip SVG/exception lines
        if (EXCEPTION_PATTERNS.some((p) => p.test(line))) continue;

        for (const pattern of FORBIDDEN_PATTERNS) {
          if (pattern.test(line)) {
            // Allow if it's inside a comment
            const trimmed = line.trim();
            if (trimmed.startsWith('//') || trimmed.startsWith('*')) continue;
            
            expect.soft(false, `${fileName}:${i + 1} contains raw color: "${line.trim().substring(0, 80)}"`).toBe(true);
          }
        }
      }
    });
  }

  it('dashboard components use semantic tokens', () => {
    const dashFiles = getFilesRecursive(DASHBOARD_COMPONENTS_DIR);
    for (const filePath of dashFiles) {
      const content = readFileSync(filePath, 'utf-8');
      const lines = content.split('\n');
      const fileName = filePath.split('/').pop()!;

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (EXCEPTION_PATTERNS.some((p) => p.test(line))) continue;

        for (const pattern of FORBIDDEN_PATTERNS) {
          if (pattern.test(line)) {
            const trimmed = line.trim();
            if (trimmed.startsWith('//') || trimmed.startsWith('*')) continue;
            expect.soft(false, `${fileName}:${i + 1} contains raw color`).toBe(true);
          }
        }
      }
    }
  });
});
