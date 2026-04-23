import { describe, expect, test } from 'vitest';
import { selectPlural } from './plural';

const EN_DOCS = { one: 'Document', other: 'Documents' };
const UK_DOCS = { one: 'Документ', few: 'Документи', many: 'Документів', other: 'Документа' };

describe('selectPlural — en', () => {
	test('one for 1', () => {
		expect(selectPlural('en', 1, EN_DOCS)).toBe('Document');
	});
	test('other for 0', () => {
		expect(selectPlural('en', 0, EN_DOCS)).toBe('Documents');
	});
	test('other for 2, 5, 100', () => {
		expect(selectPlural('en', 2, EN_DOCS)).toBe('Documents');
		expect(selectPlural('en', 5, EN_DOCS)).toBe('Documents');
		expect(selectPlural('en', 100, EN_DOCS)).toBe('Documents');
	});
});

describe('selectPlural — uk (3 forms per CLDR)', () => {
	test('one for 1, 21 (ends in 1 but not 11)', () => {
		expect(selectPlural('uk', 1, UK_DOCS)).toBe('Документ');
		expect(selectPlural('uk', 21, UK_DOCS)).toBe('Документ');
	});

	test('few for 2, 3, 4, 22-24 (2–4 endings, not 12–14)', () => {
		expect(selectPlural('uk', 2, UK_DOCS)).toBe('Документи');
		expect(selectPlural('uk', 3, UK_DOCS)).toBe('Документи');
		expect(selectPlural('uk', 4, UK_DOCS)).toBe('Документи');
		expect(selectPlural('uk', 22, UK_DOCS)).toBe('Документи');
	});

	test('many for 0, 5-20, 25+', () => {
		expect(selectPlural('uk', 0, UK_DOCS)).toBe('Документів');
		expect(selectPlural('uk', 5, UK_DOCS)).toBe('Документів');
		expect(selectPlural('uk', 11, UK_DOCS)).toBe('Документів');
		expect(selectPlural('uk', 14, UK_DOCS)).toBe('Документів');
		expect(selectPlural('uk', 20, UK_DOCS)).toBe('Документів');
		expect(selectPlural('uk', 100, UK_DOCS)).toBe('Документів');
	});

	test('falls back to other when few/many omitted', () => {
		const minimal = { one: 'x', other: 'y' };
		expect(selectPlural('uk', 2, minimal)).toBe('y');
		expect(selectPlural('uk', 5, minimal)).toBe('y');
	});
});
