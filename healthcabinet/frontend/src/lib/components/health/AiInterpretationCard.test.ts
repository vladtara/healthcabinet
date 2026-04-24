/**
 * Unit tests for AiInterpretationCard component (AC: #4).
 */

import axe from 'axe-core';
import { fireEvent, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { QueryClient } from '@tanstack/query-core';
import { render } from '@testing-library/svelte';
import AiInterpretationCardTestWrapper from './AiInterpretationCardTestWrapper.svelte';

vi.mock('$lib/api/ai', () => ({
	getDocumentInterpretation: vi.fn()
}));

import { getDocumentInterpretation } from '$lib/api/ai';

const mockGetInterpretation = vi.mocked(getDocumentInterpretation);

function makeQueryClient() {
	return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderCard(documentId = 'doc-1') {
	const queryClient = makeQueryClient();
	const result = render(AiInterpretationCardTestWrapper, {
		props: { queryClient, documentId }
	});
	return { ...result, queryClient };
}

function makeInterpretationResponse(overrides: Record<string, unknown> = {}) {
	return {
		document_id: 'doc-1',
		interpretation: 'Your glucose is within the normal range.',
		model_version: 'claude-sonnet-4-6',
		generated_at: '2026-03-26T00:00:00Z',
		reasoning: null,
		...overrides
	};
}

function makeReasoning(overrides: Record<string, unknown> = {}) {
	return {
		values_referenced: [
			{
				name: 'Glucose',
				value: 91,
				unit: 'mg/dL',
				ref_low: 70,
				ref_high: 99,
				status: 'normal'
			}
		],
		uncertainty_flags: [],
		prior_documents_referenced: [],
		...overrides
	};
}

describe('AiInterpretationCard', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('renders skeleton when query is loading', () => {
		// Return a promise that never resolves so query stays pending
		mockGetInterpretation.mockReturnValue(new Promise(() => {}));
		const { container } = renderCard();
		expect(container.querySelector('[aria-busy="true"]')).toBeTruthy();
	});

	test('renders interpretation text and disclaimer when query resolves', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse());
		const { getByText } = renderCard();

		await waitFor(() => {
			expect(getByText('Your glucose is within the normal range.')).toBeTruthy();
		});

		// Disclaimer must be visible
		expect(getByText(/educational purposes only/i)).toBeTruthy();
	});

	test('renders nothing (no section) on 404 response', async () => {
		mockGetInterpretation.mockRejectedValue({
			status: 404,
			title: 'Not Found',
			type: 'about:blank'
		});
		const { container } = renderCard();

		await waitFor(() => {
			expect(container.querySelector('section')).toBeNull();
		});
	});

	test('aria-live="polite" region is present when interpretation is loaded', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				interpretation: 'Your ferritin is slightly low.'
			})
		);
		const { container } = renderCard();

		await waitFor(() => {
			expect(container.querySelector('[aria-live="polite"]')).toBeTruthy();
		});
	});

	test('disclaimer text is present in DOM (not sr-only, not aria-hidden)', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				interpretation: 'Your values look normal.',
				model_version: null
			})
		);
		const { container } = renderCard();

		await waitFor(() => {
			const disclaimer = container.querySelector('p.text-\\[11px\\]');
			expect(disclaimer).toBeTruthy();
			expect(disclaimer?.getAttribute('aria-hidden')).not.toBe('true');
			const srOnly = disclaimer?.classList.contains('sr-only');
			expect(srOnly).toBeFalsy();
		});
	});

	test('shows muted error message on non-404 error', async () => {
		mockGetInterpretation.mockRejectedValue({
			status: 500,
			title: 'Internal Server Error',
			type: 'about:blank'
		});
		const { getByText } = renderCard();

		await waitFor(() => {
			expect(getByText(/Interpretation unavailable/i)).toBeTruthy();
		});
	});

	test('axe-core audit passes on loaded state', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				interpretation: 'Your hemoglobin is within the normal range.'
			})
		);
		const { container } = renderCard();

		await waitFor(() => {
			expect(container.querySelector('section')).toBeTruthy();
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('renders no toggle when reasoning is null', async () => {
		mockGetInterpretation.mockResolvedValue(makeInterpretationResponse({ reasoning: null }));
		const { queryByRole, getByText } = renderCard();

		await waitFor(() => {
			expect(getByText('Your glucose is within the normal range.')).toBeTruthy();
		});

		expect(queryByRole('button', { name: /show reasoning/i })).toBeNull();
	});

	test('renders toggle when reasoning is present', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				reasoning: makeReasoning()
			})
		);
		const { getByRole } = renderCard();

		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});
	});

	test('panel is hidden by default', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				reasoning: makeReasoning()
			})
		);
		const { container, getByRole } = renderCard();

		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});

		expect(container.querySelector('#reasoning-panel')).toHaveClass('hidden');
	});

	test('panel becomes visible after toggle click', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				reasoning: makeReasoning()
			})
		);
		const { container, getByRole, getByText } = renderCard();

		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});

		await fireEvent.click(getByRole('button', { name: /show reasoning/i }));

		expect(container.querySelector('#reasoning-panel')).not.toHaveClass('hidden');
		expect(getByText('Glucose')).toBeTruthy();
	});

	test('aria-expanded reflects open state', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				reasoning: makeReasoning()
			})
		);
		const { getByRole } = renderCard();

		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});

		const toggle = getByRole('button', { name: /show reasoning/i });
		expect(toggle).toHaveAttribute('aria-expanded', 'false');

		await fireEvent.click(toggle);

		expect(getByRole('button', { name: /hide reasoning/i })).toHaveAttribute(
			'aria-expanded',
			'true'
		);
	});

	test('announces reasoning expansion via live region', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				reasoning: makeReasoning()
			})
		);
		const { container, getByRole } = renderCard();

		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});

		const announcement = container.querySelector('p.sr-only[aria-atomic="true"]');
		expect(announcement?.textContent).toBe('');

		await fireEvent.click(getByRole('button', { name: /show reasoning/i }));

		expect(announcement?.textContent).toBe('Reasoning details shown below.');
	});

	test('renders duplicate biomarker names without dropping rows', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				reasoning: makeReasoning({
					values_referenced: [
						{
							name: 'Glucose',
							value: 91,
							unit: 'mg/dL',
							ref_low: 70,
							ref_high: 99,
							status: 'normal'
						},
						{
							name: 'Glucose',
							value: 104,
							unit: 'mg/dL',
							ref_low: 70,
							ref_high: 99,
							status: 'high'
						}
					]
				})
			})
		);
		const { container, getAllByRole, getAllByText, getByRole } = renderCard();

		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});

		await fireEvent.click(getByRole('button', { name: /show reasoning/i }));

		expect(getAllByText('Glucose')).toHaveLength(2);
		expect(getAllByRole('row')).toHaveLength(3);
		expect(container.querySelectorAll('tbody tr')).toHaveLength(2);
	});

	test('renders duplicate uncertainty flags without dropping items', async () => {
		const flag = 'Insufficient data to interpret HbA1c confidently';
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				reasoning: makeReasoning({
					values_referenced: [],
					uncertainty_flags: [flag, flag]
				})
			})
		);
		const { getAllByText, getByRole } = renderCard();

		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});

		await fireEvent.click(getByRole('button', { name: /show reasoning/i }));

		expect(getAllByText(flag)).toHaveLength(2);
	});

	test('uncertainty flags render when present', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				reasoning: makeReasoning({
					values_referenced: [],
					uncertainty_flags: ['Insufficient data to interpret HbA1c confidently']
				})
			})
		);
		const { getByRole, getByText } = renderCard();

		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});

		await fireEvent.click(getByRole('button', { name: /show reasoning/i }));

		expect(getByText('Insufficient data to interpret HbA1c confidently')).toBeTruthy();
	});

	test('falls back to unknown label for unrecognized runtime statuses', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				reasoning: makeReasoning({
					values_referenced: [
						{
							name: 'Glucose',
							value: 91,
							unit: 'mg/dL',
							ref_low: 70,
							ref_high: 99,
							status: 'future-status'
						}
					]
				})
			})
		);
		const { getByRole, getByText } = renderCard();

		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});

		await fireEvent.click(getByRole('button', { name: /show reasoning/i }));

		expect(getByText('Unknown')).toBeTruthy();
	});

	test('resets showReasoning state when documentId prop changes', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({ reasoning: makeReasoning() })
		);
		const queryClient = makeQueryClient();
		const { getByRole, rerender } = render(AiInterpretationCardTestWrapper, {
			props: { queryClient, documentId: 'doc-1' }
		});

		// Open the reasoning panel
		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});
		await fireEvent.click(getByRole('button', { name: /show reasoning/i }));
		expect(getByRole('button', { name: /hide reasoning/i })).toHaveAttribute(
			'aria-expanded',
			'true'
		);

		// Navigate to a different document
		await rerender({ queryClient, documentId: 'doc-2' });

		// After new document's data loads the toggle must start collapsed
		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toHaveAttribute(
				'aria-expanded',
				'false'
			);
		});
	});

	test('SR announcer sits outside the outer atomic live region', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({ reasoning: makeReasoning() })
		);
		const { container } = renderCard();

		await waitFor(() => {
			expect(container.querySelector('section')).toBeTruthy();
		});

		const outerRegion = container.querySelector('div[aria-live="polite"][aria-atomic="true"]');
		const announcer = container.querySelector('p.sr-only[aria-live="polite"]');

		expect(outerRegion).toBeTruthy();
		expect(announcer).toBeTruthy();
		// Announcer must NOT be nested inside the atomic outer region to avoid re-reads
		expect(outerRegion?.contains(announcer)).toBe(false);
	});

	test('axe-core passes on expanded state', async () => {
		mockGetInterpretation.mockResolvedValue(
			makeInterpretationResponse({
				reasoning: makeReasoning({
					uncertainty_flags: ['Insufficient data to interpret HbA1c confidently']
				})
			})
		);
		const { container, getByRole } = renderCard();

		await waitFor(() => {
			expect(getByRole('button', { name: /show reasoning/i })).toBeTruthy();
		});

		await fireEvent.click(getByRole('button', { name: /show reasoning/i }));

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
