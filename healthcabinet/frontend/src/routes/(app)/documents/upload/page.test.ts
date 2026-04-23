import { fireEvent, waitFor } from '@testing-library/svelte';
import axe from 'axe-core';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import DocumentUploadZone from '$lib/components/health/DocumentUploadZone.svelte';
import type { DocumentStatusEvent } from '$lib/api/documents';

vi.mock('$lib/api/documents', () => ({
	uploadDocument: vi.fn(),
	reuploadDocument: vi.fn(),
	streamDocumentStatus: vi.fn()
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

import { uploadDocument, reuploadDocument, streamDocumentStatus } from '$lib/api/documents';

const mockUploadDocument = vi.mocked(uploadDocument);
const mockReuploadDocument = vi.mocked(reuploadDocument);
const mockStreamDocumentStatus = vi.mocked(streamDocumentStatus);

type OnEvent = (event: DocumentStatusEvent) => void;
type OnError = (error: 'stream-error' | 'auth-error') => void;

const capturedStreams = new Map<
	string,
	{ onEvent: OnEvent; onError: OnError; signal: AbortSignal }
>();

function makePdfFile(sizeBytes = 1024): File {
	return new File([new ArrayBuffer(sizeBytes)], 'lab_results.pdf', {
		type: 'application/pdf'
	});
}

function makeLargeFile(): File {
	// 21MB — exceeds 20MB limit
	return new File([new ArrayBuffer(21 * 1024 * 1024)], 'huge.pdf', {
		type: 'application/pdf'
	});
}

function makeQueueDocument(id: string, filename: string) {
	return {
		id,
		user_id: 'user-1',
		filename,
		file_size_bytes: 1024,
		file_type: 'application/pdf',
		status: 'pending' as const,
		arq_job_id: 'job-123',
		keep_partial: null,
		document_kind: 'unknown' as const,
		needs_date_confirmation: false,
		partial_measured_at_text: null,
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString()
	};
}

function emitDocumentEvent(documentId: string, event: string, message = ''): void {
	capturedStreams.get(documentId)?.onEvent({
		event,
		document_id: documentId,
		progress: 0,
		message
	});
}

function emitStreamError(documentId: string, error: 'stream-error' | 'auth-error'): void {
	capturedStreams.get(documentId)?.onError(error);
}

beforeEach(() => {
	capturedStreams.clear();
	mockStreamDocumentStatus.mockImplementation(
		(
			documentId: string,
			signal: AbortSignal,
			onEvent: OnEvent,
			onError: OnError
		): Promise<void> => {
			capturedStreams.set(documentId, { onEvent, onError, signal });
			return new Promise(() => {});
		}
	);
});

describe('DocumentUploadZone', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		const mockDoc = {
			id: 'mock-doc-id',
			user_id: 'user-1',
			filename: 'lab_results.pdf',
			file_size_bytes: 1024,
			file_type: 'application/pdf',
			status: 'pending' as const,
			arq_job_id: 'job-123',
			keep_partial: null,
			document_kind: 'unknown' as const,
			needs_date_confirmation: false,
			partial_measured_at_text: null,
			created_at: new Date().toISOString(),
			updated_at: new Date().toISOString()
		};
		mockUploadDocument.mockResolvedValue(mockDoc);
		mockReuploadDocument.mockResolvedValue(mockDoc);
	});

	test('file picker accept attribute is image/*,application/pdf', () => {
		const { container } = renderComponent(DocumentUploadZone);
		const input = container.querySelector('#file-input') as HTMLInputElement;
		expect(input).toBeTruthy();
		expect(input.accept).toBe('image/*,application/pdf');
	});

	test('no mobile camera input exists (desktop-only MVP)', () => {
		const { container } = renderComponent(DocumentUploadZone);
		const cameraInput = container.querySelector('#camera-input');
		expect(cameraInput).toBeNull();
	});

	test('upload zone has role="button" and is keyboard activatable', () => {
		const { container } = renderComponent(DocumentUploadZone);
		const zone = container.querySelector('[role="button"]');
		expect(zone).toBeTruthy();
		expect(zone?.getAttribute('tabindex')).toBe('0');
	});

	test('Enter key triggers file input click', async () => {
		const { container } = renderComponent(DocumentUploadZone);
		const zone = container.querySelector('[role="button"]') as HTMLElement;
		const fileInput = container.querySelector('#file-input') as HTMLInputElement;

		const clickSpy = vi.spyOn(fileInput, 'click');
		await fireEvent.keyDown(zone, { key: 'Enter' });
		expect(clickSpy).toHaveBeenCalledOnce();
	});

	test('Space key triggers file input click', async () => {
		const { container } = renderComponent(DocumentUploadZone);
		const zone = container.querySelector('[role="button"]') as HTMLElement;
		const fileInput = container.querySelector('#file-input') as HTMLInputElement;

		const clickSpy = vi.spyOn(fileInput, 'click');
		await fireEvent.keyDown(zone, { key: ' ' });
		expect(clickSpy).toHaveBeenCalledOnce();
	});

	test('file >20MB shows error before upload — no API call made', async () => {
		const { container } = renderComponent(DocumentUploadZone);
		const fileInput = container.querySelector('#file-input') as HTMLInputElement;

		Object.defineProperty(fileInput, 'files', {
			value: [makeLargeFile()],
			configurable: true
		});
		await fireEvent.change(fileInput);

		await waitFor(() => {
			// Check the visual alert element (not the aria-live sr-only region)
			const alert = container.querySelector('[role="alert"]');
			expect(alert?.textContent).toMatch(/maximum size is 20 ?MB/i);
		});

		expect(mockUploadDocument).not.toHaveBeenCalled();
	});

	test('drag-over applies dragging class and announces to screen reader', async () => {
		const { container } = renderComponent(DocumentUploadZone);
		const zone = container.querySelector('[role="button"]') as HTMLElement;

		await fireEvent.dragOver(zone, { preventDefault: () => {} });

		await waitFor(() => {
			expect(zone.classList.contains('hc-upload-zone-dragging')).toBe(true);
		});

		const liveRegion = container.querySelector('[aria-live="polite"]');
		expect(liveRegion?.textContent).toContain('Drop file to upload');
	});

	test('drag-leave clears dragging state', async () => {
		const { container } = renderComponent(DocumentUploadZone);
		const zone = container.querySelector('[role="button"]') as HTMLElement;

		await fireEvent.dragOver(zone, { preventDefault: () => {} });
		await fireEvent.dragLeave(zone);

		await waitFor(() => {
			expect(zone.classList.contains('hc-upload-zone-dragging')).toBe(false);
		});
	});

	test('retry preserves file reference and calls uploadDocument again with same file', async () => {
		mockUploadDocument.mockRejectedValueOnce(new Error('network error'));

		const { container, getByRole } = renderComponent(DocumentUploadZone);
		const fileInput = container.querySelector('#file-input') as HTMLInputElement;
		const file = makePdfFile();

		Object.defineProperty(fileInput, 'files', { value: [file], configurable: true });
		await fireEvent.change(fileInput);

		await waitFor(() => {
			expect(getByRole('button', { name: /retry/i })).toBeTruthy();
		});

		mockUploadDocument.mockResolvedValueOnce({
			id: 'new-id',
			user_id: 'user-1',
			filename: 'lab_results.pdf',
			file_size_bytes: 1024,
			file_type: 'application/pdf',
			status: 'pending',
			arq_job_id: null,
			keep_partial: null,
			document_kind: 'unknown',
			needs_date_confirmation: false,
			partial_measured_at_text: null,
			created_at: new Date().toISOString(),
			updated_at: new Date().toISOString()
		});

		const retryBtn = getByRole('button', { name: /retry/i });
		await fireEvent.click(retryBtn);

		await waitFor(() => {
			expect(mockUploadDocument).toHaveBeenCalledTimes(2);
		});

		// Verify the same File object is passed on both calls (file reference preserved, AC #5).
		expect(mockUploadDocument.mock.calls[0]?.[0]).toBe(file);
		expect(mockUploadDocument.mock.calls[1]?.[0]).toBe(file);
	});

	test('successful upload shows completion message', async () => {
		const { container } = renderComponent(DocumentUploadZone);
		const fileInput = container.querySelector('#file-input') as HTMLInputElement;

		Object.defineProperty(fileInput, 'files', {
			value: [makePdfFile()],
			configurable: true
		});
		await fireEvent.change(fileInput);

		await waitFor(() => {
			// Check the aria-live region for the success announcement
			const liveRegion = container.querySelector('[aria-live="polite"]');
			expect(liveRegion?.textContent).toContain('Upload complete');
		});
	});

	test('axe accessibility audit passes on initial render', async () => {
		const { container } = renderComponent(DocumentUploadZone);
		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});

	test('axe accessibility audit passes on error state', async () => {
		const { container } = renderComponent(DocumentUploadZone);
		const fileInput = container.querySelector('#file-input') as HTMLInputElement;

		Object.defineProperty(fileInput, 'files', {
			value: [makeLargeFile()],
			configurable: true
		});
		await fireEvent.change(fileInput);

		await waitFor(() => {
			expect(container.querySelector('[role="alert"]')).toBeTruthy();
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});

// ============================================================
// Story 11-3: Window chrome wrapper tests (mounted page)
// ============================================================

import { render, screen } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/query-core';
import UploadPageTestWrapper from './UploadPageTestWrapper.svelte';

const { pageStoreHandle } = vi.hoisted(() => ({
	pageStoreHandle: { store: null as unknown as { set: (v: { url: URL }) => void } }
}));

vi.mock('$app/stores', async () => {
	const { writable } = await import('svelte/store');
	pageStoreHandle.store = writable({ url: new URL('http://localhost:3000/documents/upload') });
	return { page: pageStoreHandle.store };
});

function setPageUrl(url: string): void {
	pageStoreHandle.store.set({ url: new URL(url) });
}

function makeQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: { retry: false, staleTime: Infinity }
		}
	});
}

describe('Upload page section header (Story 11-3)', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	test('section header renders with Import Health Document title', async () => {
		const queryClient = makeQueryClient();
		render(UploadPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(screen.getByText(/Import Health Document/)).toBeTruthy();
		});
	});

	test('subtitle text is present', async () => {
		const queryClient = makeQueryClient();
		render(UploadPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(screen.getByText('Add a new lab result to your health record')).toBeTruthy();
		});
	});

	test('cancel button is present in idle state and navigates to /documents', async () => {
		const { goto: mockGoto } = await import('$app/navigation');
		const queryClient = makeQueryClient();
		render(UploadPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(screen.getByRole('button', { name: /cancel/i })).toBeTruthy();
		});

		await fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
		expect(mockGoto).toHaveBeenCalledWith('/documents');
	});

	test('region role and aria-label are present', async () => {
		const queryClient = makeQueryClient();
		render(UploadPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(screen.getByRole('region', { name: /import health document/i })).toBeTruthy();
		});
	});

	test('upload zone is rendered inside section', async () => {
		const queryClient = makeQueryClient();
		const { container } = render(UploadPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			const section = container.querySelector('.hc-import-dialog');
			expect(section).toBeTruthy();
			const zone = section?.querySelector('[role="button"]');
			expect(zone).toBeTruthy();
		});
	});

	test('dropzone wrapper has sunken panel styling', async () => {
		const queryClient = makeQueryClient();
		const { container } = render(UploadPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			const dropzone = container.querySelector('.hc-import-dropzone');
			expect(dropzone).toBeTruthy();
		});
	});

	test('axe accessibility audit passes on page', async () => {
		const queryClient = makeQueryClient();
		const { container } = render(UploadPageTestWrapper, { props: { queryClient } });

		await waitFor(() => {
			expect(screen.getByText(/Import Health Document/)).toBeTruthy();
		});

		const results = await axe.run(container);
		expect(results.violations).toHaveLength(0);
	});
});

describe('Upload page multi-file queue (Story 15.4)', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockUploadDocument.mockImplementation(async (file: File) => {
			const stem = file.name.replace(/\.[^.]+$/, '');
			return makeQueueDocument(`doc-${stem}`, file.name);
		});
	});

	test('multi-file queue processes sequentially, shows summary, and resets for another batch', async () => {
		const queryClient = makeQueryClient();
		const { container } = render(UploadPageTestWrapper, { props: { queryClient } });
		const fileInput = container.querySelector('#file-input') as HTMLInputElement;
		const alpha = new File(['a'], 'alpha.pdf', { type: 'application/pdf' });
		const beta = new File(['b'], 'beta.pdf', { type: 'application/pdf' });

		expect(fileInput.multiple).toBe(true);

		Object.defineProperty(fileInput, 'files', {
			value: [alpha, beta],
			configurable: true
		});
		await fireEvent.change(fileInput);

		await waitFor(() => {
			expect(screen.getByText('⏳ Processing Batch')).toBeTruthy();
			expect(screen.getByLabelText('Upload queue')).toBeTruthy();
			expect(mockUploadDocument).toHaveBeenCalledTimes(1);
			expect(mockUploadDocument.mock.calls[0]?.[0]).toBe(alpha);
		});

		await waitFor(() => {
			expect(capturedStreams.has('doc-alpha')).toBe(true);
		});
		emitDocumentEvent('doc-alpha', 'document.completed', 'Alpha complete');

		await waitFor(() => {
			expect(mockUploadDocument).toHaveBeenCalledTimes(2);
			expect(mockUploadDocument.mock.calls[1]?.[0]).toBe(beta);
			expect(capturedStreams.has('doc-beta')).toBe(true);
		});

		emitDocumentEvent('doc-beta', 'document.partial', 'Beta partial');

		await waitFor(() => {
			expect(screen.getByText('Batch complete')).toBeTruthy();
			expect(screen.getByText(/✓ 1 complete/)).toBeTruthy();
			expect(screen.getByText(/⚠ 1 partial/)).toBeTruthy();
		});

		const partialBadge = Array.from(container.querySelectorAll('.hc-badge-warning')).find((node) =>
			node.textContent?.includes('Partial')
		);
		expect(partialBadge).toBeTruthy();

		await fireEvent.click(screen.getByRole('button', { name: /upload another batch/i }));

		await waitFor(() => {
			expect(screen.getByText('Add a new lab result to your health record')).toBeTruthy();
			expect(screen.queryByText('Batch complete')).toBeNull();
		});
	});

	test('auth error aborts the batch and surfaces re-auth without advancing to the next file', async () => {
		const queryClient = makeQueryClient();
		const { container } = render(UploadPageTestWrapper, { props: { queryClient } });
		const fileInput = container.querySelector('#file-input') as HTMLInputElement;
		const alpha = new File(['a'], 'alpha.pdf', { type: 'application/pdf' });
		const beta = new File(['b'], 'beta.pdf', { type: 'application/pdf' });

		Object.defineProperty(fileInput, 'files', {
			value: [alpha, beta],
			configurable: true
		});
		await fireEvent.change(fileInput);

		await waitFor(() => {
			expect(mockUploadDocument).toHaveBeenCalledTimes(1);
			expect(capturedStreams.has('doc-alpha')).toBe(true);
		});

		emitStreamError('doc-alpha', 'auth-error');

		await waitFor(() => {
			expect(screen.getByRole('alert', { name: /authentication required/i })).toHaveTextContent(
				'Your session expired. Please sign in again to continue this batch.'
			);
		});

		expect(mockUploadDocument).toHaveBeenCalledTimes(1);
		expect(screen.queryByText('Batch complete')).toBeNull();
		expect(screen.getByText('Failed')).toBeTruthy();
		expect(screen.getByText('Queued')).toBeTruthy();
	});

	test('retry mode: file input multiple is false when retryDocumentId URL param is present', async () => {
		// Story 15.7 AC2 — retry flow must stay single-file regardless of the
		// multi-file queue code path. Verifies both the input attribute and that
		// the reupload API (not the upload API) is wired for the selected file.
		setPageUrl('http://localhost:3000/documents/upload?retryDocumentId=doc-retry-42');

		const retryDoc = makeQueueDocument('doc-retry-42', 'lab_results.pdf');
		mockReuploadDocument.mockResolvedValueOnce(retryDoc);

		const queryClient = makeQueryClient();
		const { container } = render(UploadPageTestWrapper, { props: { queryClient } });

		const fileInput = container.querySelector('#file-input') as HTMLInputElement;
		expect(fileInput).toBeTruthy();
		expect(fileInput.multiple).toBe(false);

		const file = makePdfFile();
		Object.defineProperty(fileInput, 'files', { value: [file], configurable: true });
		await fireEvent.change(fileInput);

		await waitFor(() => {
			expect(mockReuploadDocument).toHaveBeenCalledTimes(1);
			expect(mockReuploadDocument.mock.calls[0]?.[0]).toBe('doc-retry-42');
			expect(mockReuploadDocument.mock.calls[0]?.[1]).toBe(file);
		});
		expect(mockUploadDocument).not.toHaveBeenCalled();

		// Reset URL so subsequent tests see the default (idempotency across files).
		setPageUrl('http://localhost:3000/documents/upload');
	});

	test('single-file retry mode rejects multi-file drops before calling the upload APIs', async () => {
		const { container } = renderComponent(DocumentUploadZone, {
			props: { retryDocumentId: 'doc-retry-42' }
		});
		const zone = container.querySelector('[role="button"]') as HTMLElement;
		const alpha = new File(['a'], 'alpha.pdf', { type: 'application/pdf' });
		const beta = new File(['b'], 'beta.pdf', { type: 'application/pdf' });

		await fireEvent.drop(zone, {
			preventDefault: () => {},
			dataTransfer: { files: [alpha, beta] }
		});

		await waitFor(() => {
			expect(container.querySelector('[role="alert"]')?.textContent).toContain(
				'Single-file mode accepts only one file'
			);
		});
		expect(mockReuploadDocument).not.toHaveBeenCalled();
		expect(mockUploadDocument).not.toHaveBeenCalled();
		expect(screen.queryByRole('button', { name: /retry upload/i })).toBeNull();
	});
});
