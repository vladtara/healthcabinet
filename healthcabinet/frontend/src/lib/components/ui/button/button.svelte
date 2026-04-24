<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes, HTMLAnchorAttributes } from 'svelte/elements';

	type Variant = 'primary' | 'standard' | 'destructive' | 'toolbar' | 'tab';

	interface BaseProps {
		children?: Snippet;
		variant?: Variant;
		active?: boolean;
	}

	type Props = BaseProps &
		(({ href: string } & HTMLAnchorAttributes) | ({ href?: undefined } & HTMLButtonAttributes));

	let {
		children,
		class: className,
		variant = 'standard',
		active = false,
		href,
		...rest
	}: Props = $props();

	let classes = $derived(`hc-button btn-${variant} ${className ?? ''}`.trim());
</script>

{#if href}
	{#if variant === 'tab'}
		<a {href} class={classes} role="tab" aria-selected={active} {...rest as HTMLAnchorAttributes}>
			{@render children?.()}
		</a>
	{:else}
		<a {href} class={classes} {...rest as HTMLAnchorAttributes}>
			{@render children?.()}
		</a>
	{/if}
{:else if variant === 'tab'}
	<button class={classes} role="tab" aria-selected={active} {...rest as HTMLButtonAttributes}>
		{@render children?.()}
	</button>
{:else}
	<button class={classes} {...rest as HTMLButtonAttributes}>
		{@render children?.()}
	</button>
{/if}
