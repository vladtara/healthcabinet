<script lang="ts">
	import { feedbackStore, dismissToast } from '$lib/stores/feedback.svelte';
	import Toast from './Toast.svelte';
</script>

<div role="region" aria-label="Notifications" aria-live="polite" class="hc-toast-container">
	{#each feedbackStore.toasts as toast (toast.id)}
		<Toast type={toast.type} message={toast.message} onDismiss={() => dismissToast(toast.id)} />
	{/each}
</div>
