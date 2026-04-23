import { apiFetch, apiStream } from '$lib/api/client.svelte';
import type {
	DeleteResponse,
	Document,
	DocumentDetail,
	KeepPartialResponse
} from '$lib/types/api';

export interface DocumentStatusEvent {
	event: string;
	document_id: string;
	progress: number;
	message: string;
}

const STREAM_RETRY_DELAY_MS = 1000;

function isAbortError(error: unknown): boolean {
	return (error as { name?: string })?.name === 'AbortError';
}

function isAuthError(error: unknown): boolean {
	return (error as { status?: number })?.status === 401;
}

function emitFrames(
	frames: string[],
	signal: AbortSignal,
	onEvent: (event: DocumentStatusEvent) => void
): boolean {
	for (const frame of frames) {
		if (signal.aborted) return true;
		const dataLine = frame.split('\n').find((line) => line.startsWith('data: '));
		if (!dataLine) continue;

		try {
			onEvent(JSON.parse(dataLine.slice(6)) as DocumentStatusEvent);
		} catch {
			/* malformed frame — skip */
		}

		if (signal.aborted) return true;
	}

	return false;
}

async function waitForRetry(signal: AbortSignal): Promise<void> {
	if (signal.aborted) return;

	await new Promise<void>((resolve) => {
		let settled = false;

		function finish(): void {
			if (settled) return;
			settled = true;
			signal.removeEventListener('abort', onAbort);
			resolve();
		}

		function onAbort(): void {
			clearTimeout(timer);
			finish();
		}

		const timer = setTimeout(finish, STREAM_RETRY_DELAY_MS);
		signal.addEventListener('abort', onAbort, { once: true });
	});
}

/**
 * Fetch all documents for the authenticated user, sorted newest first.
 */
export async function listDocuments(): Promise<Document[]> {
	return apiFetch<Document[]>('/api/v1/documents');
}

/**
 * Fetch a single document with its extracted health values.
 */
export async function getDocumentDetail(documentId: string): Promise<DocumentDetail> {
	return apiFetch<DocumentDetail>(`/api/v1/documents/${documentId}`);
}

/**
 * Delete a document, its health values, and storage object.
 */
export async function deleteDocument(documentId: string): Promise<DeleteResponse> {
	return apiFetch<DeleteResponse>(`/api/v1/documents/${documentId}`, {
		method: 'DELETE'
	});
}

/**
 * Upload a file to the backend, which proxies it to MinIO.
 * The browser never contacts MinIO directly.
 */
export async function uploadDocument(file: File): Promise<Document> {
	const formData = new FormData();
	formData.append('file', file);
	return apiFetch<Document>('/api/v1/documents/upload', {
		method: 'POST',
		body: formData,
	});
}

/**
 * Upload a replacement file for an existing document slot via the backend proxy.
 * Only valid for documents in partial or failed status.
 * The same document_id is reused — no duplicate document row is created.
 * Rate limited: consumes the same quota as a fresh upload.
 */
export async function reuploadDocument(documentId: string, file: File): Promise<Document> {
	const formData = new FormData();
	formData.append('file', file);
	return apiFetch<Document>(`/api/v1/documents/${documentId}/reupload`, {
		method: 'POST',
		body: formData,
	});
}

/**
 * Persist the user's decision to keep partial extraction results.
 * Dismisses the recovery prompt without deleting or mutating extracted values.
 */
export async function keepPartialResults(documentId: string): Promise<KeepPartialResponse> {
	return apiFetch<KeepPartialResponse>(`/api/v1/documents/${documentId}/keep-partial`, {
		method: 'POST'
	});
}

/**
 * Confirm the year for a document whose extractor produced a yearless result date.
 * Story 15.2 — contract-only helper; UI consumption lands in Story 15.3.
 *
 * Returns the updated document detail, including:
 *  - `needs_date_confirmation` cleared to false
 *  - `partial_measured_at_text` cleared to null
 *  - every health value's `measured_at` populated with the resolved timestamp
 *  - recomputed terminal status (completed unless low-confidence values remain)
 */
export async function confirmDateYear(
	documentId: string,
	year: number
): Promise<DocumentDetail> {
	return apiFetch<DocumentDetail>(`/api/v1/documents/${documentId}/confirm-date-year`, {
		method: 'POST',
		body: JSON.stringify({ year })
	});
}

/**
 * Stream real-time document processing status via fetch-based SSE.
 * Uses Authorization header (not query-param) for token security.
 * Automatic 401 refresh is handled by apiStream().
 */
export async function streamDocumentStatus(
	documentId: string,
	signal: AbortSignal,
	onEvent: (event: DocumentStatusEvent) => void,
	onError: (error: 'stream-error' | 'auth-error') => void
): Promise<void> {
	while (!signal.aborted) {
		let response: Response;
		try {
			response = await apiStream(`/api/v1/documents/${documentId}/status`, { signal });
		} catch (error) {
			if (isAbortError(error)) return;

			const errorType = isAuthError(error) ? 'auth-error' : 'stream-error';
			onError(errorType);
			if (errorType === 'auth-error') return;

			await waitForRetry(signal);
			continue;
		}

		if (!response.ok) {
			const errorType = response.status === 401 ? 'auth-error' : 'stream-error';
			onError(errorType);
			if (errorType === 'auth-error') return;

			await waitForRetry(signal);
			continue;
		}

		const reader = response.body?.getReader();
		if (!reader) {
			onError('stream-error');
			await waitForRetry(signal);
			continue;
		}

		const decoder = new TextDecoder();
		let buffer = '';

		try {
			while (!signal.aborted) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const frames = buffer.split('\n\n');
				buffer = frames.pop() ?? '';

				if (emitFrames(frames, signal, onEvent)) return;
			}

			if (signal.aborted) return;

			buffer += decoder.decode();
			const trailingFrames = buffer.split('\n\n');
			buffer = trailingFrames.pop() ?? '';

			if (emitFrames(trailingFrames, signal, onEvent)) return;
			if (signal.aborted) return;
		} catch (error) {
			if (isAbortError(error)) return;
		} finally {
			reader.cancel().catch(() => {});
		}

		if (signal.aborted) return;

		onError('stream-error');
		await waitForRetry(signal);
	}
}
