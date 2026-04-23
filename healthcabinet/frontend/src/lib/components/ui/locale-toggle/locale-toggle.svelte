<script lang="ts">
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	interface Props {
		class?: string;
	}
	let { class: className = '' }: Props = $props();

	const copy = $derived(t(localeStore.locale).localeToggle);
	const isEn = $derived(localeStore.locale === 'en');
	const isUk = $derived(localeStore.locale === 'uk');

	function select(next: 'en' | 'uk') {
		localeStore.setLocale(next);
	}
</script>

<div
	class="hc-locale-toggle {className}"
	role="group"
	aria-label={copy.label}
	data-testid="locale-toggle"
>
	<button
		type="button"
		class="hc-locale-toggle-btn"
		aria-pressed={isEn}
		aria-label={copy.ariaEn}
		onclick={() => select('en')}
	>
		{copy.en}
	</button>
	<button
		type="button"
		class="hc-locale-toggle-btn"
		aria-pressed={isUk}
		aria-label={copy.ariaUk}
		onclick={() => select('uk')}
	>
		{copy.uk}
	</button>
</div>
