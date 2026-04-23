import axe from 'axe-core';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import PartialExtractionCard from './PartialExtractionCard.svelte';

describe('PartialExtractionCard', () => {
	const defaultProps = {
		status: 'partial' as const,
		documentId: 'doc-1',
		onReupload: vi.fn(),
		onKeepPartial: vi.fn(),
		isKeepingPartial: false
	};

	beforeEach(() => {
		vi.clearAllMocks();
	});

	// --- CSS class structure (AC 8) ---

	test('partial status renders with hc-recovery-card and hc-recovery-card-partial classes', () => {
		const { container } = renderComponent(PartialExtractionCard, defaultProps);
		const card = container.querySelector('.hc-recovery-card');
		expect(card).toBeTruthy();
		expect(card?.classList.contains('hc-recovery-card-partial')).toBe(true);
	});

	test('failed status renders with hc-recovery-card-failed class', () => {
		const { container } = renderComponent(PartialExtractionCard, {
			...defaultProps,
			status: 'failed'
		});
		const card = container.querySelector('.hc-recovery-card');
		expect(card).toBeTruthy();
		expect(card?.classList.contains('hc-recovery-card-failed')).toBe(true);
	});

	// --- Photo tips (AC 8) ---

	test('photo tips render with all 3 tips', () => {
		const { getByText } = renderComponent(PartialExtractionCard, defaultProps);
		expect(getByText('Good lighting')).toBeTruthy();
		expect(getByText('Flat surface')).toBeTruthy();
		expect(getByText('No shadows')).toBeTruthy();
	});

	test('photo tips section has header text', () => {
		const { getByText } = renderComponent(PartialExtractionCard, defaultProps);
		expect(getByText('Tips for a better photo')).toBeTruthy();
	});

	// --- Button styling classes (AC 8) ---

	test('re-upload button has primary accent styling class', () => {
		const { container } = renderComponent(PartialExtractionCard, defaultProps);
		const primary = container.querySelector('.hc-recovery-btn-primary');
		expect(primary).toBeTruthy();
		expect(primary?.textContent).toContain('Re-upload document');
	});

	test('keep-partial button has secondary styling class', () => {
		const { container } = renderComponent(PartialExtractionCard, defaultProps);
		const secondary = container.querySelector('.hc-recovery-btn-secondary');
		expect(secondary).toBeTruthy();
		expect(secondary?.textContent).toContain('Keep partial results');
	});

	test('keep-partial button not shown for failed status', () => {
		const { container } = renderComponent(PartialExtractionCard, {
			...defaultProps,
			status: 'failed'
		});
		expect(container.querySelector('.hc-recovery-btn-secondary')).toBeNull();
	});

	test('keep-partial button shows Saving text when isKeepingPartial', () => {
		const { container } = renderComponent(PartialExtractionCard, {
			...defaultProps,
			isKeepingPartial: true
		});
		const secondary = container.querySelector('.hc-recovery-btn-secondary');
		expect(secondary?.textContent).toContain('Saving');
		expect(secondary?.hasAttribute('disabled')).toBe(true);
	});

	// --- Heading text ---

	test('partial status shows correct heading', () => {
		const { getByText } = renderComponent(PartialExtractionCard, defaultProps);
		expect(getByText(/couldn't read everything clearly/i)).toBeTruthy();
	});

	test('failed status shows correct heading', () => {
		const { getByText } = renderComponent(PartialExtractionCard, {
			...defaultProps,
			status: 'failed'
		});
		expect(getByText(/extraction failed/i)).toBeTruthy();
	});

	// --- ARIA ---

	test('card has role="region" and aria-label for partial', () => {
		const { container } = renderComponent(PartialExtractionCard, defaultProps);
		const region = container.querySelector('[role="region"]');
		expect(region).toBeTruthy();
		expect(region?.getAttribute('aria-label')).toBe('Partial extraction recovery');
	});

	test('card has aria-label for failed', () => {
		const { container } = renderComponent(PartialExtractionCard, {
			...defaultProps,
			status: 'failed'
		});
		const region = container.querySelector('[role="region"]');
		expect(region?.getAttribute('aria-label')).toBe('Extraction failed recovery');
	});

	test('tips section has aria-label', () => {
		const { container } = renderComponent(PartialExtractionCard, defaultProps);
		const tips = container.querySelector('[aria-label="Photo tips for better extraction"]');
		expect(tips).toBeTruthy();
	});

	// --- Axe audit ---

	test('axe accessibility audit passes for partial status', async () => {
		const { container } = renderComponent(PartialExtractionCard, defaultProps);
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('axe accessibility audit passes for failed status', async () => {
		const { container } = renderComponent(PartialExtractionCard, {
			...defaultProps,
			status: 'failed'
		});
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
