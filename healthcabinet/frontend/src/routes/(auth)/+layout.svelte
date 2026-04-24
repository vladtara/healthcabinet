<script lang="ts">
	// Public layout — no auth guard
	import { LocaleToggle } from '$lib/components/ui/locale-toggle';

	interface Props {
		children: import('svelte').Snippet;
	}
	let { children }: Props = $props();
</script>

<div class="hc-auth-layout bg-background flex min-h-screen flex-col items-center justify-center">
	<div class="hc-auth-locale-corner">
		<LocaleToggle />
	</div>
	{@render children()}
</div>
