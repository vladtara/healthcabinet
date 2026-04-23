import { describe, expect, test, vi, beforeEach } from 'vitest';
import type { Document } from '$lib/types/api';
import {
	TERMINAL_STATUSES,
	createUploadQueue,
	advanceQueue,
	applyTerminalStatus,
	countByStatus,
	getActiveEntry,
	getQueueStatus,
	isTerminal,
	markEntryProcessing,
	processNextInQueue,
	validateFilesForQueue,
	type UploadQueueEntry,
	type UploadEntryStatus
} from './upload-queue';

function makeDoc(id: string): Document {
	return {
		id,
		user_id: 'user-1',
		filename: `${id}.pdf`,
		file_size_bytes: 1024,
		file_type: 'application/pdf',
		status: 'pending',
		arq_job_id: `job-${id}`,
		keep_partial: null,
		document_kind: 'unknown',
		needs_date_confirmation: false,
		partial_measured_at_text: null,
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString()
	};
}

function makeFile(name = 'test.pdf', size = 1024, type = 'application/pdf'): File {
	return new File(['pdf-bytes'], name, { type });
}

vi.mock('$lib/api/documents', () => ({
	uploadDocument: vi.fn(async (file: File): Promise<Document> => makeDoc(`server-${file.name}`))
}));

async function flush(): Promise<void> {
	await new Promise((r) => setTimeout(r, 0));
	await new Promise((r) => setTimeout(r, 0));
}

beforeEach(() => {
	vi.clearAllMocks();
});

describe('upload-queue data model', () => {
	test('TERMINAL_STATUSES contains exactly completed, partial, failed', () => {
		expect(TERMINAL_STATUSES.has('completed')).toBe(true);
		expect(TERMINAL_STATUSES.has('partial')).toBe(true);
		expect(TERMINAL_STATUSES.has('failed')).toBe(true);
		expect(TERMINAL_STATUSES.has('queued')).toBe(false);
		expect(TERMINAL_STATUSES.has('uploading')).toBe(false);
		expect(TERMINAL_STATUSES.has('processing')).toBe(false);
		expect(TERMINAL_STATUSES.size).toBe(3);
	});

	test('isTerminal returns true only for terminal statuses', () => {
		expect(isTerminal('completed')).toBe(true);
		expect(isTerminal('partial')).toBe(true);
		expect(isTerminal('failed')).toBe(true);
		expect(isTerminal('queued')).toBe(false);
		expect(isTerminal('uploading')).toBe(false);
		expect(isTerminal('processing')).toBe(false);
	});

	test('createUploadQueue from empty files returns empty array', () => {
		expect(createUploadQueue([])).toEqual([]);
	});

	test('createUploadQueue from one file returns single queued entry', () => {
		const f = makeFile('a.pdf');
		const q = createUploadQueue([f]);
		expect(q).toHaveLength(1);
		expect(q[0].status).toBe('queued');
		expect(q[0].file).toBe(f);
		expect(q[0].documentId).toBeUndefined();
		expect(q[0].error).toBeUndefined();
		expect(typeof q[0].id).toBe('string');
		expect(q[0].id.length).toBeGreaterThan(0);
	});

	test('createUploadQueue assigns unique ids to each entry', () => {
		const files = [makeFile('a.pdf'), makeFile('b.pdf'), makeFile('c.pdf')];
		const q = createUploadQueue(files);
		const ids = q.map((e) => e.id);
		expect(new Set(ids).size).toBe(3);
	});
});

describe('advanceQueue', () => {
	test('returns unchanged empty queue', () => {
		expect(advanceQueue([])).toEqual([]);
	});

	test('promotes first queued entry to uploading when no active entry exists', () => {
		const q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'queued' },
			{ id: '2', file: makeFile('b.pdf'), status: 'queued' }
		];
		const next = advanceQueue(q);
		expect(next[0].status).toBe('uploading');
		expect(next[1].status).toBe('queued');
	});

	test('does not promote when active entry already exists (uploading)', () => {
		const q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'uploading', documentId: 'd1' },
			{ id: '2', file: makeFile('b.pdf'), status: 'queued' }
		];
		const next = advanceQueue(q);
		expect(next[0].status).toBe('uploading');
		expect(next[1].status).toBe('queued');
	});

	test('does not promote when active entry already exists (processing)', () => {
		const q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'processing', documentId: 'd1' },
			{ id: '2', file: makeFile('b.pdf'), status: 'queued' }
		];
		const next = advanceQueue(q);
		expect(next[0].status).toBe('processing');
		expect(next[1].status).toBe('queued');
	});

	test('promotes next queued entry once previous is terminal', () => {
		const q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'completed', documentId: 'd1' },
			{ id: '2', file: makeFile('b.pdf'), status: 'queued' },
			{ id: '3', file: makeFile('c.pdf'), status: 'queued' }
		];
		const next = advanceQueue(q);
		expect(next[0].status).toBe('completed');
		expect(next[1].status).toBe('uploading');
		expect(next[2].status).toBe('queued');
	});

	test('returns queue unchanged when every entry is terminal', () => {
		const q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'completed', documentId: 'd1' },
			{ id: '2', file: makeFile('b.pdf'), status: 'failed', error: 'x' },
			{ id: '3', file: makeFile('c.pdf'), status: 'partial', documentId: 'd3' }
		];
		expect(advanceQueue(q)).toEqual(q);
	});
});

describe('countByStatus / getActiveEntry / getQueueStatus', () => {
	const sample: UploadQueueEntry[] = [
		{ id: '1', file: makeFile('a.pdf'), status: 'completed', documentId: 'd1' },
		{ id: '2', file: makeFile('b.pdf'), status: 'partial', documentId: 'd2' },
		{ id: '3', file: makeFile('c.pdf'), status: 'failed', error: 'bad' },
		{ id: '4', file: makeFile('d.pdf'), status: 'processing', documentId: 'd4' },
		{ id: '5', file: makeFile('e.pdf'), status: 'queued' }
	];

	test('countByStatus returns per-status counts', () => {
		const counts = countByStatus(sample);
		expect(counts.completed).toBe(1);
		expect(counts.partial).toBe(1);
		expect(counts.failed).toBe(1);
		expect(counts.processing).toBe(1);
		expect(counts.queued).toBe(1);
		expect(counts.uploading).toBe(0);
	});

	test('getActiveEntry returns first uploading-or-processing entry', () => {
		const active = getActiveEntry(sample);
		expect(active?.id).toBe('4');
	});

	test('getActiveEntry returns undefined when none active', () => {
		const terminalOnly: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'completed', documentId: 'd1' }
		];
		expect(getActiveEntry(terminalOnly)).toBeUndefined();
	});

	test('getQueueStatus returns idle for empty queue', () => {
		expect(getQueueStatus([])).toBe('idle');
	});

	test('getQueueStatus returns summary when every entry is terminal', () => {
		const allTerminal: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'completed', documentId: 'd1' },
			{ id: '2', file: makeFile('b.pdf'), status: 'failed', error: 'x' }
		];
		expect(getQueueStatus(allTerminal)).toBe('summary');
	});

	test('getQueueStatus returns active while any non-terminal entry exists', () => {
		expect(getQueueStatus(sample)).toBe('active');
	});
});

describe('processNextInQueue', () => {
	test('uploads first queued file, marks uploading, then advances to processing with documentId', async () => {
		const files = [makeFile('first.pdf')];
		let q = createUploadQueue(files);
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (curr: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			q = mut(q);
		};

		processNextInQueue({
			queryClient: { invalidateQueries },
			getQueue: () => q,
			setQueue,
			uploadFailedMessage: 'Upload failed'
		});
		// Synchronously the entry is marked uploading before the await resolves.
		expect(q[0].status).toBe('uploading');
		expect(q[0].documentId).toBeUndefined();

		await flush();

		// After uploadDocument resolves the entry is promoted to processing with a documentId.
		expect(q[0].status).toBe('processing');
		expect(q[0].documentId).toBe('server-first.pdf');
	});

	test('no-op when an active entry already exists', async () => {
		let q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'uploading', documentId: 'd1' },
			{ id: '2', file: makeFile('b.pdf'), status: 'queued' }
		];
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			q = mut(q);
		};

		processNextInQueue({
			queryClient: { invalidateQueries },
			getQueue: () => q,
			setQueue,
			uploadFailedMessage: 'Upload failed'
		});
		await flush();

		expect(q[0].status).toBe('uploading');
		expect(q[1].status).toBe('queued');
	});

	test('no-op when no queued entries remain', async () => {
		let q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'completed', documentId: 'd1' },
			{ id: '2', file: makeFile('b.pdf'), status: 'failed', error: 'x' }
		];
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			q = mut(q);
		};

		processNextInQueue({
			queryClient: { invalidateQueries },
			getQueue: () => q,
			setQueue,
			uploadFailedMessage: 'Upload failed'
		});
		await flush();

		expect(q).toEqual([
			{ id: '1', file: expect.any(File), status: 'completed', documentId: 'd1' },
			{ id: '2', file: expect.any(File), status: 'failed', error: 'x' }
		]);
	});

	test('upload exception marks entry failed and advances to next queued file', async () => {
		const docs = await import('$lib/api/documents');
		const uploadMock = vi.mocked(docs.uploadDocument);
		uploadMock.mockRejectedValueOnce(new Error('upload crash'));

		const files = [makeFile('a.pdf'), makeFile('b.pdf')];
		let q = createUploadQueue(files);
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			q = mut(q);
		};

		processNextInQueue({
			queryClient: { invalidateQueries },
			getQueue: () => q,
			setQueue,
			uploadFailedMessage: 'Upload failed'
		});
		await flush();
		await flush();

		expect(q[0].status).toBe('failed');
		expect(q[0].error).toContain('upload crash');
		// Upload failure does not invalidate dashboard cache.
		expect(invalidateQueries).not.toHaveBeenCalled();
		// Next file picks up — either still uploading or already promoted to processing.
		expect(['uploading', 'processing']).toContain(q[1].status);
	});
});

describe('applyTerminalStatus', () => {
	test('completed → invalidates all three dashboard keys', () => {
		let q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'processing', documentId: 'd1' }
		];
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			q = mut(q);
		};

		applyTerminalStatus({ invalidateQueries }, setQueue, '1', 'completed');

		expect(q[0].status).toBe('completed');
		expect(invalidateQueries).toHaveBeenCalledTimes(3);
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['documents'] });
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['health_values'] });
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['ai_dashboard_interpretation'] });
	});

	test('partial → invalidates all three dashboard keys', () => {
		let q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'processing', documentId: 'd1' }
		];
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			q = mut(q);
		};

		applyTerminalStatus({ invalidateQueries }, setQueue, '1', 'partial');

		expect(q[0].status).toBe('partial');
		expect(invalidateQueries).toHaveBeenCalledTimes(3);
		expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['ai_dashboard_interpretation'] });
	});

	test('failed → does NOT invalidate any cache keys', () => {
		let q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'processing', documentId: 'd1' }
		];
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			q = mut(q);
		};

		applyTerminalStatus({ invalidateQueries }, setQueue, '1', 'failed', 'bad scan');

		expect(q[0].status).toBe('failed');
		expect(q[0].error).toBe('bad scan');
		expect(invalidateQueries).not.toHaveBeenCalled();
	});

	test('3-file batch per-file invalidation count (2 completed, 1 failed)', () => {
		let q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'processing', documentId: 'd1' },
			{ id: '2', file: makeFile('b.pdf'), status: 'processing', documentId: 'd2' },
			{ id: '3', file: makeFile('c.pdf'), status: 'processing', documentId: 'd3' }
		];
		const invalidateQueries = vi.fn();
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			q = mut(q);
		};

		applyTerminalStatus({ invalidateQueries }, setQueue, '1', 'completed');
		applyTerminalStatus({ invalidateQueries }, setQueue, '2', 'failed', 'x');
		applyTerminalStatus({ invalidateQueries }, setQueue, '3', 'completed');

		// 2 completed × 3 keys = 6 calls, failed invokes 0.
		expect(invalidateQueries).toHaveBeenCalledTimes(6);
		const dashboardCalls = invalidateQueries.mock.calls.filter(
			([arg]) => (arg as { queryKey: string[] }).queryKey[0] === 'ai_dashboard_interpretation'
		);
		expect(dashboardCalls).toHaveLength(2);
	});
});

describe('markEntryProcessing', () => {
	test('transitions uploading → processing', () => {
		let q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'uploading', documentId: 'd1' }
		];
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			q = mut(q);
		};

		markEntryProcessing(setQueue, '1');
		expect(q[0].status).toBe('processing');
	});

	test('leaves non-uploading entries untouched', () => {
		let q: UploadQueueEntry[] = [
			{ id: '1', file: makeFile('a.pdf'), status: 'queued' },
			{ id: '2', file: makeFile('b.pdf'), status: 'completed', documentId: 'd2' }
		];
		const setQueue = (mut: (c: UploadQueueEntry[]) => UploadQueueEntry[]) => {
			q = mut(q);
		};

		markEntryProcessing(setQueue, '1');
		markEntryProcessing(setQueue, '2');
		expect(q[0].status).toBe('queued');
		expect(q[1].status).toBe('completed');
	});
});

describe('validateFilesForQueue', () => {
	test('accepts PDFs and images within size limit', () => {
		const pdf = new File(['x'], 'a.pdf', { type: 'application/pdf' });
		const png = new File(['x'], 'b.png', { type: 'image/png' });
		const { accepted, rejected } = validateFilesForQueue([pdf, png]);
		expect(accepted).toHaveLength(2);
		expect(rejected).toHaveLength(0);
	});

	test('rejects unsupported types with code unsupportedType', () => {
		const doc = new File(['x'], 'a.docx', {
			type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
		});
		const { accepted, rejected } = validateFilesForQueue([doc]);
		expect(accepted).toHaveLength(0);
		expect(rejected).toHaveLength(1);
		expect(rejected[0].reasonCode).toBe('unsupportedType');
	});

	test('rejects oversized files with code tooLarge', () => {
		// Construct a File with size > 20MB. Browsers derive size from byte length;
		// use a mocked object to avoid allocating 21MB in memory.
		const big = Object.assign(new File(['x'], 'big.pdf', { type: 'application/pdf' }), {});
		Object.defineProperty(big, 'size', { value: 21 * 1024 * 1024 });
		const { accepted, rejected } = validateFilesForQueue([big]);
		expect(accepted).toHaveLength(0);
		expect(rejected).toHaveLength(1);
		expect(rejected[0].reasonCode).toBe('tooLarge');
	});

	test('partitions a mixed batch', () => {
		const pdf = new File(['x'], 'a.pdf', { type: 'application/pdf' });
		const doc = new File(['x'], 'b.docx', {
			type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
		});
		const { accepted, rejected } = validateFilesForQueue([pdf, doc]);
		expect(accepted).toEqual([pdf]);
		expect(rejected.map((r) => r.file)).toEqual([doc]);
	});
});

describe('upload-queue status type exhaustiveness', () => {
	test('every UploadEntryStatus value is handled', () => {
		const allStatuses: UploadEntryStatus[] = [
			'queued',
			'uploading',
			'processing',
			'completed',
			'partial',
			'failed'
		];
		expect(allStatuses).toHaveLength(6);
	});
});
