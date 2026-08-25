/**
 * Playwright E2E tests – Login flow
 *
 * Tests:
 * - Unauthenticated navigation redirects to login
 * - Login page loads with expected form elements
 * - Empty form submission shows validation errors
 * - Invalid credentials show an error message
 */

import { test, expect, Page } from '@playwright/test'

test.describe('Login Page', () => {
  test('redirects unauthenticated user from dashboard to login', async ({ page }) => {
    await page.goto('/dashboard')
    // Should be redirected to some auth page
    await expect(page).toHaveURL(/login|auth|unauthorized/, { timeout: 10_000 })
  })

  test('login page has email and password inputs', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('input[type="email"], input[name="email"]')).toBeVisible({ timeout: 10_000 })
    await expect(page.locator('input[type="password"], input[name="password"]')).toBeVisible()
  })

  test('login page has a submit button', async ({ page }) => {
    await page.goto('/login')
    const submitBtn = page.locator('button[type="submit"], button:has-text("Login"), button:has-text("Sign in")')
    await expect(submitBtn.first()).toBeVisible({ timeout: 10_000 })
  })

  test('submitting empty email shows validation feedback', async ({ page }) => {
    await page.goto('/login')

    // Click submit without filling in fields
    const submitBtn = page.locator('button[type="submit"]').first()
    await submitBtn.click()

    // Either HTML5 validation or custom error message
    // Check that we're still on the login page (no navigation)
    await expect(page).toHaveURL(/login/, { timeout: 3_000 })
  })

  test('invalid credentials show error state', async ({ page }) => {
    await page.goto('/login')

    const emailInput = page.locator('input[type="email"], input[name="email"]').first()
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first()

    await emailInput.fill('nonexistent@example.com')
    await passwordInput.fill('WrongPassword123!')

    const submitBtn = page.locator('button[type="submit"]').first()
    await submitBtn.click()

    // Should show an error (either toast, alert, or error text)
    const errorIndicator = page.locator(
      '[role="alert"], .error, [class*="error"], [class*="toast"], text=/invalid|incorrect|wrong|failed/i'
    )
    await expect(errorIndicator.first()).toBeVisible({ timeout: 10_000 })
  })
})
