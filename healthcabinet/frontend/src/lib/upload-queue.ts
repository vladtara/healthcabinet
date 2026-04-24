import { uploadDocument } from '$lib/api/documents';

export type UploadEntryStatus =
	| 'queued'
	| 'uploading'
	| 'processing'
	| 'completed'
	| 'partial'
	| 'failed';

export type QueueStatus = 'idle' | 'active' | 'summary';

export interface UploadQueueEntry {
	id: string;
	file: File;
	status: UploadEntryStatus;
	documentId?: string;
	error?: string;
}

export const TERMINAL_STATUSES: ReadonlySet<UploadEntryStatus> = new Set<UploadEntryStatus>([
	'completed',
	'partial',
	'failed'
]);

const DASHBOARD_INVALIDATION_KEYS = ['documents', 'health_values'];

type InvalidateQueryArg = {
	queryKey: string[];
	refetchType?: 'active' | 'inactive' | 'all' | 'none';
};

export function isTerminal(status: UploadEntryStatus): boolean {
	return TERMINAL_STATUSES.has(status);
}

function generateEntryId(): string {
	if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
		return crypto.randomUUID();
	}
	return `entry-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createUploadQueue(files: File[]): UploadQueueEntry[] {
	return files.map((file) => ({
		id: generateEntryId(),
		file,
		status: 'queued' as const
	}));
}

export function getActiveEntry(queue: UploadQueueEntry[]): UploadQueueEntry | undefined {
	return queue.find((e) => e.status === 'uploading' || e.status === 'processing');
}

export function getQueueStatus(queue: UploadQueueEntry[]): QueueStatus {
	if (queue.length === 0) return 'idle';
	if (queue.every((e) => isTerminal(e.status))) return 'summary';
	return 'active';
}

export function countByStatus(queue: UploadQueueEntry[]): Record<UploadEntryStatus, number> {
	const counts: Record<UploadEntryStatus, number> = {
		queued: 0,
		uploading: 0,
		processing: 0,
		completed: 0,
		partial: 0,
		failed: 0
	};
	for (const entry of queue) counts[entry.status] += 1;
	return counts;
}

/**
 * Pure transition: promotes the first queued entry to `uploading` when no active
 * entry exists. Returns the queue unchanged if an entry is already active or no
 * queued entries remain. Does NOT initiate any IO — callers orchestrate side
 * effects separately.
 */
export function advanceQueue(queue: UploadQueueEntry[]): UploadQueueEntry[] {
	if (queue.length === 0) return queue;
	if (getActiveEntry(queue)) return queue;

	const idx = queue.findIndex((e) => e.status === 'queued');
	if (idx === -1) return queue;

	return queue.map((entry, i) => (i === idx ? { ...entry, status: 'uploading' as const } : entry));
}

interface QueryClientLike {
	invalidateQueries: (arg: InvalidateQueryArg) => unknown;
}

type QueueMutator = (mutate: (current: UploadQueueEntry[]) => UploadQueueEntry[]) => void;

interface ProcessQueueOptions {
	queryClient: QueryClientLike;
	getQueue: () => UploadQueueEntry[];
	setQueue: QueueMutator;
	/** Locale-aware fallback message when a non-Error rejection is caught. Required so the helper never fabricates an English string. */
	uploadFailedMessage: string;
}

function updateEntry(
	setQueue: QueueMutator,
	entryId: string,
	patch: Partial<UploadQueueEntry>
): void {
	setQueue((current) => current.map((e) => (e.id === entryId ? { ...e, ...patch } : e)));
}

/**
 * Upload the first queued file and attach its documentId. Once `documentId` is
 * set on the entry, the UI's ProcessingPipeline subscribes to SSE and drives the
 * entry's terminal transition via `applyTerminalStatus`. If the upload call
 * itself throws, the entry is marked `failed` and the next queued file is
 * started.
 *
 * Safe to call when an active entry already exists — it is a no-op.
 */
export function processNextInQueue(options: ProcessQueueOptions): void {
	const { queryClient, getQueue, setQueue } = options;

	const current = getQueue();
	if (getActiveEntry(current)) return;
	const queuedIdx = current.findIndex((e) => e.status === 'queued');
	if (queuedIdx === -1) return;

	const entryId = current[queuedIdx].id;
	const file = current[queuedIdx].file;

	updateEntry(setQueue, entryId, { status: 'uploading' });

	void (async () => {
		try {
			const doc = await uploadDocument(file);
			// Upload succeeded — promote to `processing` so the UI pipeline picks up.
			updateEntry(setQueue, entryId, { documentId: doc.id, status: 'processing' });
		} catch (error) {
			const message =
				error instanceof Error ? error.message : options.uploadFailedMessage;
			updateEntry(setQueue, entryId, { status: 'failed', error: message });
			// Start the next file once the current one failed at upload-time.
			// Forward the full options object so the recursive call carries the
			// required `uploadFailedMessage` — the helper does not fabricate a
			// default (see ProcessQueueOptions jsdoc).
			processNextInQueue(options);
		}
	})();
}

/**
 * Transition an entry to a terminal status in response to a ProcessingPipeline
 * terminal event. Also performs dashboard-cache invalidation for successful
 * terminal states (completed / partial) and skips it for `failed`, matching
 * Story 15.3's invalidation contract. Does NOT advance the queue — callers
 * invoke `processNextInQueue` after this to start the next file.
 */
export function applyTerminalStatus(
	queryClient: QueryClientLike,
	setQueue: QueueMutator,
	entryId: string,
	status: 'completed' | 'partial' | 'failed',
	errorMessage?: string
): void {
	// Callers must supply a locale-aware `errorMessage` when `status === 'failed'`.
	// The helper itself stays pure — it never fabricates English fallbacks, since
	// a fallback here would silently regress i18n for any future non-en caller.
	updateEntry(setQueue, entryId, {
		status,
		error: status === 'failed' ? errorMessage : undefined
	});

		if (status === 'completed' || status === 'partial') {
			for (const key of DASHBOARD_INVALIDATION_KEYS) {
				queryClient.invalidateQueries({ queryKey: [key] });
			}
			queryClient.invalidateQueries({
				queryKey: ['ai_dashboard_interpretation'],
				refetchType: 'none'
			});
		}
	}

/**
 * ProcessingPipeline reports `onEvent` before the terminal event. Call this
 * from the panel's first non-terminal callback to lift the active entry from
 * `uploading` to `processing` so the UI reflects real progress.
 */
export function markEntryProcessing(setQueue: QueueMutator, entryId: string): void {
	setQueue((current) =>
		current.map((e) => (e.id === entryId && e.status === 'uploading' ? { ...e, status: 'processing' } : e))
	);
}

/**
 * Validation helpers — mirror the per-file checks inside `DocumentUploadZone` so
 * invalid files are rejected before they ever reach the queue.
 */
export const MAX_FILE_SIZE = 20 * 1024 * 1024;
export const ACCEPTED_FILE_TYPES = ['image/', 'application/pdf'] as const;

export type ValidationReasonCode = 'unsupportedType' | 'tooLarge';

export interface FileValidationRejection {
	file: File;
	reasonCode: ValidationReasonCode;
}

export interface FileValidationResultCoded {
	accepted: File[];
	rejected: FileValidationRejection[];
}

/**
 * Validate selected files for the upload queue.
 *
 * Returns rejection **reason codes** rather than localized strings so the
 * helper stays pure (no browser-only state, no locale coupling). Callers
 * resolve codes to locale-aware copy at render time via the message catalog,
 * which keeps the i18n boundary at the UI layer where it belongs.
 */
export function validateFilesForQueue(files: File[]): FileValidationResultCoded {
	const accepted: File[] = [];
	const rejected: FileValidationRejection[] = [];
	for (const file of files) {
		if (!ACCEPTED_FILE_TYPES.some((t) => file.type.startsWith(t))) {
			rejected.push({ file, reasonCode: 'unsupportedType' });
			continue;
		}
		if (file.size > MAX_FILE_SIZE) {
			rejected.push({ file, reasonCode: 'tooLarge' });
			continue;
		}
		accepted.push(file);
	}
	return { accepted, rejected };
}
