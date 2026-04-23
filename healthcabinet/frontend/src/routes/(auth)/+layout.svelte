<script lang="ts">
	// Public layout — no auth guard
	import { LocaleToggle } from '$lib/components/ui/locale-toggle';

	interface Props {
		children: import('svelte').Snippet;
	}
	let { children }: Props = $props();
</script>

<div class="hc-auth-layout flex min-h-screen flex-col items-center justify-center bg-background">
	<div class="hc-auth-locale-corner">
		<LocaleToggle />
	</div>
	{@render children()}
</div>
