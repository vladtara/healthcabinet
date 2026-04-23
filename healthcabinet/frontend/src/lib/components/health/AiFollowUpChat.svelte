<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { getDocumentInterpretation, streamAiChat } from '$lib/api/ai';
	import type { ApiError } from '$lib/api/client.svelte';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Button } from '$lib/components/ui/button';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).aiChat);

	type FollowUpErrorKey = '' | 'generic' | 'streaming' | 'network' | 'custom';

	interface Props {
		documentId: string;
	}

	let { documentId }: Props = $props();

	let question = $state('');
	let isStreaming = $state(false);
	let waitingForFirstChunk = $state(false);
	let streamedAnswer = $state('');
	let errorKey = $state<FollowUpErrorKey>('');
	let errorCustomMessage = $state('');

	// Derived message — retranslates if the user toggles locale while an error banner is visible.
	const errorMessage = $derived.by(() => {
		switch (errorKey) {
			case 'generic':
				return copy.errorGeneric;
			case 'streaming':
				return copy.errorStreaming;
			case 'network':
				return copy.followUpErrorNetwork;
			case 'custom':
				return errorCustomMessage;
			default:
				return '';
		}
	});

	let activeController: AbortController | null = null;

	// Gate the form on the interpretation query — reuse cached data instead of a separate readiness query
	const interpretationQuery = createQuery(() => ({
		queryKey: ['ai_interpretation', documentId] as const,
		queryFn: () => getDocumentInterpretation(documentId),
		retry: false
	}));

	function is404(error: unknown): boolean {
		return (error as ApiError)?.status === 404;
	}

	// Reset local state whenever the user navigates to a different document
	// and cancel any in-flight stream (mirrors ProcessingPipeline.svelte EventSource cleanup)
	$effect(() => {
		documentId; // reactive dependency
		question = '';
		isStreaming = false;
		waitingForFirstChunk = false;
		streamedAnswer = '';
		errorKey = '';
		errorCustomMessage = '';

		return () => {
			activeController?.abort();
			activeController = null;
		};
	});

	async function handleSubmit() {
		const trimmed = question.trim();
		if (!trimmed || isStreaming) return;

		activeController?.abort();
		activeController = new AbortController();
		const controller = activeController;
		const { signal } = controller;

		isStreaming = true;
		waitingForFirstChunk = true;
		streamedAnswer = '';
		errorKey = '';
		errorCustomMessage = '';

		let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;

		try {
			const response = await streamAiChat({ document_id: documentId, question: trimmed }, signal);

			if (!response.ok) {
				const err = await response.json().catch(() => ({ status: response.status }));
				const detail = (err as { detail?: string }).detail;
				if (typeof detail === 'string' && detail.trim().length > 0) {
					errorCustomMessage = detail;
					errorKey = 'custom';
				} else {
					errorKey = 'generic';
				}
				return;
			}

			reader = response.body?.getReader() ?? undefined;
			if (!reader) {
				errorKey = 'streaming';
				return;
			}

			const decoder = new TextDecoder();
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				const chunk = decoder.decode(value, { stream: true });
				if (waitingForFirstChunk) {
					waitingForFirstChunk = false;
				}
				streamedAnswer += chunk;
			}
		} catch (err) {
			if ((err as { name?: string })?.name === 'AbortError') {
				reader?.cancel().catch(() => {}); // release the stream lock
				return; // Silently ignore — stream was canceled due to document navigation
			}
			errorKey = 'network';
		} finally {
			isStreaming = false;
			waitingForFirstChunk = false;
			if (activeController === controller) {
				activeController = null;
			}
		}
	}
</script>

<!--
  Render nothing when the interpretation query indicates the document has no AI interpretation.
  This gates the Q&A panel without duplicating the interpretation loading logic.
-->
{#if interpretationQuery.data || (interpretationQuery.isError && !is404(interpretationQuery.error))}
	{#if interpretationQuery.data}
		<section
			aria-label={copy.followUpAria}
			class="mt-4 border-l-4 border-l-[#3366FF] bg-card/50 rounded-md p-4"
		>
			<h3 class="text-base font-semibold mb-3 text-foreground">{copy.followUpHeader}</h3>

			<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-3">
				<label for="follow-up-question" class="sr-only">{copy.followUpHeader}</label>
				<Textarea
					id="follow-up-question"
					bind:value={question}
					placeholder={copy.followUpPlaceholder}
					disabled={isStreaming}
					aria-label={copy.followUpQuestionAria}
					class="resize-none"
				/>
				<Button
					type="submit"
					disabled={isStreaming || !question.trim()}
					class="w-auto"
				>
					{isStreaming ? copy.followUpGettingAnswer : copy.followUpAskButton}
				</Button>
			</form>

			<!-- Response area with aria-live for screen reader announcements -->
			<div aria-live="polite" class="mt-4">
				{#if waitingForFirstChunk}
					<div
						aria-busy="true"
						aria-label={copy.followUpLoadingAria}
						class="animate-pulse rounded-md h-16 bg-card border border-border"
					></div>
				{:else if streamedAnswer}
					<div class="text-[15px] leading-relaxed text-foreground whitespace-pre-wrap">
						{streamedAnswer}
					</div>
				{/if}
			</div>

			{#if errorMessage}
				<p role="alert" class="mt-3 text-[13px] text-destructive">{errorMessage}</p>
			{/if}
		</section>
	{/if}
{/if}
