import { describe, expect, test } from 'vitest';
import { DEFAULT_NEAR_BOTTOM_THRESHOLD_PX, isNearBottom } from './ai-chat-scroll';

function fakeEl(scrollHeight: number, scrollTop: number, clientHeight: number): HTMLElement {
	return { scrollHeight, scrollTop, clientHeight } as unknown as HTMLElement;
}

describe('isNearBottom', () => {
	test('returns true when element is null or undefined (fresh mount)', () => {
		expect(isNearBottom(null)).toBe(true);
		expect(isNearBottom(undefined)).toBe(true);
	});

	test('returns true when scrollTop equals maximum', () => {
		// scrollTop = scrollHeight - clientHeight => distance = 0
		expect(isNearBottom(fakeEl(1000, 900, 100))).toBe(true);
	});

	test('returns true when within default threshold of bottom', () => {
		// distance = 1000 - 880 - 100 = 20, under 24px threshold
		expect(isNearBottom(fakeEl(1000, 880, 100))).toBe(true);
	});

	test('returns false when scrolled well above the threshold', () => {
		// distance = 1000 - 500 - 100 = 400
		expect(isNearBottom(fakeEl(1000, 500, 100))).toBe(false);
	});

	test('returns true at exactly the threshold boundary', () => {
		// distance = 1000 - 876 - 100 = 24, equal to threshold => sticky
		expect(isNearBottom(fakeEl(1000, 876, 100))).toBe(true);
	});

	test('returns false just past the threshold boundary', () => {
		// distance = 25, just outside threshold
		expect(isNearBottom(fakeEl(1000, 875, 100))).toBe(false);
	});

	test('honors a custom threshold override', () => {
		// distance = 100; strict threshold (4px) rejects, lax threshold (200px) accepts
		expect(isNearBottom(fakeEl(1000, 800, 100), 4)).toBe(false);
		expect(isNearBottom(fakeEl(1000, 800, 100), 200)).toBe(true);
	});

	test('handles fractional scrollTop (browsers may report fractional values)', () => {
		// scrollTop is fractional but scrollHeight/clientHeight are rounded;
		// MDN notes this is why we use a threshold comparison.
		expect(isNearBottom(fakeEl(1000, 899.7, 100))).toBe(true);
		expect(isNearBottom(fakeEl(1000, 899.4, 100))).toBe(true);
	});

	test('default threshold is exposed for consumers', () => {
		expect(DEFAULT_NEAR_BOTTOM_THRESHOLD_PX).toBe(24);
	});
});
