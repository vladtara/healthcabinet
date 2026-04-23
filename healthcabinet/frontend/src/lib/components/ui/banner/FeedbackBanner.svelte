<script lang="ts">
	type BannerType = 'info' | 'success' | 'error' | 'warning';

	interface Props {
		type: BannerType;
		message: string;
		dismissible?: boolean;
		onDismiss?: () => void;
	}
	let { type, message, dismissible = false, onDismiss }: Props = $props();

	const icons: Record<BannerType, string> = {
		info: 'ℹ',
		success: '✓',
		error: '✕',
		warning: '⚠'
	};

	const role = $derived(type === 'error' ? 'alert' : 'status');

	let dismissed = $state(false);

	function handleDismiss() {
		dismissed = true;
		onDismiss?.();
	}
</script>

{#if !dismissed}
	<div class="hc-banner hc-banner-{type}" {role}>
		<span class="hc-banner-icon" aria-hidden="true">{icons[type]}</span>
		<span class="hc-banner-message">{message}</span>
		{#if dismissible}
			<button
				class="hc-banner-dismiss"
				onclick={handleDismiss}
				aria-label="Dismiss banner"
			>×</button>
		{/if}
	</div>
{/if}
