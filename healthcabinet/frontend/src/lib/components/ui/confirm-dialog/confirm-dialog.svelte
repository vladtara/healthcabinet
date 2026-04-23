<script lang="ts">
	import type { Snippet } from 'svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const dialogCopy = $derived(t(localeStore.locale).confirmDialog);

	type ConfirmVariant = 'destructive' | 'primary' | 'standard';

	interface Props {
		/** Bindable. Parent owns dialog open/close state. */
		open: boolean;
		/** Shown in the dialog title bar. Also used as the default aria-label. */
		title: string;
		/** Text on the primary confirm button (e.g., "Delete My Account"). */
		confirmLabel: string;
		/** Visual weight of the confirm button. Default: 'destructive'. */
		confirmVariant?: ConfirmVariant;
		/** Text on the cancel button. Default: 'Cancel'. */
		cancelLabel?: string;
		/** Gate for the confirm button (e.g., type-to-confirm match). Default: true. */
		canConfirm?: boolean;
		/** When true, disables both buttons, blocks Escape/backdrop close, and swaps confirm label. */
		loading?: boolean;
		/** Text shown on the confirm button while `loading` is true. Default: 'Working...'. */
		loadingLabel?: string;
		/** Override aria-label when it must differ from the visible title. */
		ariaLabel?: string;
		/**
		 * Called when the user clicks confirm. The component does NOT auto-close on confirm —
		 * the caller owns the dialog lifecycle via `bind:open`. This is intentional: async
		 * handlers often need to keep the dialog open during work (loading state) and only
		 * close on success. Set `loading` during the operation and `open = false` on success.
		 */
		onConfirm: () => void | Promise<void>;
		children?: Snippet;
	}

	let {
		open = $bindable(),
		title,
		confirmLabel,
		confirmVariant = 'destructive',
		cancelLabel,
		canConfirm = true,
		loading = false,
		loadingLabel,
		ariaLabel,
		onConfirm,
		children
	}: Props = $props();

	// Locale-aware defaults when caller does not override.
	const resolvedCancelLabel = $derived(cancelLabel ?? dialogCopy.cancel);
	const resolvedLoadingLabel = $derived(loadingLabel ?? dialogCopy.working);

	let panelEl = $state<HTMLDivElement | undefined>();
	let previouslyFocused: HTMLElement | null = null;
	let wasOpen = false;
	let confirmInFlight = $state(false);

	const confirmClass = $derived(
		confirmVariant === 'primary'
			? 'btn-primary'
			: confirmVariant === 'standard'
				? 'btn-standard'
				: 'btn-destructive'
	);

	function close() {
		if (loading) return;
		open = false;
	}

	async function handleConfirm() {
		if (confirmInFlight) return;
		confirmInFlight = true;
		try {
			await onConfirm();
		} finally {
			confirmInFlight = false;
		}
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
			previouslyFocused =
				document.activeElement instanceof HTMLElement ? document.activeElement : null;
			const frame = requestAnimationFrame(() => {
				panelEl?.focus();
			});
			wasOpen = true;
			return () => cancelAnimationFrame(frame);
		}

		if (!open && wasOpen) {
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
	<div class="hc-dialog-backdrop" onclick={handleBackdropClick}>
		<div
			bind:this={panelEl}
			class="hc-dialog-panel"
			role="dialog"
			aria-modal="true"
			aria-label={ariaLabel ?? title}
			tabindex="-1"
			onclick={(e) => e.stopPropagation()}
			onkeydown={handleKeydown}
		>
			<div class="hc-dialog-title">{title}</div>
			<div class="hc-dialog-body">
				{@render children?.()}
			</div>
			<div class="hc-dialog-actions">
				<button type="button" class="btn-standard" onclick={close} disabled={loading}>
					{resolvedCancelLabel}
				</button>
				<button
					type="button"
					class={confirmClass}
					onclick={handleConfirm}
					disabled={!canConfirm || loading || confirmInFlight}
				>
					{loading ? resolvedLoadingLabel : confirmLabel}
				</button>
			</div>
		</div>
	</div>
{/if}
