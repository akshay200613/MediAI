/**
 * Unit tests for apps/frontend/src/lib/utils.ts
 * Tests all exported utility functions in isolation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  formatDate,
  formatDateTime,
  formatTimeAgo,
  getStatusBadgeClass,
  getInitials,
  extractErrorMessage,
  cn,
} from '@/lib/utils'

// ── cn (class merger) ────────────────────────────────────────────────────────

describe('cn', () => {
  it('merges class strings', () => {
    expect(cn('foo', 'bar')).toContain('foo')
    expect(cn('foo', 'bar')).toContain('bar')
  })

  it('handles undefined values gracefully', () => {
    expect(() => cn(undefined as any)).not.toThrow()
  })

  it('deduplicates conflicting tailwind classes', () => {
    const result = cn('text-red-500', 'text-blue-500')
    // twMerge should keep only the last
    expect(result).toBe('text-blue-500')
  })
})

// ── formatDate ───────────────────────────────────────────────────────────────

describe('formatDate', () => {
  it('formats a known date string correctly', () => {
    // 2024-06-15 in various locales should at least contain the year and day
    const result = formatDate('2024-06-15T00:00:00.000Z')
    expect(result).toContain('2024')
    expect(result).toMatch(/15|Jun/)
  })

  it('returns a non-empty string', () => {
    expect(formatDate('2023-01-01T00:00:00Z').length).toBeGreaterThan(0)
  })
})

// ── formatDateTime ────────────────────────────────────────────────────────────

describe('formatDateTime', () => {
  it('includes time in the output', () => {
    const result = formatDateTime('2024-01-01T14:30:00Z')
    // Should contain AM/PM indicator
    expect(result).toMatch(/AM|PM/)
  })

  it('includes the year', () => {
    const result = formatDateTime('2024-06-15T10:00:00Z')
    expect(result).toContain('2024')
  })
})

// ── formatTimeAgo ─────────────────────────────────────────────────────────────

describe('formatTimeAgo', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-06-15T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns "just now" for very recent timestamps', () => {
    const recent = new Date('2024-06-15T11:59:45Z').toISOString()
    expect(formatTimeAgo(recent)).toBe('just now')
  })

  it('returns minutes ago for timestamps within the last hour', () => {
    const thirtyMinAgo = new Date('2024-06-15T11:30:00Z').toISOString()
    expect(formatTimeAgo(thirtyMinAgo)).toBe('30m ago')
  })

  it('returns hours ago for timestamps within the last 24h', () => {
    const threeHoursAgo = new Date('2024-06-15T09:00:00Z').toISOString()
    expect(formatTimeAgo(threeHoursAgo)).toBe('3h ago')
  })

  it('returns days ago for timestamps older than 24h', () => {
    const twoDaysAgo = new Date('2024-06-13T12:00:00Z').toISOString()
    expect(formatTimeAgo(twoDaysAgo)).toBe('2d ago')
  })
})

// ── getStatusBadgeClass ───────────────────────────────────────────────────────

describe('getStatusBadgeClass', () => {
  it('returns badge-blue for scheduled', () => {
    expect(getStatusBadgeClass('scheduled')).toBe('badge-blue')
  })

  it('returns badge-green for confirmed', () => {
    expect(getStatusBadgeClass('confirmed')).toBe('badge-green')
  })

  it('returns badge-green for completed', () => {
    expect(getStatusBadgeClass('completed')).toBe('badge-green')
  })

  it('returns badge-red for cancelled', () => {
    expect(getStatusBadgeClass('cancelled')).toBe('badge-red')
  })

  it('returns badge-yellow for in_progress', () => {
    expect(getStatusBadgeClass('in_progress')).toBe('badge-yellow')
  })

  it('returns badge-gray for no_show', () => {
    expect(getStatusBadgeClass('no_show')).toBe('badge-gray')
  })

  it('returns badge-gray for unknown status', () => {
    expect(getStatusBadgeClass('unknown_status_xyz')).toBe('badge-gray')
  })

  it('returns badge-green for active', () => {
    expect(getStatusBadgeClass('active')).toBe('badge-green')
  })
})

// ── getInitials ───────────────────────────────────────────────────────────────

describe('getInitials', () => {
  it('returns two-character initials for a full name', () => {
    expect(getInitials('John Smith')).toBe('JS')
  })

  it('handles a single-word name', () => {
    expect(getInitials('Alice')).toBe('A')
  })

  it('handles three-word names by taking first two initials', () => {
    expect(getInitials('Mary Jane Watson')).toBe('MJ')
  })

  it('returns uppercase initials', () => {
    expect(getInitials('john doe')).toBe('JD')
  })

  it('handles empty string gracefully', () => {
    expect(() => getInitials('')).not.toThrow()
  })
})

// ── extractErrorMessage ───────────────────────────────────────────────────────

describe('extractErrorMessage', () => {
  it('returns default message for null/undefined', () => {
    expect(extractErrorMessage(null)).toBe('An unexpected error occurred')
    expect(extractErrorMessage(undefined)).toBe('An unexpected error occurred')
  })

  it('extracts string detail from axios error response', () => {
    const err = { response: { data: { detail: 'Email already exists' } } }
    expect(extractErrorMessage(err)).toBe('Email already exists')
  })

  it('extracts first item from array detail', () => {
    const err = { response: { data: { detail: ['Invalid email', 'Required field'] } } }
    expect(extractErrorMessage(err)).toBe('Invalid email, Required field')
  })

  it('extracts msg from array of objects', () => {
    const err = { response: { data: { detail: [{ msg: 'Too short' }] } } }
    expect(extractErrorMessage(err)).toBe('Too short')
  })

  it('extracts msg from object detail', () => {
    const err = { response: { data: { detail: { msg: 'Server error' } } } }
    expect(extractErrorMessage(err)).toBe('Server error')
  })

  it('falls back to message property if no response.data.detail', () => {
    const err = { message: 'Network Error' }
    expect(extractErrorMessage(err)).toBe('Network Error')
  })

  it('converts non-object errors to string', () => {
    expect(extractErrorMessage('plain string error')).toBe('plain string error')
  })
})
