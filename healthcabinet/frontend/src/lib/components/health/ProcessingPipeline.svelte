<script lang="ts">
	import { streamDocumentStatus, type DocumentStatusEvent } from '$lib/api/documents';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).upload);

	// Internal event-id sequence so the locale change can retranslate stage
	// labels at render time without replaying SSE events.
	const STAGE_IDS = [
		'document.upload_started',
		'document.reading',
		'document.extracting',
		'document.generating',
		'document.completed'
	] as const;

	type StageStatus = 'done' | 'active' | 'pending' | 'error';

	type FailureReason = 'failed' | 'partial' | 'stream-error';

	interface Props {
		documentId: string;
		onComplete: () => void;
		onFailed: (reason?: FailureReason) => void;
		onAuthError?: () => void;
	}

	let { documentId, onComplete, onFailed, onAuthError }: Props = $props();

	function stageLabelFor(id: string): string {
		switch (id) {
			case 'document.upload_started':
				return copy.pipelineStageUploading;
			case 'document.reading':
				return copy.pipelineStageReading;
			case 'document.extracting':
				return copy.pipelineStageExtracting;
			case 'document.generating':
				return copy.pipelineStageGenerating;
			case 'document.completed':
				return copy.pipelineStageComplete;
			default:
				return '';
		}
	}

	const TERMINAL_EVENTS = new Set(['document.completed', 'document.failed', 'document.partial']);

	// Keep only the per-stage status in $state; label is derived at render
	// time from the id so it retranslates when the user flips locale mid-stream.
	interface StageState {
		id: string;
		status: StageStatus;
	}

	// Which status-announcement category is active, if any. The resolved
	// localized string is derived below so the aria-live region retranslates
	// on locale flip. `custom` carries a backend-supplied string verbatim
	// (AC 5 — server text passes through untranslated).
	type StatusKey = 'processing' | 'partial-fallback' | 'failed-fallback' | 'conn-lost' | 'session-expired' | 'stage-label' | 'custom';

	function createInitialStages(): StageState[] {
		return STAGE_IDS.map((id) => ({ id, status: 'pending' as const }));
	}

	let stages = $state<StageState[]>(createInitialStages());
	let statusKey = $state<StatusKey>('processing');
	let statusStageId = $state<string>('');
	let statusCustomMessage = $state<string>('');
	let consecutiveErrors = $state(0);

	const statusAnnouncement = $derived.by(() => {
		switch (statusKey) {
			case 'processing':
				return copy.pipelineStatusProcessing;
			case 'partial-fallback':
				return copy.pipelineStatusPartialFallback;
			case 'failed-fallback':
				return copy.pipelineStatusFailedFallback;
			case 'conn-lost':
				return copy.pipelineStatusConnLost;
			case 'session-expired':
				return copy.pipelineStatusSessionExpired;
			case 'stage-label':
				return stageLabelFor(statusStageId) || copy.pipelineStatusProcessing;
			case 'custom':
				return statusCustomMessage;
			default:
				return copy.pipelineStatusProcessing;
		}
	});

	function resetPipeline(): void {
		stages = createInitialStages();
		statusKey = 'processing';
		statusStageId = '';
		statusCustomMessage = '';
		consecutiveErrors = 0;
		lastProgressedIdx = -1;
	}

	// Track the index of the last successfully progressed stage so failure states
	// only mark stages that actually ran as done, not all prior stages.
	let lastProgressedIdx = $state(-1);

	const progressValue = $derived(stages.filter((s) => s.status === 'done').length * 25);

	function updateStage(event: DocumentStatusEvent): void {
		const eventName = event.event;
		const idx = STAGE_IDS.findIndex((id) => id === eventName);
		if (idx === -1) {
			// Terminal failure event (document.failed, document.partial) — not in STAGE_IDS.
			// Only mark stages up to the last progressed index as done.
			stages = STAGE_IDS.map((id, i) => ({
				id,
				status: i <= lastProgressedIdx ? 'done' : i === lastProgressedIdx + 1 ? 'error' : 'pending'
			}));
			if (event.message) {
				statusKey = 'custom';
				statusCustomMessage = event.message;
			} else {
				statusKey = eventName === 'document.partial' ? 'partial-fallback' : 'failed-fallback';
			}
			return;
		}
		lastProgressedIdx = idx;
		stages = STAGE_IDS.map((id, i) => {
			if (eventName === 'document.completed') return { id, status: 'done' as const };
			if (i < idx) return { id, status: 'done' as const };
			if (i === idx) return { id, status: 'active' as const };
			return { id, status: 'pending' as const };
		});
		if (event.message) {
			statusKey = 'custom';
			statusCustomMessage = event.message;
		} else {
			statusKey = 'stage-label';
			statusStageId = STAGE_IDS[idx];
		}
	}

	function markFailureStages(): void {
		stages = STAGE_IDS.map((id, i) => ({
			id,
			status: i <= lastProgressedIdx ? 'done' : i === lastProgressedIdx + 1 ? 'error' : 'pending'
		}));
	}

	function handleStreamError(): boolean {
		consecutiveErrors += 1;
		if (consecutiveErrors < 3) return false;
		markFailureStages();
		statusKey = 'conn-lost';
		return true;
	}

	function handleAuthError(): void {
		markFailureStages();
		statusKey = 'session-expired';
	}

	function failPipeline(message: 'auth-error' | 'stream-error'): void {
		if (message === 'auth-error') {
			handleAuthError();
			if (onAuthError) {
				onAuthError();
				return;
			}
		} else if (!handleStreamError()) {
			return;
		}

		onFailed('stream-error');
	}

	$effect(() => {
		resetPipeline();
		if (!documentId) return;

		const controller = new AbortController();
		let terminated = false;

		streamDocumentStatus(
			documentId,
			controller.signal,
			(event: DocumentStatusEvent) => {
				if (terminated) return;
				consecutiveErrors = 0;
				updateStage(event);
				if (TERMINAL_EVENTS.has(event.event)) {
					terminated = true;
					controller.abort();
					if (event.event === 'document.completed') {
						onComplete();
					} else if (event.event === 'document.partial') {
						onFailed('partial');
					} else {
						onFailed('failed');
					}
				}
			},
			(errorType) => {
				if (terminated) return;
				if (errorType === 'auth-error') {
					terminated = true;
					controller.abort();
					failPipeline('auth-error');
					return;
				}

				if (handleStreamError()) {
					terminated = true;
					controller.abort();
					onFailed('stream-error');
				}
			}
		);

		return () => controller.abort();
	});
</script>

<div role="status" class="hc-pipeline-container">
	<div aria-live="polite" class="sr-only">{statusAnnouncement}</div>

	<ol class="hc-pipeline-stages">
		{#each stages as stage (stage.id)}
			<li class="hc-pipeline-stage hc-pipeline-stage-{stage.status}">
				<span class="hc-pipeline-symbol" aria-hidden="true">
					{#if stage.status === 'done'}✅{:else if stage.status === 'active'}⏳{:else if stage.status === 'error'}✕{:else}○{/if}
				</span>
				<span class="hc-pipeline-label">{stageLabelFor(stage.id)}</span>
				<span class="hc-pipeline-status-label">
					{#if stage.status === 'done'}{copy.pipelineStageStatusComplete}{:else if stage.status === 'active'}{copy.pipelineStageStatusInProgress}{:else if stage.status === 'error'}{copy.pipelineStageStatusFailed}{:else}{copy.pipelineStageStatusPending}{/if}
				</span>
			</li>
		{/each}
	</ol>

	<progress class="hc-pipeline-progress" value={progressValue} max="100"></progress>
</div>
