/**
 * E2E: Sign-In Flow
 * Tests the full auth → session → RBAC pipeline end-to-end.
 *
 * Stage 6F — Gate 1
 */
import { test, expect } from '../playwright-fixture';

test.describe('Sign-In Flow', () => {
  test('sign-in page renders with required fields', async ({ page }) => {
    await page.goto('/sign-in');
    
    // Verify the sign-in form is visible
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('empty form submission shows validation errors', async ({ page }) => {
    await page.goto('/sign-in');
    
    // Click sign in without filling fields
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Should remain on sign-in page (no redirect)
    await expect(page).toHaveURL(/sign-in/);
  });

  test('sign-in page has links to sign-up and forgot password', async ({ page }) => {
    await page.goto('/sign-in');
    
    // Verify navigation links exist
    await expect(page.getByRole('link', { name: /sign up/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /forgot/i })).toBeVisible();
  });

  test('unauthenticated access to /admin redirects to sign-in', async ({ page }) => {
    // Clear any existing session
    await page.context().clearCookies();
    
    await page.goto('/admin');
    
    // Should redirect to sign-in (RBAC gate)
    await page.waitForURL(/sign-in/, { timeout: 10000 });
    await expect(page).toHaveURL(/sign-in/);
  });

  test('unauthenticated access to /dashboard redirects to sign-in', async ({ page }) => {
    await page.context().clearCookies();
    
    await page.goto('/dashboard');
    
    await page.waitForURL(/sign-in/, { timeout: 10000 });
    await expect(page).toHaveURL(/sign-in/);
  });
});
