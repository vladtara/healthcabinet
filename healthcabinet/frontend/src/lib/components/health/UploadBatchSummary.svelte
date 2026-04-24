<script lang="ts">
	import { countByStatus, type UploadQueueEntry } from '$lib/upload-queue';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).upload);

	interface Props {
		queue: UploadQueueEntry[];
		onStartAnother: () => void;
	}

	let { queue, onStartAnother }: Props = $props();

	const counts = $derived(countByStatus(queue));
	const successfulEntries = $derived(
		queue.filter((e) => (e.status === 'completed' || e.status === 'partial') && e.documentId)
	);
	const failedEntries = $derived(queue.filter((e) => e.status === 'failed'));
</script>

<section
	aria-label={copy.batchSummaryAria}
	style="display: flex; flex-direction: column; gap: 14px;"
>
	<h3 style="margin: 0; font-size: 16px;">{copy.batchCompleteHeader}</h3>
	<p aria-live="polite" style="margin: 0; display: flex; gap: 16px; font-size: 13px;">
		<span>✓ {counts.completed} {copy.queueCompleteLabel}</span>
		<span>⚠ {counts.partial} {copy.queuePartialLabel}</span>
		<span>✕ {counts.failed} {copy.queueFailedLabel}</span>
	</p>

	{#if successfulEntries.length > 0}
		<div>
			<p
				style="margin: 0 0 6px; font-size: 12px; color: var(--text-muted, #8a8f98); text-transform: uppercase; letter-spacing: 0.04em;"
			>
				{copy.batchSuccessfulHeader}
			</p>
			<ul
				role="list"
				style="list-style: none; padding: 0; margin: 0; border: 1px solid var(--surface-raised, #2a2e38);"
			>
				{#each successfulEntries as entry (entry.id)}
					<li
						style="display: grid; grid-template-columns: auto 1fr auto auto; align-items: center; gap: 10px; padding: 6px 10px; border-bottom: 1px solid var(--surface-raised, #2a2e38);"
					>
						<span aria-hidden="true">📄</span>
						<span
							title={entry.file.name}
							style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
						>
							{entry.file.name}
						</span>
						<span
							class={entry.status === 'partial'
								? 'hc-badge hc-badge-warning'
								: 'hc-pipeline-stage-done'}
							style={entry.status === 'partial'
								? 'font-size: 11px;'
								: 'padding: 2px 6px; font-size: 11px; border: 1px solid var(--surface-raised, #2a2e38); border-radius: 2px;'}
						>
							{entry.status === 'partial' ? copy.batchStatusPartial : copy.batchStatusComplete}
						</span>
						{#if entry.documentId}
							<a
								href={`/documents/${entry.documentId}`}
								style="font-size: 12px; text-decoration: underline;"
							>
								{copy.batchViewResult}
							</a>
						{/if}
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if failedEntries.length > 0}
		<div>
			<p
				style="margin: 0 0 6px; font-size: 12px; color: var(--text-muted, #8a8f98); text-transform: uppercase; letter-spacing: 0.04em;"
			>
				{copy.batchFailedHeader}
			</p>
			<ul
				role="list"
				style="list-style: none; padding: 0; margin: 0; border: 1px solid var(--surface-raised, #2a2e38);"
			>
				{#each failedEntries as entry (entry.id)}
					<li
						style="display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; padding: 6px 10px; border-bottom: 1px solid var(--surface-raised, #2a2e38);"
					>
						<span aria-hidden="true">📄</span>
						<span
							title={entry.file.name}
							style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
						>
							{entry.file.name}
						</span>
						<span
							class="hc-pipeline-stage-error"
							style="padding: 2px 6px; font-size: 11px; border: 1px solid var(--surface-raised, #2a2e38); border-radius: 2px;"
						>
							{copy.batchStatusFailed}
						</span>
						{#if entry.error}
							<span
								style="grid-column: 1 / -1; font-size: 11px; color: var(--status-action, #e05252);"
							>
								{entry.error}
							</span>
						{/if}
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<div style="display: flex; gap: 8px;">
		<button type="button" class="hc-recovery-btn-primary" onclick={() => onStartAnother()}>
			{copy.batchUploadAnother}
		</button>
	</div>
</section>
