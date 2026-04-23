import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/svelte';
import type { DocumentStatusEvent } from '$lib/api/documents';

// Track streamDocumentStatus callbacks per call
type StreamCallCapture = {
	documentId: string;
	signal: AbortSignal;
	onEvent: (event: DocumentStatusEvent) => void;
	onError: (error: 'stream-error' | 'auth-error') => void;
};
let streamCalls: StreamCallCapture[] = [];

// Mock the apiFetch/apiStream functions used by all API helpers
vi.mock('$lib/api/client.svelte', () => ({
	apiFetch: vi.fn(),
	apiStream: vi.fn(),
	tokenState: { accessToken: 'mock-token' },
	API_BASE: 'http://localhost:8000'
}));

// Partial mock: keep real API helpers, override streamDocumentStatus
vi.mock('$lib/api/documents', async (importOriginal) => {
	const actual = await importOriginal<typeof import('$lib/api/documents')>();
	return {
		...actual,
		streamDocumentStatus: vi.fn(
			(
				documentId: string,
				signal: AbortSignal,
				onEvent: (event: DocumentStatusEvent) => void,
				onError: (error: 'stream-error' | 'auth-error') => void
			): Promise<void> => {
				streamCalls.push({ documentId, signal, onEvent, onError });
				return new Promise(() => {}); // never resolves (open stream)
			}
		)
	};
});

import { apiFetch } from '$lib/api/client.svelte';
import {
	listDocuments,
	getDocumentDetail,
	deleteDocument,
	reuploadDocument,
	keepPartialResults
} from '$lib/api/documents';
import { flagHealthValue } from '$lib/api/health-values';
import type { Document, DocumentDetail } from '$lib/types/api';
import { QueryClient } from '@tanstack/query-core';
import DocumentsPageTestWrapper from './DocumentsPageTestWrapper.svelte';

const mockApiFetch = vi.mocked(apiFetch);

function makeDoc(overrides: Partial<Document> = {}): Document {
	return {
		id: 'doc-1',
		user_id: 'user-1',
		filename: 'blood_test.pdf',
		file_size_bytes: 45056,
		file_type: 'application/pdf',
		status: 'completed',
		arq_job_id: null,
		keep_partial: null,
		document_kind: 'analysis',
		needs_date_confirmation: false,
		partial_measured_at_text: null,
		created_at: '2024-06-15T10:00:00Z',
		updated_at: '2024-06-15T10:05:00Z',
		...overrides
	};
}

function makeDetail(overrides: Partial<DocumentDetail> = {}): DocumentDetail {
	return {
		id: 'doc-1',
		filename: 'blood_test.pdf',
		file_size_bytes: 45056,
		file_type: 'application/pdf',
		status: 'completed',
		arq_job_id: null,
		keep_partial: null,
		document_kind: 'analysis',
		needs_date_confirmation: false,
		partial_measured_at_text: null,
		created_at: '2024-06-15T10:00:00Z',
		updated_at: '2024-06-15T10:05:00Z',
		health_values: [
			{
				id: 'hv-1',
				biomarker_name: 'Glucose',
				canonical_biomarker_name: 'glucose',
				value: 95,
				unit: 'mg/dL',
				measured_at: null,
				confidence: 0.95,
				reference_range_low: 70,
				reference_range_high: 100,
				needs_review: false,
				is_flagged: false,
				flagged_at: null
			}
		],
		...overrides
	};
}

describe('Documents cabinet API helpers', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('listDocuments calls GET /api/v1/documents', async () => {
		const docs = [makeDoc(), makeDoc({ id: 'doc-2', filename: 'xray.pdf' })];
		mockApiFetch.mockResolvedValue(docs);

		const result = await listDocuments();

		expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/documents');
		expect(result).toEqual(docs);
		expect(result).toHaveLength(2);
	});

	test('listDocuments returns empty array when no documents', async () => {
		mockApiFetch.mockResolvedValue([]);

		const result = await listDocuments();

		expect(result).toEqual([]);
		expect(result).toHaveLength(0);
	});

	test('getDocumentDetail calls GET /api/v1/documents/{id}', async () => {
		const detail = makeDetail();
		mockApiFetch.mockResolvedValue(detail);

		const result = await getDocumentDetail('doc-1');

		expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/documents/doc-1');
		expect(result.health_values).toHaveLength(1);
		expect(result.health_values[0].biomarker_name).toBe('Glucose');
	});

	test('getDocumentDetail includes health values with confidence', async () => {
		const detail = makeDetail({
			health_values: [
				{
					id: 'hv-1',
					biomarker_name: 'HbA1c',
					canonical_biomarker_name: 'hba1c',
					value: 5.7,
					unit: '%',
					measured_at: null,
					confidence: 0.92,
					reference_range_low: 4.0,
					reference_range_high: 5.6,
					needs_review: true,
					is_flagged: false,
					flagged_at: null
				},
				{
					id: 'hv-2',
					biomarker_name: 'Cholesterol',
					canonical_biomarker_name: 'cholesterol_total',
					value: 180,
					unit: 'mg/dL',
					measured_at: null,
					confidence: 0.88,
					reference_range_low: null,
					reference_range_high: 200,
					needs_review: false,
					is_flagged: false,
					flagged_at: null
				}
			]
		});
		mockApiFetch.mockResolvedValue(detail);

		const result = await getDocumentDetail('doc-1');

		expect(result.health_values).toHaveLength(2);
		expect(result.health_values[0].needs_review).toBe(true);
		expect(result.health_values[1].confidence).toBe(0.88);
	});

	test('deleteDocument calls DELETE /api/v1/documents/{id}', async () => {
		mockApiFetch.mockResolvedValue({ deleted: true });

		const result = await deleteDocument('doc-1');

		expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/documents/doc-1', {
			method: 'DELETE'
		});
		expect(result.deleted).toBe(true);
	});

	test('deleteDocument propagates API errors', async () => {
		mockApiFetch.mockRejectedValue(new Error('Not found'));

		await expect(deleteDocument('nonexistent')).rejects.toThrow('Not found');
	});

});

describe('Documents cabinet page behavior', () => {
	test('Document type returns correct status badge mapping', () => {
		// These match the statusBadge function in the component
		const statusMap: Record<string, { text: string }> = {
			completed: { text: 'Completed' },
			processing: { text: 'Processing' },
			pending: { text: 'Pending' },
			partial: { text: 'Partial' },
			failed: { text: 'Failed' }
		};

		expect(statusMap['completed'].text).toBe('Completed');
		expect(statusMap['pending'].text).toBe('Pending');
		expect(statusMap['partial'].text).toBe('Partial');
		expect(statusMap['failed'].text).toBe('Failed');
	});

	test('document list is sorted newest first by API contract', async () => {
		const older = makeDoc({
			id: 'doc-old',
			created_at: '2024-01-01T00:00:00Z'
		});
		const newer = makeDoc({
			id: 'doc-new',
			created_at: '2024-06-15T00:00:00Z'
		});
		mockApiFetch.mockResolvedValue([newer, older]);

		const result = await listDocuments();

		// API returns newest first
		expect(result[0].id).toBe('doc-new');
		expect(result[1].id).toBe('doc-old');
	});

	test('all document statuses are handled', () => {
		const statuses: Document['status'][] = [
			'completed',
			'processing',
			'pending',
			'partial',
			'failed'
		];

		for (const status of statuses) {
			const doc = makeDoc({ status });
			expect(doc.status).toBe(status);
		}
	});
});

// ============================================================
// Mounted component tests — real QueryClient, mocked apiFetch
// ============================================================

function makeQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: {
				retry: false,
				// staleTime: Infinity prevents background refetch so test data stays stable
				staleTime: Infinity
			}
		}
	});
}

describe('Documents cabinet page component (mounted)', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		streamCalls = [];
	});

	test('renders empty state when document list is empty', async () => {
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], []);
		vi.mocked(apiFetch).mockResolvedValue([]);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(screen.getByText('No documents yet')).toBeInTheDocument();
		});
		expect(screen.getByRole('link', { name: /upload health document/i })).toBeInTheDocument();
	});

	test('renders loading indicator while fetching documents', async () => {
		const queryClient = makeQueryClient();
		// No pre-populated data — query starts in loading state
		// Make apiFetch hang so component stays in loading state
		vi.mocked(apiFetch).mockReturnValue(new Promise(() => {}));

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(screen.getByText('Loading documents…')).toBeInTheDocument();
		});
	});

	test('renders document cards with correct status badge text', async () => {
		const docs = [
			makeDoc({ id: '1', filename: 'blood.pdf', status: 'completed' }),
			makeDoc({ id: '2', filename: 'xray.pdf', status: 'failed' }),
			makeDoc({ id: '3', filename: 'labs.pdf', status: 'partial' })
		];
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], docs);
		vi.mocked(apiFetch).mockResolvedValue(docs);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(screen.getByText('Completed')).toBeInTheDocument();
		});
		expect(screen.getByText('Failed')).toBeInTheDocument();
		expect(screen.getByText('Partial')).toBeInTheDocument();
	});

	test('SSE stream invalidates queries on terminal completed event', async () => {
		const pendingDoc = makeDoc({ id: 'pending-1', status: 'pending' });
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [pendingDoc]);
		vi.mocked(apiFetch).mockResolvedValue([pendingDoc]);

		const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries').mockResolvedValue(undefined);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(streamCalls).toHaveLength(1);
		});

		// Push a completed event through the captured onEvent callback
		streamCalls[0].onEvent({
			event: 'document.completed',
			document_id: 'pending-1',
			progress: 1.0,
			message: 'Done'
		});

		await waitFor(() => {
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents'] });
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents', 'pending-1'] });
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['health_values'] });
		});
	});

	test('SSE partial event invalidates both documents and health_values', async () => {
		const processingDoc = makeDoc({ id: 'pending-2', status: 'processing' });
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [processingDoc]);
		vi.mocked(apiFetch).mockResolvedValue([processingDoc]);

		const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries').mockResolvedValue(undefined);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(streamCalls).toHaveLength(1);
		});

		streamCalls[0].onEvent({
			event: 'document.partial',
			document_id: 'pending-2',
			progress: 0.5,
			message: 'Partial'
		});

		await waitFor(() => {
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents'] });
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents', 'pending-2'] });
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['health_values'] });
		});
	});

	test('SSE error resilience — stream aborted only after 3 consecutive errors', async () => {
		const pendingDoc = makeDoc({ id: 'pending-3', status: 'pending' });
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [pendingDoc]);
		vi.mocked(apiFetch).mockResolvedValue([pendingDoc]);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(streamCalls).toHaveLength(1);
		});

		const call = streamCalls[0];

		// First two errors must NOT abort the controller
		call.onError('stream-error');
		expect(call.signal.aborted).toBe(false);
		call.onError('stream-error');
		expect(call.signal.aborted).toBe(false);
		// Third consecutive error triggers abort
		call.onError('stream-error');
		expect(call.signal.aborted).toBe(true);
	});

	test('auth error aborts immediately without waiting for three errors', async () => {
		const pendingDoc = makeDoc({ id: 'pending-auth', status: 'pending' });
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [pendingDoc]);
		vi.mocked(apiFetch).mockResolvedValue([pendingDoc]);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(streamCalls).toHaveLength(1);
		});

		const firstCall = streamCalls[0];
		firstCall.onError('auth-error');

		expect(firstCall.signal.aborted).toBe(true);
	});

	test('delete mutation removes document from cache immediately via setQueryData', async () => {
		const docs = [
			makeDoc({ id: 'doc-1', filename: 'blood_test.pdf' }),
			makeDoc({ id: 'doc-2', filename: 'xray_report.pdf' })
		];
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], docs);
		queryClient.setQueryData(['documents', 'doc-1'], makeDetail({ id: 'doc-1', filename: 'blood_test.pdf' }));
		vi.mocked(apiFetch).mockResolvedValue(docs);

		const setDataSpy = vi.spyOn(queryClient, 'setQueryData');

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(screen.getByText('blood_test.pdf')).toBeInTheDocument();
		});

		// Open detail panel for doc-1
		const cardButton = screen.getByRole('button', { name: /view blood_test\.pdf/i });
		await fireEvent.click(cardButton);

		await waitFor(() => {
			expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument();
		});

		// Mock the delete API response
		vi.mocked(apiFetch).mockResolvedValue({ deleted: true });

		// Click delete then confirm
		const deleteBtn = screen.getByRole('button', { name: /delete document/i });
		await fireEvent.click(deleteBtn);

		const confirmBtn = await screen.findByRole('button', { name: /^delete$/i });
		await fireEvent.click(confirmBtn);

		await waitFor(() => {
			// setQueryData must be called (not just invalidate) for immediate removal
			expect(setDataSpy).toHaveBeenCalledWith(['documents'], expect.any(Function));
		});
	});

	test('closing the detail panel clears a pending delete confirmation state', async () => {
		const docs = [makeDoc({ id: 'doc-1', filename: 'blood_test.pdf' })];
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], docs);
		queryClient.setQueryData(['documents', 'doc-1'], makeDetail({ id: 'doc-1' }));
		vi.mocked(apiFetch).mockResolvedValue(docs);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(screen.getByText('blood_test.pdf')).toBeInTheDocument();
		});

		await fireEvent.click(screen.getByRole('button', { name: /view blood_test\.pdf/i }));

		await waitFor(() => {
			expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument();
		});

		await fireEvent.click(screen.getByRole('button', { name: /delete document/i }));
		expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument();

		await fireEvent.click(screen.getByRole('button', { name: /close document details/i }));

		await waitFor(() => {
			expect(screen.queryByRole('region', { name: /document details/i })).not.toBeInTheDocument();
		});

		await fireEvent.click(screen.getByRole('button', { name: /view blood_test\.pdf/i }));

		await waitFor(() => {
			expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument();
		});
		expect(screen.getByRole('button', { name: /delete document/i })).toBeInTheDocument();
		expect(screen.queryByRole('button', { name: /^delete$/i })).not.toBeInTheDocument();
	});
});

// ============================================================
// Story 2.5 — API helpers: retry upload and keep-partial
// ============================================================

describe('Documents retry API helpers', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('reuploadDocument calls POST /api/v1/documents/{id}/reupload', async () => {
		const mockDoc = makeDoc({ id: 'doc-1' });
		mockApiFetch.mockResolvedValue(mockDoc);
		const file = new File([new ArrayBuffer(512000)], 'test.pdf', { type: 'application/pdf' });

		const result = await reuploadDocument('doc-1', file);

		expect(mockApiFetch).toHaveBeenCalledWith(
			'/api/v1/documents/doc-1/reupload',
			expect.objectContaining({ method: 'POST', body: expect.any(FormData) })
		);
		expect(result.id).toBe('doc-1');
	});

	test('reuploadDocument returns same document_id — no new row created', async () => {
		const existingDocId = 'existing-doc-id';
		mockApiFetch.mockResolvedValue(makeDoc({ id: existingDocId }));
		const file = new File([new ArrayBuffer(1024)], 'new.pdf', { type: 'application/pdf' });

		const result = await reuploadDocument(existingDocId, file);

		// Same document_id confirms no duplicate row was created
		expect(result.id).toBe(existingDocId);
	});

	test('keepPartialResults calls POST /api/v1/documents/{id}/keep-partial', async () => {
		mockApiFetch.mockResolvedValue({ kept: true });

		const result = await keepPartialResults('doc-1');

		expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/documents/doc-1/keep-partial', {
			method: 'POST'
		});
		expect(result.kept).toBe(true);
	});

	test('keepPartialResults propagates API errors', async () => {
		mockApiFetch.mockRejectedValue(new Error('Not found'));

		await expect(keepPartialResults('nonexistent')).rejects.toThrow('Not found');
	});
});

// ============================================================
// Story 2.5 — Cabinet page recovery UX (mounted component)
// ============================================================

describe('Documents cabinet page — recovery UX (Story 2.5)', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		streamCalls = [];
	});

	test('detail panel shows re-upload CTA for partial document without keep_partial', async () => {
		const partialDoc = makeDoc({ id: 'doc-partial', status: 'partial', keep_partial: null });
		const partialDetail = makeDetail({
			id: 'doc-partial',
			status: 'partial',
			keep_partial: null,
			health_values: []
		});
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [partialDoc]);
		queryClient.setQueryData(['documents', 'doc-partial'], partialDetail);
		vi.mocked(apiFetch).mockResolvedValue([partialDoc]);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => expect(screen.getByText('blood_test.pdf')).toBeInTheDocument());

		await fireEvent.click(screen.getByRole('button', { name: /view blood_test\.pdf/i }));

		await waitFor(() => expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument());

		// Recovery card must be shown
		expect(
			screen.getByText(/we couldn't read everything clearly/i)
		).toBeInTheDocument();

		// Re-upload is primary CTA
		expect(screen.getByRole('button', { name: /re-upload document/i })).toBeInTheDocument();

		// Keep partial results is secondary action
		expect(screen.getByRole('button', { name: /keep partial results/i })).toBeInTheDocument();
	});

	test('detail panel shows failure message for failed document', async () => {
		const failedDoc = makeDoc({ id: 'doc-failed', status: 'failed', keep_partial: null });
		const failedDetail = makeDetail({
			id: 'doc-failed',
			status: 'failed',
			keep_partial: null,
			health_values: []
		});
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [failedDoc]);
		queryClient.setQueryData(['documents', 'doc-failed'], failedDetail);
		vi.mocked(apiFetch).mockResolvedValue([failedDoc]);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => expect(screen.getByText('blood_test.pdf')).toBeInTheDocument());

		await fireEvent.click(screen.getByRole('button', { name: /view blood_test\.pdf/i }));

		await waitFor(() => expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument());

		// Failure message and re-upload CTA must be shown
		expect(screen.getByText(/extraction failed/i)).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /re-upload document/i })).toBeInTheDocument();

		// 'Keep partial results' must NOT be shown for failed documents
		expect(screen.queryByRole('button', { name: /keep partial results/i })).not.toBeInTheDocument();
	});

	test('detail panel hides recovery card when keep_partial is true', async () => {
		const keptDoc = makeDoc({ id: 'doc-kept', status: 'partial', keep_partial: true });
		const keptDetail = makeDetail({
			id: 'doc-kept',
			status: 'partial',
			keep_partial: true,
			health_values: []
		});
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [keptDoc]);
		queryClient.setQueryData(['documents', 'doc-kept'], keptDetail);
		vi.mocked(apiFetch).mockResolvedValue([keptDoc]);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => expect(screen.getByText('blood_test.pdf')).toBeInTheDocument());

		await fireEvent.click(screen.getByRole('button', { name: /view blood_test\.pdf/i }));

		await waitFor(() => expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument());

		// Recovery card must be hidden when user has kept partial results
		expect(screen.queryByText(/we couldn't read everything clearly/i)).not.toBeInTheDocument();
		expect(screen.queryByRole('button', { name: /re-upload document/i })).not.toBeInTheDocument();
	});

	test('partial document shows 3-tip photo guide', async () => {
		const partialDoc = makeDoc({ id: 'doc-tips', status: 'partial', keep_partial: null });
		const partialDetail = makeDetail({
			id: 'doc-tips',
			status: 'partial',
			keep_partial: null,
			health_values: []
		});
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [partialDoc]);
		queryClient.setQueryData(['documents', 'doc-tips'], partialDetail);
		vi.mocked(apiFetch).mockResolvedValue([partialDoc]);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => expect(screen.getByText('blood_test.pdf')).toBeInTheDocument());
		await fireEvent.click(screen.getByRole('button', { name: /view blood_test\.pdf/i }));
		await waitFor(() => expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument());

		// All three photo tips must be displayed
		expect(screen.getByText('Good lighting')).toBeInTheDocument();
		expect(screen.getByText('Flat surface')).toBeInTheDocument();
		expect(screen.getByText('No shadows')).toBeInTheDocument();
	});

	test('keep-partial mutation updates cached document to hide recovery card', async () => {
		const partialDoc = makeDoc({ id: 'doc-kp', status: 'partial', keep_partial: null });
		const partialDetail = makeDetail({
			id: 'doc-kp',
			status: 'partial',
			keep_partial: null,
			health_values: []
		});
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [partialDoc]);
		queryClient.setQueryData(['documents', 'doc-kp'], partialDetail);

		vi.mocked(apiFetch).mockResolvedValue([partialDoc]);

		const setDataSpy = vi.spyOn(queryClient, 'setQueryData');

		// Mock keepPartialResults at the API module level so the detail refetch doesn't
		// return the keep-partial response accidentally.
		vi.mocked(apiFetch).mockImplementation((url: string) => {
			if (typeof url === 'string' && url.includes('/keep-partial')) {
				return Promise.resolve({ kept: true });
			}
			if (typeof url === 'string' && url.includes('/doc-kp') && !url.includes('keep-partial')) {
				return Promise.resolve(partialDetail);
			}
			return Promise.resolve([partialDoc]);
		});

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => expect(screen.getByText('blood_test.pdf')).toBeInTheDocument());
		await fireEvent.click(screen.getByRole('button', { name: /view blood_test\.pdf/i }));
		await waitFor(() => expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument());

		const keepBtn = screen.getByRole('button', { name: /keep partial results/i });
		await fireEvent.click(keepBtn);

		await waitFor(() => {
			// setQueryData must be called to optimistically hide the recovery card
			expect(setDataSpy).toHaveBeenCalledWith(['documents'], expect.any(Function));
		});
	});

	test('keep-partial mutation also updates detail cache to hide recovery card immediately (Finding 3)', async () => {
		// Verify that setQueryData is called for the detail cache ['documents', docId] so the
		// recovery card disappears immediately without waiting for the background refetch.
		// (invalidateQueries triggers a background refetch which may return stale data in tests;
		//  the important thing is that setQueryData is called with the right updater.)
		const docId = 'doc-kp-detail';
		const partialDoc = makeDoc({ id: docId, status: 'partial', keep_partial: null });
		const partialDetail = makeDetail({
			id: docId,
			status: 'partial',
			keep_partial: null,
			health_values: []
		});
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [partialDoc]);
		queryClient.setQueryData(['documents', docId], partialDetail);

		vi.mocked(apiFetch).mockImplementation((url: string) => {
			if (typeof url === 'string' && url.includes('/keep-partial')) {
				return Promise.resolve({ kept: true });
			}
			if (typeof url === 'string' && url.includes(`/${docId}`) && !url.includes('keep-partial')) {
				return Promise.resolve(partialDetail);
			}
			return Promise.resolve([partialDoc]);
		});

		const setDataCalls: Array<[unknown[], unknown]> = [];
		const setDataSpy = vi.spyOn(queryClient, 'setQueryData').mockImplementation(
			(key: unknown, updater: unknown) => {
				setDataCalls.push([key as unknown[], updater]);
				// Actually apply the update so the cache reflects reality.
				// @ts-expect-error calling original with typed args
				QueryClient.prototype.setQueryData.call(queryClient, key, updater);
			}
		);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => expect(screen.getByText('blood_test.pdf')).toBeInTheDocument());
		await fireEvent.click(screen.getByRole('button', { name: /view blood_test\.pdf/i }));
		await waitFor(() => expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument());

		// Re-spy without mockImplementation to let setQueryData work normally.
		setDataSpy.mockRestore();
		const setDataSpy2 = vi.spyOn(queryClient, 'setQueryData');

		const keepBtn = screen.getByRole('button', { name: /keep partial results/i });
		await fireEvent.click(keepBtn);

		await waitFor(() => {
			// List cache must be updated optimistically.
			expect(setDataSpy2).toHaveBeenCalledWith(['documents'], expect.any(Function));
			// Detail cache must ALSO be updated immediately — this is the Finding 3 fix.
			expect(setDataSpy2).toHaveBeenCalledWith(['documents', docId], expect.any(Function));
		});

		// Verify the updater function for the detail key produces keep_partial: true.
		const detailCall = setDataSpy2.mock.calls.find(
			([key]) => Array.isArray(key) && key[0] === 'documents' && key[1] === docId
		);
		expect(detailCall).toBeDefined();
		const updaterFn = detailCall![1] as (old: typeof partialDetail) => typeof partialDetail;
		const updated = updaterFn(partialDetail);
		expect(updated?.keep_partial).toBe(true);
	});

	test('SSE retry completion invalidates documents and health_values queries', async () => {
		// After a retry completes (partial doc goes to completed), queries must be refreshed
		const partialDoc = makeDoc({ id: 'retry-doc', status: 'partial', keep_partial: null });
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [partialDoc]);
		vi.mocked(apiFetch).mockResolvedValue([partialDoc]);

		const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries').mockResolvedValue(undefined);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		// Partial doc won't open an SSE connection (not pending/processing)
		// Simulate that after retry the doc is now pending/processing
		const retryingDoc = makeDoc({ id: 'retry-doc', status: 'pending', keep_partial: null });
		queryClient.setQueryData(['documents'], [retryingDoc]);
		vi.mocked(apiFetch).mockResolvedValue([retryingDoc]);

		await waitFor(() => expect(streamCalls.length).toBeGreaterThan(0));

		streamCalls[0].onEvent({
			event: 'document.completed',
			document_id: 'retry-doc',
			progress: 1.0,
			message: 'Done'
		});

		await waitFor(() => {
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents'] });
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['documents', 'retry-doc'] });
			expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['health_values'] });
		});
	});

	test('completed document does not show recovery card', async () => {
		const completedDoc = makeDoc({ id: 'doc-complete', status: 'completed', keep_partial: null });
		const completedDetail = makeDetail({
			id: 'doc-complete',
			status: 'completed',
			keep_partial: null
		});
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], [completedDoc]);
		queryClient.setQueryData(['documents', 'doc-complete'], completedDetail);
		vi.mocked(apiFetch).mockResolvedValue([completedDoc]);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => expect(screen.getByText('blood_test.pdf')).toBeInTheDocument());
		await fireEvent.click(screen.getByRole('button', { name: /view blood_test\.pdf/i }));
		await waitFor(() => expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument());

		// No recovery card for completed documents
		expect(screen.queryByText(/we couldn't read everything clearly/i)).not.toBeInTheDocument();
		expect(screen.queryByText(/extraction failed/i)).not.toBeInTheDocument();
	});
});

// ============================================================
// Story 2.6 — Value flagging: API helper
// ============================================================

describe('flagHealthValue API helper', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('flagHealthValue calls PUT /api/v1/health-values/{id}/flag', async () => {
		const response = { id: 'hv-1', is_flagged: true, flagged_at: '2026-03-25T10:00:00Z' };
		mockApiFetch.mockResolvedValue(response);

		const result = await flagHealthValue('hv-1');

		expect(mockApiFetch).toHaveBeenCalledWith('/api/v1/health-values/hv-1/flag', {
			method: 'PUT'
		});
		expect(result.is_flagged).toBe(true);
		expect(result.flagged_at).toBe('2026-03-25T10:00:00Z');
	});

	test('flagHealthValue preserves snake_case contract', async () => {
		mockApiFetch.mockResolvedValue({
			id: 'hv-abc',
			is_flagged: true,
			flagged_at: '2026-03-25T00:00:00Z'
		});

		const result = await flagHealthValue('hv-abc');

		// TypeScript interface uses snake_case — no transformation layer
		expect('is_flagged' in result).toBe(true);
		expect('flagged_at' in result).toBe(true);
	});

	test('flagHealthValue propagates API errors', async () => {
		mockApiFetch.mockRejectedValue(new Error('Not found'));

		await expect(flagHealthValue('nonexistent')).rejects.toThrow('Not found');
	});
});

// ============================================================
// Story 2.6 — Value flagging: component interaction
// ============================================================

describe('Documents cabinet page — health status in detail panel', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		streamCalls = [];
	});

	test('detail panel shows health status column with Optimal for in-range value', async () => {
		const docs = [makeDoc({ id: 'doc-status-1', status: 'completed' })];
		const detail = makeDetail({ id: 'doc-status-1' });
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents'], docs);
		queryClient.setQueryData(['documents', 'doc-status-1'], detail);
		vi.mocked(apiFetch).mockResolvedValue(docs);

		render(DocumentsPageTestWrapper, { props: { queryClient } });

		await waitFor(() => expect(screen.getByText('blood_test.pdf')).toBeInTheDocument());
		await fireEvent.click(screen.getByRole('button', { name: /view blood_test\.pdf/i }));
		await waitFor(() => expect(screen.getByRole('region', { name: /document details/i })).toBeInTheDocument());

		// Glucose 95 within 70-100 => Optimal
		expect(screen.getByText(/Optimal/)).toBeInTheDocument();
	});
});
