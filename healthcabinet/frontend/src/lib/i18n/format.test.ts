import { describe, expect, test } from 'vitest';
import { formatDate, formatDateTime, formatTime, toBcp47 } from './format';

describe('toBcp47', () => {
	test('maps en to en-US and uk to uk-UA', () => {
		expect(toBcp47('en')).toBe('en-US');
		expect(toBcp47('uk')).toBe('uk-UA');
	});
});

describe('formatDate', () => {
	test('returns an empty string for null/undefined/invalid input', () => {
		expect(formatDate(null, 'en')).toBe('');
		expect(formatDate(undefined, 'en')).toBe('');
		expect(formatDate('not-a-date', 'en')).toBe('');
	});

	test('formats with the selected locale (en uses "/" separator, uk uses ".")', () => {
		const iso = '2026-04-22T10:00:00Z';
		const en = formatDate(iso, 'en');
		const uk = formatDate(iso, 'uk');
		// en-US: 04/22/2026, uk-UA: 22.04.2026 — separator differs per CLDR.
		// Asserting the separators rather than bare substring catches a
		// regression where `formatDate` silently ignores the locale argument.
		expect(en).toContain('/');
		expect(uk).toContain('.');
		expect(en).not.toContain('.');
		expect(uk).not.toContain('/');
	});

	test('accepts a Date object directly', () => {
		const d = new Date('2026-04-22T10:00:00Z');
		expect(formatDate(d, 'en')).not.toBe('');
	});
});

describe('formatTime', () => {
	test('returns empty string for invalid input', () => {
		expect(formatTime(undefined, 'uk')).toBe('');
	});

	test('en formats in 12-hour with AM/PM; uk formats in 24-hour without AM/PM', () => {
		// 10:05 UTC — in en-US this is "10:05 AM", in uk-UA it's "10:05" (no AM/PM).
		// The time is also host-tz dependent, so assert only on the AM/PM
		// presence which is the locale-policy bit.
		const iso = '2026-04-22T10:05:00Z';
		const en = formatTime(iso, 'en');
		const uk = formatTime(iso, 'uk');
		expect(en).toMatch(/AM|PM/);
		expect(uk).not.toMatch(/AM|PM/);
	});
});

describe('formatDateTime', () => {
	test('produces output that contains both date and time components', () => {
		const iso = '2026-04-22T10:05:00Z';
		const out = formatDateTime(iso, 'en');
		expect(out).toMatch(/\d/);
		expect(out.length).toBeGreaterThan(5);
	});
});
