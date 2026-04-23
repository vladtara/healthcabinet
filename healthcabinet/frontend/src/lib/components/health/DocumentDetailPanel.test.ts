import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/query-core';
import axe from 'axe-core';

// Mock the apiFetch function used by all API helpers
vi.mock('$lib/api/client.svelte', () => ({
	apiFetch: vi.fn(),
	tokenState: { accessToken: 'mock-token' },
	API_BASE: 'http://localhost:8000'
}));

import { apiFetch } from '$lib/api/client.svelte';
import type { DocumentDetail, HealthValueItem } from '$lib/types/api';
import DocumentDetailPanelTestWrapper from './DocumentDetailPanelTestWrapper.svelte';

const mockApiFetch = vi.mocked(apiFetch);

function makeHealthValue(overrides: Partial<HealthValueItem> = {}): HealthValueItem {
	return {
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
		flagged_at: null,
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
		health_values: [makeHealthValue()],
		...overrides
	};
}

function makeQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: {
				retry: false,
				staleTime: Infinity
			}
		}
	});
}

interface RenderOpts {
	queryClient?: QueryClient;
	documentId?: string;
	detail?: DocumentDetail;
	onClose?: () => void;
	onDelete?: (docId: string) => void;
	onKeepPartial?: (docId: string) => void;
	onReupload?: (docId: string) => void;
	isKeepingPartial?: boolean;
	isDeleting?: boolean;
}

function renderPanel(opts: RenderOpts = {}) {
	const documentId = opts.documentId ?? 'doc-1';
	const detail = opts.detail ?? makeDetail({ id: documentId });
	const queryClient = opts.queryClient ?? makeQueryClient();
	queryClient.setQueryData(['documents', documentId], detail);
	mockApiFetch.mockResolvedValue(detail);

	const onClose = opts.onClose ?? vi.fn();
	const onDelete = opts.onDelete ?? vi.fn();
	const onKeepPartial = opts.onKeepPartial ?? vi.fn();
	const onReupload = opts.onReupload ?? vi.fn();

	render(DocumentDetailPanelTestWrapper, {
		props: {
			queryClient,
			documentId,
			onClose,
			onDelete,
			onKeepPartial,
			onReupload,
			isKeepingPartial: opts.isKeepingPartial ?? false,
			isDeleting: opts.isDeleting ?? false
		}
	});

	return { queryClient, onClose, onDelete, onKeepPartial, onReupload };
}

describe('DocumentDetailPanel', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	// --- Metadata rendering (AC 1, 2, 3) ---

	test('renders document metadata — filename, date, file size', async () => {
		renderPanel();

		await waitFor(() => {
			expect(screen.getByText('blood_test.pdf')).toBeInTheDocument();
		});
		// Date and size are now in separate rows of the meta grid
		expect(screen.getByText(/Jun 15, 2024/)).toBeInTheDocument();
		expect(screen.getByText(/44\.0 KB/)).toBeInTheDocument();
	});

	test('renders file type icon for PDF', async () => {
		renderPanel();

		await waitFor(() => {
			expect(screen.getByText('📄')).toBeInTheDocument();
		});
	});

	test('renders file type icon for image', async () => {
		renderPanel({ detail: makeDetail({ file_type: 'image/jpeg' }) });

		await waitFor(() => {
			expect(screen.getByText('🖼️')).toBeInTheDocument();
		});
	});

	test('renders header with document filename', async () => {
		renderPanel();

		await waitFor(() => {
			expect(screen.getByText('blood_test.pdf')).toBeInTheDocument();
		});
	});

	// --- Status badge (AC 4) ---

	test.each([
		{ status: 'completed' as const, symbol: '●', text: 'Completed' },
		{ status: 'processing' as const, symbol: '◉', text: 'Processing' },
		{ status: 'partial' as const, symbol: '⚠', text: 'Partial' },
		{ status: 'failed' as const, symbol: '✕', text: 'Failed' },
		{ status: 'pending' as const, symbol: '○', text: 'Pending' }
	])('status badge displays $text for $status', async ({ status, text }) => {
		renderPanel({ detail: makeDetail({ status, health_values: [] }) });

		await waitFor(() => {
			expect(screen.getByText(new RegExp(text))).toBeInTheDocument();
		});
	});

	// --- Recovery card (AC 5) ---

	test('recovery card appears for partial document without keep_partial', async () => {
		renderPanel({
			detail: makeDetail({ status: 'partial', keep_partial: null, health_values: [] })
		});

		await waitFor(() => {
			expect(screen.getByText(/we couldn't read everything clearly/i)).toBeInTheDocument();
		});
		expect(screen.getByRole('button', { name: /re-upload document/i })).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /keep partial results/i })).toBeInTheDocument();
	});

	test('recovery card appears for failed document', async () => {
		renderPanel({
			detail: makeDetail({ status: 'failed', keep_partial: null, health_values: [] })
		});

		await waitFor(() => {
			expect(screen.getByText(/extraction failed/i)).toBeInTheDocument();
		});
		expect(screen.getByRole('button', { name: /re-upload document/i })).toBeInTheDocument();
		// No keep-partial for failed documents
		expect(screen.queryByRole('button', { name: /keep partial results/i })).not.toBeInTheDocument();
	});

	test('recovery card hidden for completed documents', async () => {
		renderPanel({ detail: makeDetail({ status: 'completed' }) });

		await waitFor(() => {
			expect(screen.getByText('blood_test.pdf')).toBeInTheDocument();
		});

		expect(screen.queryByText(/we couldn't read everything clearly/i)).not.toBeInTheDocument();
		expect(screen.queryByText(/extraction failed/i)).not.toBeInTheDocument();
	});

	test('recovery card hidden for processing documents', async () => {
		renderPanel({ detail: makeDetail({ status: 'processing', health_values: [] }) });

		await waitFor(() => {
			expect(screen.getByText('blood_test.pdf')).toBeInTheDocument();
		});

		expect(screen.queryByText(/we couldn't read everything clearly/i)).not.toBeInTheDocument();
	});

	test('recovery card hidden for pending documents', async () => {
		renderPanel({ detail: makeDetail({ status: 'pending', health_values: [] }) });

		await waitFor(() => {
			expect(screen.getByText('blood_test.pdf')).toBeInTheDocument();
		});

		expect(screen.queryByText(/we couldn't read everything clearly/i)).not.toBeInTheDocument();
	});

	test('recovery card hidden for partial+kept documents', async () => {
		renderPanel({
			detail: makeDetail({ status: 'partial', keep_partial: true, health_values: [] })
		});

		await waitFor(() => {
			expect(screen.getByText('blood_test.pdf')).toBeInTheDocument();
		});

		expect(screen.queryByText(/we couldn't read everything clearly/i)).not.toBeInTheDocument();
	});

	// --- Extracted values (AC 6) ---

	test('extracted values render with biomarker, value, unit, status', async () => {
		renderPanel();

		await waitFor(() => {
			expect(screen.getByText('Glucose')).toBeInTheDocument();
		});
		expect(screen.getByText('95')).toBeInTheDocument();
		expect(screen.getByText('mg/dL')).toBeInTheDocument();
		// Default makeHealthValue has value 95 within range 70-100 => Optimal
		expect(screen.getByText(/Optimal/)).toBeInTheDocument();
	});

	test('shows empty message when no health values', async () => {
		renderPanel({ detail: makeDetail({ health_values: [] }) });

		await waitFor(() => {
			expect(screen.getByText('No extracted health values.')).toBeInTheDocument();
		});
	});

	test('shows values count in header', async () => {
		renderPanel({
			detail: makeDetail({
				health_values: [
					makeHealthValue({ id: 'hv-1', biomarker_name: 'Glucose' }),
					makeHealthValue({ id: 'hv-2', biomarker_name: 'TSH' })
				]
			})
		});

		await waitFor(() => {
			expect(screen.getByText('Extracted Values')).toBeInTheDocument();
			// Values count shown in metadata
			expect(screen.getByText('2')).toBeInTheDocument();
		});
	});

	// --- Delete flow (AC 7) ---

	test('delete button opens confirmation dialog', async () => {
		renderPanel();

		await waitFor(() => {
			expect(screen.getByRole('button', { name: /delete document/i })).toBeInTheDocument();
		});

		await fireEvent.click(screen.getByRole('button', { name: /delete document/i }));

		expect(screen.getByRole('alertdialog')).toBeInTheDocument();
		expect(screen.getByText('Delete Document?')).toBeInTheDocument();
	});

	test('confirmation dialog shows filename in message', async () => {
		renderPanel();

		await waitFor(() => {
			expect(screen.getByRole('button', { name: /delete document/i })).toBeInTheDocument();
		});

		await fireEvent.click(screen.getByRole('button', { name: /delete document/i }));

		const dialog = screen.getByRole('alertdialog');
		expect(within(dialog).getByText(/blood_test\.pdf/)).toBeInTheDocument();
		expect(within(dialog).getByText(/permanently remove/)).toBeInTheDocument();
	});

	test('cancel in dialog dismisses without deleting', async () => {
		const { onDelete } = renderPanel();

		await waitFor(() => {
			expect(screen.getByRole('button', { name: /delete document/i })).toBeInTheDocument();
		});

		await fireEvent.click(screen.getByRole('button', { name: /delete document/i }));
		expect(screen.getByRole('alertdialog')).toBeInTheDocument();

		await fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

		expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
		expect(onDelete).not.toHaveBeenCalled();
	});

	test('confirm delete calls onDelete, onClose, and closes dialog', async () => {
		const { onDelete, onClose } = renderPanel();

		await waitFor(() => {
			expect(screen.getByRole('button', { name: /delete document/i })).toBeInTheDocument();
		});

		await fireEvent.click(screen.getByRole('button', { name: /delete document/i }));
		await fireEvent.click(screen.getByRole('button', { name: /^delete$/i }));

		expect(onDelete).toHaveBeenCalledWith('doc-1');
		expect(onClose).toHaveBeenCalled();
		expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
	});

	test('escape dismisses dialog but not panel when dialog is open', async () => {
		const { onClose } = renderPanel();

		await waitFor(() => {
			expect(screen.getByRole('button', { name: /delete document/i })).toBeInTheDocument();
		});

		// Open confirm dialog
		await fireEvent.click(screen.getByRole('button', { name: /delete document/i }));
		expect(screen.getByRole('alertdialog')).toBeInTheDocument();

		// Escape should dismiss dialog, not panel
		await fireEvent.keyDown(window, { key: 'Escape' });

		expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
		// Panel should still be open (onClose not called)
		expect(onClose).not.toHaveBeenCalled();
		expect(screen.getByLabelText('Document details')).toBeInTheDocument();
	});

	test('escape closes panel when dialog is not open', async () => {
		const { onClose } = renderPanel();

		await waitFor(() => {
			expect(screen.getByLabelText('Document details')).toBeInTheDocument();
		});

		await fireEvent.keyDown(window, { key: 'Escape' });
		expect(onClose).toHaveBeenCalled();
	});

	// --- WCAG (AC 11) ---

	test('panel has section role and aria-label', async () => {
		renderPanel();

		await waitFor(() => {
			const section = screen.getByLabelText('Document details');
			expect(section).toBeInTheDocument();
		});
	});

	test('confirmation dialog has alertdialog role', async () => {
		renderPanel();

		await waitFor(() => {
			expect(screen.getByRole('button', { name: /delete document/i })).toBeInTheDocument();
		});

		await fireEvent.click(screen.getByRole('button', { name: /delete document/i }));

		const alertDialog = screen.getByRole('alertdialog');
		expect(alertDialog).toHaveAttribute('aria-modal', 'true');
		expect(alertDialog).toHaveAttribute('aria-labelledby', 'delete-dialog-title');
	});

	// --- Loading and error states ---

	test('shows loading state while detail query is pending', async () => {
		const queryClient = makeQueryClient();
		// Don't pre-populate cache — let the query stay pending
		mockApiFetch.mockReturnValue(new Promise(() => {}));

		render(DocumentDetailPanelTestWrapper, {
			props: {
				queryClient,
				documentId: 'doc-loading',
				onClose: vi.fn(),
				onDelete: vi.fn(),
				onKeepPartial: vi.fn(),
				onReupload: vi.fn(),
				isKeepingPartial: false,
				isDeleting: false
			}
		});

		await waitFor(() => {
			expect(screen.getByText('Loading details…')).toBeInTheDocument();
		});
	});

	test('shows error state when detail query fails', async () => {
		const queryClient = makeQueryClient();
		mockApiFetch.mockRejectedValue(new Error('Not found'));

		render(DocumentDetailPanelTestWrapper, {
			props: {
				queryClient,
				documentId: 'doc-error',
				onClose: vi.fn(),
				onDelete: vi.fn(),
				onKeepPartial: vi.fn(),
				onReupload: vi.fn(),
				isKeepingPartial: false,
				isDeleting: false
			}
		});

		await waitFor(() => {
			expect(screen.getByText('Failed to load document details.')).toBeInTheDocument();
		});
	});

	// --- Health status column ---

	test('health status shows empty when reference range is missing', async () => {
		renderPanel({
			detail: makeDetail({
				health_values: [
					makeHealthValue({ id: 'hv-no-range', reference_range_low: null, reference_range_high: null })
				]
			})
		});

		await waitFor(() => {
			expect(screen.getByText('Glucose')).toBeInTheDocument();
		});
		// Should not show any status label
		expect(screen.queryByText(/Optimal|Borderline|Concerning|Action/)).not.toBeInTheDocument();
	});

	// --- Keep-partial callback (AC 10) ---

	test('keep partial button triggers onKeepPartial callback', async () => {
		const { onKeepPartial } = renderPanel({
			detail: makeDetail({ status: 'partial', keep_partial: null, health_values: [] })
		});

		await waitFor(() => {
			expect(screen.getByRole('button', { name: /keep partial results/i })).toBeInTheDocument();
		});

		await fireEvent.click(screen.getByRole('button', { name: /keep partial results/i }));
		expect(onKeepPartial).toHaveBeenCalledWith('doc-1');
	});

	// --- Values table structure (AC 6) ---

	test('extracted values render in a data table with proper columns', async () => {
		renderPanel();

		await waitFor(() => {
			expect(screen.getByText('Glucose')).toBeInTheDocument();
		});

		// Table headers present
		expect(screen.getByText('Biomarker')).toBeInTheDocument();
		expect(screen.getByText('Value')).toBeInTheDocument();
		expect(screen.getByText('Unit')).toBeInTheDocument();
		expect(screen.getByText('Status')).toBeInTheDocument();

		// Table uses .hc-data-table class
		const tables = document.querySelectorAll('.hc-data-table table');
		expect(tables.length).toBeGreaterThan(0);
	});

	// --- Metadata enhancements: Kind / Result date / Flagged / Needs review ---

	test('renders document kind label (analysis)', async () => {
		renderPanel({ detail: makeDetail({ document_kind: 'analysis' }) });
		await waitFor(() => expect(screen.getByText(/^Kind:/)).toBeInTheDocument());
		expect(screen.getByText('Analysis')).toBeInTheDocument();
	});

	test('renders document kind label (document)', async () => {
		renderPanel({ detail: makeDetail({ document_kind: 'document' }) });
		await waitFor(() => expect(screen.getByText(/^Kind:/)).toBeInTheDocument());
		expect(screen.getByText('Document')).toBeInTheDocument();
	});

	test('result date shows a single formatted date when all values share one day', async () => {
		renderPanel({
			detail: makeDetail({
				health_values: [
					makeHealthValue({ id: 'a', measured_at: '2024-03-15T09:00:00Z' }),
					makeHealthValue({ id: 'b', measured_at: '2024-03-15T11:00:00Z' })
				]
			})
		});
		await waitFor(() => expect(screen.getByText(/^Result date:/)).toBeInTheDocument());
		expect(screen.getByText('Mar 15, 2024')).toBeInTheDocument();
	});

	test('result date shows a range when values span multiple days', async () => {
		renderPanel({
			detail: makeDetail({
				health_values: [
					makeHealthValue({ id: 'a', measured_at: '2024-03-10T09:00:00Z' }),
					makeHealthValue({ id: 'b', measured_at: '2024-03-15T09:00:00Z' })
				]
			})
		});
		await waitFor(() => expect(screen.getByText(/^Result date:/)).toBeInTheDocument());
		expect(screen.getByText(/Mar 10, 2024 – Mar 15, 2024/)).toBeInTheDocument();
	});

	test('result date shows em dash when no values have measured_at', async () => {
		renderPanel({
			detail: makeDetail({
				health_values: [makeHealthValue({ measured_at: null })]
			})
		});
		await waitFor(() => expect(screen.getByText(/^Result date:/)).toBeInTheDocument());
		// '—' is the em-dash fallback shown in the result-date value cell
		const row = screen.getByText(/^Result date:/).parentElement!;
		expect(row.textContent).toContain('—');
	});

	test('result date shows needs-confirm warning and Confirm year button', async () => {
		renderPanel({
			detail: makeDetail({
				needs_date_confirmation: true,
				partial_measured_at_text: 'March 15',
				health_values: [makeHealthValue({ measured_at: null })]
			})
		});
		await waitFor(() => {
			expect(screen.getByText(/March 15, year\?/)).toBeInTheDocument();
		});
		expect(screen.getByRole('button', { name: /confirm year/i })).toBeInTheDocument();
	});

	test('Confirm year opens an inline picker with Save and Cancel', async () => {
		renderPanel({
			detail: makeDetail({
				needs_date_confirmation: true,
				partial_measured_at_text: 'March 15',
				health_values: [makeHealthValue({ measured_at: null })]
			})
		});
		await waitFor(() =>
			expect(screen.getByRole('button', { name: /confirm year/i })).toBeInTheDocument()
		);
		await fireEvent.click(screen.getByRole('button', { name: /confirm year/i }));
		expect(screen.getByRole('combobox', { name: /year/i })).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument();
	});

	test('Cancel reverts to the warning row without calling the API', async () => {
		renderPanel({
			detail: makeDetail({
				needs_date_confirmation: true,
				partial_measured_at_text: 'March 15',
				health_values: [makeHealthValue({ measured_at: null })]
			})
		});
		await waitFor(() =>
			expect(screen.getByRole('button', { name: /confirm year/i })).toBeInTheDocument()
		);
		await fireEvent.click(screen.getByRole('button', { name: /confirm year/i }));
		await fireEvent.click(screen.getByRole('button', { name: /^cancel$/i }));
		expect(screen.queryByRole('combobox', { name: /year/i })).not.toBeInTheDocument();
		expect(mockApiFetch).not.toHaveBeenCalled();
	});

	test('Save posts the selected year, closes the picker, and invalidates dashboard queries', async () => {
		const docId = 'doc-confirm';
		const selectedYear = new Date().getFullYear() - 1;
		const initial = makeDetail({
			id: docId,
			needs_date_confirmation: true,
			partial_measured_at_text: 'March 15',
			health_values: [makeHealthValue({ id: 'hv-pending', measured_at: null })]
		});
		const queryClient = makeQueryClient();
		const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries');
		queryClient.setQueryData(['documents', docId], initial);

		// The component's detail query reads from the cache; the API call path below
		// is only exercised by the confirmDateYear POST.
		const resolved = makeDetail({
			id: docId,
			needs_date_confirmation: false,
			partial_measured_at_text: null,
			health_values: [
				makeHealthValue({
					id: 'hv-pending',
					measured_at: `${selectedYear}-03-15T00:00:00Z`
				})
			]
		});
		mockApiFetch.mockResolvedValue(resolved);

		renderPanel({ queryClient, documentId: docId, detail: initial });

		await waitFor(() =>
			expect(screen.getByRole('button', { name: /confirm year/i })).toBeInTheDocument()
		);
		await fireEvent.click(screen.getByRole('button', { name: /confirm year/i }));
		await fireEvent.change(screen.getByRole('combobox', { name: /year/i }), {
			target: { value: String(selectedYear) }
		});
		await fireEvent.click(screen.getByRole('button', { name: /^save$/i }));

		await waitFor(() => {
			expect(mockApiFetch).toHaveBeenCalledWith(
				`/api/v1/documents/${docId}/confirm-date-year`,
				expect.objectContaining({
					method: 'POST',
					body: JSON.stringify({ year: selectedYear })
				})
			);
		});
		await waitFor(() => {
			expect(screen.queryByRole('combobox', { name: /year/i })).not.toBeInTheDocument();
		});
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['documents'] });
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['health_values'] });
		expect(invalidateQueries).toHaveBeenCalledWith({
			queryKey: ['ai_dashboard_interpretation']
		});
	});

	test('Flagged count reflects is_flagged values', async () => {
		renderPanel({
			detail: makeDetail({
				health_values: [
					makeHealthValue({ id: 'a', is_flagged: true }),
					makeHealthValue({ id: 'b', is_flagged: true }),
					makeHealthValue({ id: 'c', is_flagged: false })
				]
			})
		});
		await waitFor(() => expect(screen.getByText(/^Flagged:/)).toBeInTheDocument());
		const row = screen.getByText(/^Flagged:/).parentElement!;
		expect(row.textContent).toContain('2');
	});

	test('Needs review count reflects needs_review values', async () => {
		renderPanel({
			detail: makeDetail({
				health_values: [
					makeHealthValue({ id: 'a', needs_review: true }),
					makeHealthValue({ id: 'b', needs_review: false })
				]
			})
		});
		await waitFor(() => expect(screen.getByText(/^Needs review:/)).toBeInTheDocument());
		const row = screen.getByText(/^Needs review:/).parentElement!;
		expect(row.textContent).toContain('1');
	});

	// --- Axe accessibility audit (AC 10, 11) ---

	test('axe accessibility audit passes', async () => {
		const documentId = 'doc-axe';
		const detail = makeDetail({ id: documentId });
		const queryClient = makeQueryClient();
		queryClient.setQueryData(['documents', documentId], detail);
		mockApiFetch.mockResolvedValue(detail);

		const { container } = render(DocumentDetailPanelTestWrapper, {
			props: {
				queryClient,
				documentId,
				onClose: vi.fn(),
				onDelete: vi.fn(),
				onKeepPartial: vi.fn(),
				onReupload: vi.fn(),
				isKeepingPartial: false,
				isDeleting: false
			}
		});

		await waitFor(() => {
			expect(screen.getByText('blood_test.pdf')).toBeInTheDocument();
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});
