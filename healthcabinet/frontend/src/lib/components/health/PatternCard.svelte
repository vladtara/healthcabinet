<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { getAiPatterns } from '$lib/api/ai';
	import type { PatternObservation } from '$lib/api/ai';
	import { authStore } from '$lib/stores/auth.svelte';

	const userId = $derived(authStore.user?.id ?? null);

	const patternsQuery = createQuery(() => ({
		queryKey: ['ai_patterns', userId] as const,
		enabled: userId !== null,
		queryFn: () => getAiPatterns(),
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
			class="mt-4 border-l-4 border-l-[#E07020] rounded-md bg-card/50 p-4"
		>
			<h3 class="mb-2 text-base font-semibold text-foreground">Pattern Observed</h3>
			<p class="mb-2 text-[15px] leading-relaxed text-foreground">{pattern.description}</p>
			<p class="mb-1 text-[12px] text-muted-foreground">
				Spans: {pattern.document_dates.join(' · ')}
			</p>
			<p class="text-[11px] text-muted-foreground">{pattern.recommendation}</p>
		</section>
	{/each}
{/if}
