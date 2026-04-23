import type { Locale } from '$lib/stores/locale.svelte';

/**
 * Locale-aware formatting helpers (Story 15.6).
 *
 * Map the internal app locale to a BCP 47 tag and defer to Intl.DateTimeFormat
 * so touched surfaces produce the right language for dates and times.
 * https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat
 */

export function toBcp47(locale: Locale): string {
	return locale === 'uk' ? 'uk-UA' : 'en-US';
}

function toDate(input: Date | string | number | null | undefined): Date | null {
	if (input == null) return null;
	const date = input instanceof Date ? input : new Date(input);
	return Number.isNaN(date.getTime()) ? null : date;
}

function safeFormat(
	locale: Locale,
	date: Date,
	options: Intl.DateTimeFormatOptions
): string {
	try {
		return new Intl.DateTimeFormat(toBcp47(locale), options).format(date);
	} catch (err) {
		// Swallow only invalid-option RangeErrors (MDN documents these as the
		// standard Intl failure mode). Other errors (TypeError, etc.) indicate
		// programmer mistakes and should surface instead of rendering blank UI.
		if (err instanceof RangeError) return '';
		throw err;
	}
}

export function formatDate(
	input: Date | string | number | null | undefined,
	locale: Locale,
	options: Intl.DateTimeFormatOptions = { year: 'numeric', month: '2-digit', day: '2-digit' }
): string {
	const date = toDate(input);
	if (!date) return '';
	return safeFormat(locale, date, options);
}

export function formatTime(
	input: Date | string | number | null | undefined,
	locale: Locale,
	options: Intl.DateTimeFormatOptions = { hour: '2-digit', minute: '2-digit' }
): string {
	const date = toDate(input);
	if (!date) return '';
	return safeFormat(locale, date, options);
}

export function formatDateTime(
	input: Date | string | number | null | undefined,
	locale: Locale
): string {
	const date = toDate(input);
	if (!date) return '';
	return safeFormat(locale, date, {
		year: 'numeric',
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit'
	});
}
