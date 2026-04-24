<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { getAiPatterns } from '$lib/api/ai';
	import type { PatternObservation } from '$lib/api/ai';
	import { authStore } from '$lib/stores/auth.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';

	const userId = $derived(authStore.user?.id ?? null);

	const patternsQuery = createQuery(() => ({
		queryKey: ['ai_patterns', userId, localeStore.locale] as const,
		enabled: userId !== null,
		queryFn: () => getAiPatterns(localeStore.locale),
		retry: false,
		staleTime: 5 * 60 * 1000
	}));

	function patternKey(pattern: PatternObservation, index: number): string {
		return `${pattern.description}-${pattern.document_dates.join('-')}-${index}`;
	}
</script>

{#if patternsQuery.data && patternsQuery.data.patterns.length > 0}
	{#each patternsQuery.data.patterns as pattern, index (patternKey(pattern, index))}
		<section
			aria-label={`Health Pattern Observation ${index + 1} of ${patternsQuery.data.patterns.length}`}
			class="bg-card/50 mt-4 rounded-md border-l-4 border-l-[#E07020] p-4"
		>
			<h3 class="text-foreground mb-2 text-base font-semibold">Pattern Observed</h3>
			<p class="text-foreground mb-2 text-[15px] leading-relaxed">{pattern.description}</p>
			<p class="text-muted-foreground mb-1 text-[12px]">
				Spans: {pattern.document_dates.join(' · ')}
			</p>
			<p class="text-muted-foreground text-[11px]">{pattern.recommendation}</p>
		</section>
	{/each}
{/if}
