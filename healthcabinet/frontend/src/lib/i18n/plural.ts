import type { Locale } from '$lib/stores/locale.svelte';
import { toBcp47 } from './format';

/**
 * CLDR plural categories for the supported locales:
 *   en — 'one' | 'other'
 *   uk — 'one' | 'few' | 'many' | 'other'
 *
 * English collapses to a 1/many binary; Ukrainian has 3 grammatically
 * meaningful forms (1 / 2–4 / 5+, 0) that native speakers expect.
 * Callers pass a `PluralForms` bundle and receive the correct form for
 * the given count + locale. Unsupported categories silently fall back
 * to `other`, which covers both locales' "everything else" bucket.
 *
 * Source of truth for form names:
 *   https://unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html
 */

export interface PluralForms {
	/** `one` — n = 1. */
	one: string;
	/** `other` — default / English plural and uk `other` (fractional-like). */
	other: string;
	/** `few` — Ukrainian n ending 2–4 (except 12–14). Optional; falls back to `other`. */
	few?: string;
	/** `many` — Ukrainian n=0, 5–20, and endings 0 / 5–9 / 11–14. Optional; falls back to `other`. */
	many?: string;
}

export function selectPlural(locale: Locale, count: number, forms: PluralForms): string {
	const category = new Intl.PluralRules(toBcp47(locale)).select(count);
	switch (category) {
		case 'one':
			return forms.one;
		case 'few':
			return forms.few ?? forms.other;
		case 'many':
			return forms.many ?? forms.other;
		case 'two':
		case 'zero':
		case 'other':
		default:
			return forms.other;
	}
}
