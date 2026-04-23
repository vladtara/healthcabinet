import { waitFor } from '@testing-library/svelte';
import axe from 'axe-core';
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/query-core';
import AIClinicalNoteTestWrapper from './AIClinicalNoteTestWrapper.svelte';
import { tick } from 'svelte';

vi.mock('$lib/api/ai', () => ({
	getDocumentInterpretation: vi.fn(),
	getDashboardInterpretation: vi.fn(),
	streamAiChat: vi.fn(),
	streamDashboardChat: vi.fn(),
	getAiPatterns: vi.fn()
}));

vi.mock('$lib/api/client.svelte', () => ({
	tokenState: { accessToken: 'mock-token', setToken: vi.fn(), clear: vi.fn() },
	apiFetch: vi.fn(),
	apiStream: vi.fn()
}));

import { getDashboardInterpretation, getDocumentInterpretation } from '$lib/api/ai';
const mockGetInterpretation = vi.mocked(getDocumentInterpretation);
const mockGetDashboardInterpretation = vi.mocked(getDashboardInterpretation);

const mockInterpretation = {
	document_id: 'doc-1',
	interpretation: 'Your TSH is elevated at 5.8 mIU/L, above the reference range of 0.4-4.0.',
	model_version: 'claude-4',
	generated_at: '2026-04-04T12:00:00Z',
	reasoning: {
		values_referenced: [
			{ name: 'TSH', value: 5.8, unit: 'mIU/L', ref_low: 0.4, ref_high: 4.0, status: 'high' as const }
		],
		uncertainty_flags: ['Limited historical data'],
		prior_documents_referenced: []
	}
};

function renderNote(documentId: string | null = 'doc-1') {
	const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
	return render(AIClinicalNoteTestWrapper, { props: { queryClient, documentId } });
}

describe('AIClinicalNote', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('renders interpretation text when loaded', async () => {
		mockGetInterpretation.mockResolvedValue(mockInterpretation);
		const { getByText } = renderNote();

		await waitFor(() => {
			expect(getByText(/TSH is elevated/)).toBeInTheDocument();
		});
	});

	test('renders loading skeleton', () => {
		mockGetInterpretation.mockReturnValue(new Promise(() => {}));
		const { container } = renderNote();
		expect(container.querySelector('[aria-busy="true"]')).toBeInTheDocument();
	});

	test('renders error message on fetch failure', async () => {
		mockGetInterpretation.mockRejectedValue(new Error('Network error'));
		const { getByText } = renderNote();

		await waitFor(() => {
			expect(getByText(/unable to load/i)).toBeInTheDocument();
		});
	});

	test('renders empty state when documentId is null', () => {
		const { getByText } = renderNote(null);
		expect(getByText(/upload a document/i)).toBeInTheDocument();
	});

	test('disclaimer always present when interpretation loaded', async () => {
		mockGetInterpretation.mockResolvedValue(mockInterpretation);
		const { getByText } = renderNote();

		await waitFor(() => {
			expect(getByText(/not a medical diagnosis/i)).toBeInTheDocument();
		});
	});

	test('reasoning toggle expands and collapses', async () => {
		mockGetInterpretation.mockResolvedValue(mockInterpretation);
		const { getByText, container } = renderNote();

		await waitFor(() => {
			expect(getByText('Show reasoning')).toBeInTheDocument();
		});

		getByText('Show reasoning').click();
		await tick();

		expect(getByText('TSH')).toBeInTheDocument();
		expect(getByText('High')).toBeInTheDocument();
		expect(getByText('Hide reasoning')).toBeInTheDocument();
	});

	test('axe accessibility audit passes', async () => {
		mockGetInterpretation.mockResolvedValue(mockInterpretation);
		const { container } = renderNote();

		await waitFor(() => {
			expect(container.querySelector('.hc-ai-note-body')).toBeInTheDocument();
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	// ── Story 15.3 — dashboard mode ────────────────────────────────────────

	function renderDashboardNote(documentKind: 'all' | 'analysis' | 'document' = 'analysis') {
		const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
		return render(AIClinicalNoteTestWrapper, { props: { queryClient, documentKind } });
	}

		test('dashboard mode renders aggregate interpretation text', async () => {
			mockGetDashboardInterpretation.mockResolvedValue({
				document_id: null,
				document_kind: 'analysis',
				source_document_ids: ['doc-1', 'doc-2'],
				interpretation: 'Across your lab results, values look stable.',
				model_version: 'claude-4',
				generated_at: '2026-04-20T00:00:00Z',
				reasoning: null
			});

		const { getByText } = renderDashboardNote('analysis');

		await waitFor(() => {
			expect(getByText(/values look stable/i)).toBeInTheDocument();
		});
	});

	test('dashboard mode shows filter-empty copy on 409, not the document-scoped loading text', async () => {
		class ApiError extends Error {
			status: number;
			constructor(status: number) {
				super('http');
				this.status = status;
			}
		}
		mockGetDashboardInterpretation.mockRejectedValue(new ApiError(409));

		const { getByText, queryByText } = renderDashboardNote('analysis');

		await waitFor(() => {
			expect(getByText(/no AI interpretation for this filter yet/i)).toBeInTheDocument();
		});
		expect(queryByText(/interpretation is being generated/i)).toBeNull();
	});

		test('dashboard mode calls getDashboardInterpretation, not getDocumentInterpretation', async () => {
			mockGetDashboardInterpretation.mockResolvedValue({
				document_id: null,
				document_kind: 'all',
				source_document_ids: ['doc-1'],
				interpretation: 'All docs summary.',
				model_version: null,
				generated_at: '2026-04-20T00:00:00Z',
				reasoning: null
			});

		renderDashboardNote('all');

		await waitFor(() => {
			expect(mockGetDashboardInterpretation).toHaveBeenCalledWith('all');
		});
		expect(mockGetInterpretation).not.toHaveBeenCalled();
	});
});
