import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import {
	_catalogKeysForTests,
	_resetCatalogWarningsForTests,
	translateFrequency,
	translateRationale,
	translateTestName
} from './recommendation-catalog';

// Keep these arrays in sync with backend/app/health_data/service.py:
//   _GENERAL_PANELS[]   → (test_name, rationale, frequency)
//   _CONDITION_PANELS[] → (keywords, test_name, rationale, frequency)
// If the backend adds a new row, add it here and in recommendation-catalog.ts
// together — this test locks that invariant in.

const BACKEND_TEST_NAMES = [
	// _GENERAL_PANELS
	'Complete Blood Count (CBC)',
	'Comprehensive Metabolic Panel',
	'Lipid Panel',
	'HbA1c',
	'Vitamin D (25-OH)',
	'Iron & Ferritin',
	'PSA (Prostate-Specific Antigen)',
	// _CONDITION_PANELS
	'TSH + Free T4 Panel',
	'HbA1c + Fasting Glucose',
	'Comprehensive Metabolic Panel',
	'Lipid Panel',
	'CBC + Iron + Ferritin + B12',
	'Vitamin D (25-OH)',
	'tTG-IgA Antibodies',
	'Testosterone + FSH/LH Panel'
];

const BACKEND_FREQUENCIES = [
	'Annually',
	'Every 1–2 years',
	'Every 3 years',
	'Discuss with GP',
	'Every 6 months',
	'Every 3 months'
];

const BACKEND_RATIONALES = [
	// _GENERAL_PANELS
	'Screens for anemia, infection, and immune system conditions.',
	'Checks kidney/liver function, electrolytes, and blood sugar.',
	'Assesses cardiovascular risk by measuring cholesterol and triglycerides.',
	'Detects pre-diabetes and diabetes risk over the past 3 months.',
	'Vitamin D deficiency is common and affects bone and immune health.',
	'Iron deficiency is the most common nutritional deficiency worldwide.',
	'Early screening discussion for prostate health in men over 50.',
	// _CONDITION_PANELS
	'Monitors thyroid hormone levels to guide treatment and dose adjustments.',
	'Tracks blood sugar control and progression of diabetes or pre-diabetes.',
	'Monitors kidney function and electrolytes affected by hypertension.',
	'Tracks response to lifestyle changes or medication for cholesterol management.',
	'Comprehensive anemia workup to determine type and guide treatment.',
	'Tracks supplementation response and bone health status.',
	'Monitors celiac disease activity and adherence to a gluten-free diet.',
	'Tracks hormonal imbalances associated with PCOS.'
];

describe('recommendation-catalog', () => {
	beforeEach(() => {
		_resetCatalogWarningsForTests();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe('translateTestName', () => {
		test("returns the input verbatim when locale is 'en'", () => {
			for (const name of BACKEND_TEST_NAMES) {
				expect(translateTestName('en', name)).toBe(name);
			}
		});

		test('every backend test_name is present in the uk catalog (even if identical acronym)', () => {
			for (const name of BACKEND_TEST_NAMES) {
				expect(
					_catalogKeysForTests.testNames,
					`missing uk catalog entry for "${name}"`
				).toContain(name);
				expect(translateTestName('uk', name).length).toBeGreaterThan(0);
			}
		});

		test('prose test_name values actually change under uk', () => {
			// Acronyms like 'HbA1c' stay identical by design — sample a clearly-
			// prose entry so a regression that drops the uk catalog is caught.
			expect(translateTestName('uk', 'TSH + Free T4 Panel')).not.toBe(
				'TSH + Free T4 Panel'
			);
			expect(translateTestName('uk', 'Lipid Panel')).not.toBe('Lipid Panel');
		});

		test('falls back to English input and warns when the key is unknown', () => {
			const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

			expect(translateTestName('uk', 'Unknown Future Panel')).toBe('Unknown Future Panel');
			expect(warnSpy).toHaveBeenCalledWith(
				expect.stringContaining('Missing test_name translation for "Unknown Future Panel"')
			);
		});
	});

	describe('translateFrequency', () => {
		test("returns the input verbatim when locale is 'en'", () => {
			for (const freq of BACKEND_FREQUENCIES) {
				expect(translateFrequency('en', freq)).toBe(freq);
			}
		});

		test('every backend frequency is present in the uk catalog', () => {
			for (const freq of BACKEND_FREQUENCIES) {
				expect(
					_catalogKeysForTests.frequencies,
					`missing uk catalog entry for "${freq}"`
				).toContain(freq);
				expect(translateFrequency('uk', freq).length).toBeGreaterThan(0);
			}
		});

		test('prose frequency values actually change under uk', () => {
			expect(translateFrequency('uk', 'Every 6 months')).not.toBe('Every 6 months');
			expect(translateFrequency('uk', 'Annually')).not.toBe('Annually');
		});

		test('falls back to English input and warns when the key is unknown', () => {
			const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

			expect(translateFrequency('uk', 'Every 90 years')).toBe('Every 90 years');
			expect(warnSpy).toHaveBeenCalledWith(
				expect.stringContaining('Missing frequency translation for "Every 90 years"')
			);
		});
	});

	describe('translateRationale', () => {
		test("returns the input verbatim when locale is 'en'", () => {
			for (const rat of BACKEND_RATIONALES) {
				expect(translateRationale('en', rat)).toBe(rat);
			}
		});

		test('every backend rationale is present in the uk catalog', () => {
			for (const rat of BACKEND_RATIONALES) {
				expect(
					_catalogKeysForTests.rationales,
					`missing uk catalog entry for "${rat}"`
				).toContain(rat);
				expect(translateRationale('uk', rat).length).toBeGreaterThan(0);
			}
		});

		test('rationale values change under uk', () => {
			expect(
				translateRationale(
					'uk',
					'Monitors thyroid hormone levels to guide treatment and dose adjustments.'
				)
			).not.toBe(
				'Monitors thyroid hormone levels to guide treatment and dose adjustments.'
			);
		});

		test('falls back to English input and warns when the key is unknown', () => {
			const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

			expect(translateRationale('uk', 'A totally new rationale string.')).toBe(
				'A totally new rationale string.'
			);
			expect(warnSpy).toHaveBeenCalledWith(
				expect.stringContaining(
					'Missing rationale translation for "A totally new rationale string."'
				)
			);
		});
	});

	test('exposed _catalogKeysForTests reports non-empty key sets', () => {
		expect(_catalogKeysForTests.testNames.length).toBeGreaterThan(0);
		expect(_catalogKeysForTests.frequencies.length).toBeGreaterThan(0);
		expect(_catalogKeysForTests.rationales.length).toBeGreaterThan(0);
	});
});
