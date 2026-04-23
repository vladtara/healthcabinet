<script lang="ts">
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).upload);

	interface Props {
		status: 'partial' | 'failed';
		documentId: string;
		onReupload: (documentId: string) => void;
		onKeepPartial?: (documentId: string) => void;
		isKeepingPartial?: boolean;
	}

	let { status, documentId, onReupload, onKeepPartial, isKeepingPartial = false }: Props = $props();

	const photoTips = $derived([
		{ icon: '💡', label: copy.tipLightingLabel, detail: copy.tipLightingDetail },
		{ icon: '📄', label: copy.tipFlatLabel, detail: copy.tipFlatDetail },
		{ icon: '🌑', label: copy.tipNoShadowsLabel, detail: copy.tipNoShadowsDetail }
	]);
</script>

<div
	class="hc-recovery-card {status === 'partial' ? 'hc-recovery-card-partial' : 'hc-recovery-card-failed'}"
	role="region"
	aria-label={status === 'partial' ? copy.recoveryAriaPartial : copy.recoveryAriaFailed}
>
	<div>
		{#if status === 'partial'}
			<h3 class="hc-recovery-heading">{copy.recoveryPartialHeading}</h3>
			<p class="hc-recovery-desc">
				{copy.recoveryPartialDesc}
			</p>
		{:else}
			<h3 class="hc-recovery-heading">{copy.recoveryFailedHeading}</h3>
			<p class="hc-recovery-desc">
				{copy.recoveryFailedDesc}
			</p>
		{/if}
	</div>

	<div class="hc-recovery-tips" aria-label={copy.recoveryTipsAria}>
		<p class="hc-recovery-tips-header">{copy.recoveryTipsHeader}</p>
		<ul class="hc-recovery-tips-list" role="list">
			{#each photoTips as tip (tip.label)}
				<li class="hc-recovery-tip">
					<span class="hc-recovery-tip-icon" aria-hidden="true">{tip.icon}</span>
					<div>
						<p class="hc-recovery-tip-label">{tip.label}</p>
						<p class="hc-recovery-tip-detail">{tip.detail}</p>
					</div>
				</li>
			{/each}
		</ul>
	</div>

	<div class="hc-recovery-actions">
		<button
			type="button"
			class="hc-recovery-btn-primary"
			onclick={() => onReupload(documentId)}
		>
			{copy.recoveryReupload}
		</button>

		{#if status === 'partial' && onKeepPartial}
			<button
				type="button"
				class="hc-recovery-btn-secondary"
				onclick={() => onKeepPartial?.(documentId)}
				disabled={isKeepingPartial}
			>
				{isKeepingPartial ? copy.recoveryKeepPartialSaving : copy.recoveryKeepPartial}
			</button>
		{/if}
	</div>
</div>
