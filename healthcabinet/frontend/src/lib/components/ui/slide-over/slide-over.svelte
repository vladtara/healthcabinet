<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		open: boolean;
		title: string;
		children?: Snippet;
		class?: string;
	}

	let { open = $bindable(), title, children, class: className }: Props = $props();

	let panelEl = $state<HTMLDivElement | undefined>();
	let entered = $state(false);
	let previouslyFocused: HTMLElement | null = null;
	let wasOpen = false;

	function close() {
		open = false;
	}

	function handleBackdropClick() {
		close();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			close();
			return;
		}

		if (e.key === 'Tab') {
			const focusable = getFocusableElements();
			if (focusable.length === 0) {
				e.preventDefault();
				panelEl?.focus();
				return;
			}

			const current = document.activeElement as HTMLElement | null;
			const currentIndex = current ? focusable.indexOf(current) : -1;
			const direction = e.shiftKey ? -1 : 1;
			const nextIndex =
				currentIndex === -1
					? e.shiftKey
						? focusable.length - 1
						: 0
					: (currentIndex + direction + focusable.length) % focusable.length;

			e.preventDefault();
			focusable[nextIndex]?.focus();
		}
	}

	function getFocusableElements(): HTMLElement[] {
		if (!panelEl) return [];
		return Array.from(
			panelEl.querySelectorAll<HTMLElement>(
				'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
			)
		);
	}

	$effect(() => {
		if (open && panelEl && !wasOpen) {
			previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
			entered = false;
			const frame = requestAnimationFrame(() => {
				entered = true;
				panelEl?.focus();
			});
			wasOpen = true;
			return () => cancelAnimationFrame(frame);
		}

		if (!open && wasOpen) {
			entered = false;
			if (previouslyFocused?.isConnected) {
				previouslyFocused.focus();
			}
			previouslyFocused = null;
			wasOpen = false;
		}
	});
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="hc-slide-over-backdrop" onclick={handleBackdropClick}>
	</div>
	<div
		bind:this={panelEl}
		class={`hc-slide-over hc-window ${entered ? 'hc-slide-over-enter' : ''} ${className ?? ''}`.trim()}
		role="dialog"
		aria-modal="true"
		aria-label={title}
		tabindex="-1"
		onkeydown={handleKeydown}
	>
		<div class="title-bar">
			<div class="title-bar-text">{title}</div>
			<div class="title-bar-controls">
				<button type="button" aria-label="Close" onclick={close}></button>
			</div>
		</div>
		<div class="hc-slide-over-body">
			{@render children?.()}
		</div>
	</div>
{/if}
