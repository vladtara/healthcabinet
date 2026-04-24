import type { Locale } from '$lib/stores/locale.svelte';

/**
 * Frontend translation for the fixed baseline-recommendation catalog returned
 * by `GET /api/v1/users/me/baseline`. Backend response strings come verbatim
 * from `backend/app/health_data/service.py` (`_GENERAL_PANELS` and
 * `_CONDITION_PANELS`), which store canonical English.
 *
 * Per Story 15.6 AC 5 and Story 15.7 scope, backend payloads stay unchanged;
 * this module maps English → Ukrainian at render time. An unknown input falls
 * through to the original English string so a newly-added backend catalog
 * entry degrades gracefully rather than throwing. `recommendation-catalog.test.ts`
 * locks in full coverage for the current backend catalog so a missed
 * translation fails at PR review.
 */

const testNamesUk: Record<string, string> = {
	// _GENERAL_PANELS
	'Complete Blood Count (CBC)': 'Загальний аналіз крові (CBC)',
	'Comprehensive Metabolic Panel': 'Комплексна метаболічна панель',
	'Lipid Panel': 'Ліпідна панель',
	HbA1c: 'HbA1c',
	'Vitamin D (25-OH)': 'Вітамін D (25-OH)',
	'Iron & Ferritin': 'Залізо і феритин',
	'PSA (Prostate-Specific Antigen)': 'ПСА (простат-специфічний антиген)',
	// _CONDITION_PANELS
	'TSH + Free T4 Panel': 'Панель ТТГ + вільний T4',
	'HbA1c + Fasting Glucose': 'HbA1c + глюкоза натщесерце',
	'CBC + Iron + Ferritin + B12': 'Загальний аналіз крові + залізо + феритин + B12',
	'tTG-IgA Antibodies': 'Антитіла tTG-IgA',
	'Testosterone + FSH/LH Panel': 'Тестостерон + панель ФСГ/ЛГ'
};

const frequenciesUk: Record<string, string> = {
	// _GENERAL_PANELS
	Annually: 'Щорічно',
	'Every 1–2 years': 'Кожні 1–2 роки',
	'Every 3 years': 'Кожні 3 роки',
	'Discuss with GP': 'Обговорити з лікарем',
	// _CONDITION_PANELS
	'Every 6 months': 'Кожні 6 місяців',
	'Every 3 months': 'Кожні 3 місяці'
};

const rationalesUk: Record<string, string> = {
	// _GENERAL_PANELS
	'Screens for anemia, infection, and immune system conditions.':
		'Перевіряє на анемію, інфекції та стани імунної системи.',
	'Checks kidney/liver function, electrolytes, and blood sugar.':
		'Перевіряє функцію нирок/печінки, електроліти та рівень цукру в крові.',
	'Assesses cardiovascular risk by measuring cholesterol and triglycerides.':
		'Оцінює серцево-судинний ризик шляхом вимірювання холестерину і тригліцеридів.',
	'Detects pre-diabetes and diabetes risk over the past 3 months.':
		'Виявляє переддіабет і ризик діабету за останні 3 місяці.',
	'Vitamin D deficiency is common and affects bone and immune health.':
		'Дефіцит вітаміну D поширений і впливає на кістки та імунну систему.',
	'Iron deficiency is the most common nutritional deficiency worldwide.':
		'Дефіцит заліза — найпоширеніший харчовий дефіцит у світі.',
	'Early screening discussion for prostate health in men over 50.':
		'Раннє обговорення скринінгу здоровʼя простати для чоловіків після 50 років.',
	// _CONDITION_PANELS
	'Monitors thyroid hormone levels to guide treatment and dose adjustments.':
		'Моніторинг рівня гормонів щитоподібної залози для корекції лікування і дози.',
	'Tracks blood sugar control and progression of diabetes or pre-diabetes.':
		'Відстежує контроль рівня цукру в крові та прогресування діабету або переддіабету.',
	'Monitors kidney function and electrolytes affected by hypertension.':
		'Моніторинг функції нирок і електролітів, на які впливає гіпертонія.',
	'Tracks response to lifestyle changes or medication for cholesterol management.':
		'Відстежує реакцію на зміни способу життя або ліки для контролю холестерину.',
	'Comprehensive anemia workup to determine type and guide treatment.':
		'Комплексне обстеження анемії для визначення типу та вибору лікування.',
	'Tracks supplementation response and bone health status.':
		'Відстежує реакцію на добавки та стан здоровʼя кісток.',
	'Monitors celiac disease activity and adherence to a gluten-free diet.':
		'Моніторинг активності целіакії та дотримання безглютенової дієти.',
	'Tracks hormonal imbalances associated with PCOS.':
		'Відстежує гормональні порушення, повʼязані з СПКЯ.'
};

const warnedMissingKeys = new Set<string>();

function warnMissingTranslation(kind: string, key: string) {
	if (import.meta.env.PROD) return;

	const cacheKey = `${kind}:${key}`;
	if (warnedMissingKeys.has(cacheKey)) return;

	warnedMissingKeys.add(cacheKey);
	console.warn(
		`[recommendation-catalog] Missing ${kind} translation for "${key}". Falling back to backend string.`
	);
}

function translateCatalogEntry(
	locale: Locale,
	kind: 'test_name' | 'frequency' | 'rationale',
	en: string,
	catalog: Record<string, string>
): string {
	if (locale === 'en') return en;

	const translated = catalog[en];
	if (translated) return translated;

	warnMissingTranslation(kind, en);
	return en;
}

export function translateTestName(locale: Locale, en: string): string {
	return translateCatalogEntry(locale, 'test_name', en, testNamesUk);
}

export function translateFrequency(locale: Locale, en: string): string {
	return translateCatalogEntry(locale, 'frequency', en, frequenciesUk);
}

export function translateRationale(locale: Locale, en: string): string {
	return translateCatalogEntry(locale, 'rationale', en, rationalesUk);
}

/** Test-only: the full English key sets the backend catalog ships. */
export const _catalogKeysForTests = {
	testNames: Object.keys(testNamesUk),
	frequencies: Object.keys(frequenciesUk),
	rationales: Object.keys(rationalesUk)
};

export function _resetCatalogWarningsForTests() {
	warnedMissingKeys.clear();
}
