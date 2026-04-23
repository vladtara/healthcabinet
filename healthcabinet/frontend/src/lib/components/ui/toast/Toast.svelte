<script lang="ts">
	import type { ToastType } from '$lib/stores/feedback.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).toast);

	interface Props {
		type: ToastType;
		message: string;
		onDismiss?: () => void;
	}
	let { type, message, onDismiss }: Props = $props();

	const icons: Record<ToastType, string> = {
		success: '✓',
		error: '✕',
		warning: '⚠'
	};

	const role = $derived(type === 'error' ? 'alert' : 'status');
</script>

<div class="hc-toast hc-toast-{type}" {role}>
	<span class="hc-toast-icon" aria-hidden="true">{icons[type]}</span>
	<span class="hc-toast-message">{message}</span>
	{#if onDismiss}
		<button
			class="hc-toast-dismiss"
			onclick={onDismiss}
			aria-label={copy.dismiss}
		>×</button>
	{/if}
</div>
