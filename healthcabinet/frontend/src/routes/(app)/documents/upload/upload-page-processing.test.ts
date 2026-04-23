import { describe, expect, test, vi } from 'vitest';
import type { Document } from '$lib/types/api';
import {
	handleProcessingComplete,
	handleProcessingFailure,
	handleUploadSuccess
} from './page-state';

// Stub the documents module so its `$env/dynamic/public` transitive import
// does not load during unit tests — upload-queue re-exports these helpers.
vi.mock('$lib/api/documents', () => ({
	uploadDocument: vi.fn()
}));

import {
	applyTerminalStatus,
	createUploadQueue,
	type UploadQueueEntry
} from '$lib/upload-queue';

function makeDocument(id = 'mock-doc-id'): Document {
	return {
		id,
		user_id: 'user-1',
		filename: 'lab_results.pdf',
		file_size_bytes: 1024,
		file_type: 'application/pdf',
		status: 'pending',
		arq_job_id: 'job-123',
		keep_partial: null,
		document_kind: 'unknown',
		needs_date_confirmation: false,
		partial_measured_at_text: null,
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString()
	};
}

describe('upload page processing state helpers', () => {
	test('invalidates documents, health_values, and dashboard AI queries on successful processing', () => {
		const invalidateQueries = vi.fn();
		const next = handleProcessingComplete(
			{ invalidateQueries },
			{ uploadState: 'success', documentId: 'mock-doc-id' }
		);

		expect(next).toEqual({ uploadState: 'done', documentId: 'mock-doc-id' });
		expect(invalidateQueries).toHaveBeenCalledTimes(3);
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['documents'] });
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['health_values'] });
		// Story 15.3 — rebuild dashboard AI aggregate from the new persisted row.
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['ai_dashboard_interpretation'] });
	});

	test('partial processing invalidates documents, health_values, and dashboard AI', () => {
		const invalidateQueries = vi.fn();
		const next = handleProcessingFailure(
			{ invalidateQueries },
			{ uploadState: 'success', documentId: 'mock-doc-id' },
			'partial'
		);

		expect(next).toEqual({ uploadState: 'partial', documentId: 'mock-doc-id' });
		expect(invalidateQueries).toHaveBeenCalledTimes(3);
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['documents'] });
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['health_values'] });
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['ai_dashboard_interpretation'] });
	});

	test('failed processing transitions to failed state without cache invalidation', () => {
		const invalidateQueries = vi.fn();
		const next = handleProcessingFailure(
			{ invalidateQueries },
			{ uploadState: 'success', documentId: 'mock-doc-id' },
			'failed'
		);

		expect(next).toEqual({ uploadState: 'failed', documentId: 'mock-doc-id' });
		expect(invalidateQueries).not.toHaveBeenCalled();
	});

	test('upload success captures the document id used by ProcessingPipeline', () => {
		const next = handleUploadSuccess(makeDocument('doc-42'));

		expect(next).toEqual({ uploadState: 'success', documentId: 'doc-42' });
	});
});

describe('multi-file queue dashboard invalidation (Story 15.4)', () => {
	function makeFile(name: string): File {
		return new File(['x'], name, { type: 'application/pdf' });
	}

	function simulatePipelineTerminal(
		queue: UploadQueueEntry[],
		setQueue: (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => void,
		invalidateQueries: ReturnType<typeof vi.fn>,
		entryId: string,
		status: 'completed' | 'partial' | 'failed',
		error?: string
	): void {
		void queue;
		applyTerminalStatus({ invalidateQueries }, setQueue, entryId, status, error);
	}

	test('2 completed + 1 partial + 1 failed → dashboard key invalidated 3 times', () => {
		const files = [makeFile('a.pdf'), makeFile('b.pdf'), makeFile('c.pdf'), makeFile('d.pdf')];
		let queue: UploadQueueEntry[] = createUploadQueue(files).map((e) => ({
			...e,
			status: 'processing' as const,
			documentId: `doc-${e.file.name}`
		}));
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			queue = mut(queue);
		};

		simulatePipelineTerminal(queue, setQueue, invalidateQueries, queue[0].id, 'completed');
		simulatePipelineTerminal(queue, setQueue, invalidateQueries, queue[1].id, 'partial');
		simulatePipelineTerminal(queue, setQueue, invalidateQueries, queue[2].id, 'failed', 'bad');
		simulatePipelineTerminal(queue, setQueue, invalidateQueries, queue[3].id, 'completed');

		// 3 non-failed terminals × 3 keys each = 9 invalidations total.
		expect(invalidateQueries).toHaveBeenCalledTimes(9);

		// Dashboard AI key specifically invalidated exactly once per non-failed terminal.
		const dashboardCalls = invalidateQueries.mock.calls.filter(
			([arg]) => (arg as { queryKey: string[] }).queryKey[0] === 'ai_dashboard_interpretation'
		);
		expect(dashboardCalls).toHaveLength(3);

		// Failed entry: no invalidation fired for its id.
		expect(queue.find((e) => e.id === queue[2].id)?.status).toBe('failed');
	});

	test('all-failed batch → no dashboard invalidations', () => {
		const files = [makeFile('a.pdf'), makeFile('b.pdf')];
		let queue: UploadQueueEntry[] = createUploadQueue(files).map((e) => ({
			...e,
			status: 'processing' as const,
			documentId: `doc-${e.file.name}`
		}));
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			queue = mut(queue);
		};

		applyTerminalStatus({ invalidateQueries }, setQueue, queue[0].id, 'failed', 'x');
		applyTerminalStatus({ invalidateQueries }, setQueue, queue[1].id, 'failed', 'y');

		expect(invalidateQueries).not.toHaveBeenCalled();
		expect(queue.every((e) => e.status === 'failed')).toBe(true);
	});

	test('single-file queue of one → one full invalidation (matches pre-15.4 behavior)', () => {
		const queue0: UploadQueueEntry[] = [
			{
				id: 'e1',
				file: makeFile('single.pdf'),
				status: 'processing',
				documentId: 'doc-single'
			}
		];
		let queue = queue0;
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			queue = mut(queue);
		};

		applyTerminalStatus({ invalidateQueries }, setQueue, 'e1', 'completed');

		expect(invalidateQueries).toHaveBeenCalledTimes(3);
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['documents'] });
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['health_values'] });
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['ai_dashboard_interpretation'] });
	});
});
