<script lang="ts">
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import {
		clearDocumentChat,
		getDocumentInterpretation,
		listDocumentChatMessages,
		streamAiChat,
		type ChatMessageResponse
	} from '$lib/api/ai';
	import type { ApiError } from '$lib/api/client.svelte';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Button } from '$lib/components/ui/button';
	import { ConfirmDialog } from '$lib/components/ui/confirm-dialog';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).aiChat);

	type FollowUpErrorKey = '' | 'generic' | 'streaming' | 'network' | 'custom';

	interface Props {
		documentId: string;
	}

	let { documentId }: Props = $props();
	const queryClient = useQueryClient();

	let question = $state('');
	let isStreaming = $state(false);
	let waitingForFirstChunk = $state(false);
	let streamedAnswer = $state('');
	let errorKey = $state<FollowUpErrorKey>('');
	let errorCustomMessage = $state('');
	let priorMessages = $state<ChatMessageResponse[]>([]);
	let currentUserQuestion = $state('');

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

	// Persistent chat history for this document's thread. Hydrated on mount
	// and after each successful stream. Survives page reloads.
	const historyQuery = createQuery(() => ({
		queryKey: ['ai_chat_messages', 'document', documentId] as const,
		queryFn: () => listDocumentChatMessages(documentId, { limit: 50 }),
		staleTime: 60_000,
		retry: false
	}));

	$effect(() => {
		priorMessages = historyQuery.data?.messages ?? [];
	});

	function is404(error: unknown): boolean {
		return (error as ApiError)?.status === 404;
	}

	// Reset local state whenever the user navigates to a different document
	// and cancel any in-flight stream (mirrors ProcessingPipeline.svelte EventSource cleanup)
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		documentId; // reactive dependency
		question = '';
		isStreaming = false;
		waitingForFirstChunk = false;
		streamedAnswer = '';
		currentUserQuestion = '';
		errorKey = '';
		errorCustomMessage = '';

		return () => {
			activeController?.abort();
			activeController = null;
		};
	});

	let clearDialogOpen = $state(false);
	let clearDialogLoading = $state(false);

	function openClearDialog(): void {
		if (isStreaming || clearDialogLoading) return;
		clearDialogOpen = true;
	}

	async function performClearHistory(): Promise<void> {
		clearDialogLoading = true;
		try {
			await clearDocumentChat(documentId);
			priorMessages = [];
			streamedAnswer = '';
			currentUserQuestion = '';
			await queryClient.invalidateQueries({
				queryKey: ['ai_chat_messages', 'document', documentId]
			});
			clearDialogOpen = false;
		} catch {
			errorKey = 'generic';
			clearDialogOpen = false;
		} finally {
			clearDialogLoading = false;
		}
	}

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
		currentUserQuestion = trimmed;
		question = '';
		errorKey = '';
		errorCustomMessage = '';

		let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;

		try {
			const response = await streamAiChat(
				{ document_id: documentId, question: trimmed, locale: localeStore.locale },
				signal
			);

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

		// Stream completed cleanly — refresh the persisted history so the just-
		// finished turn joins `priorMessages` on the next tick and the live
		// `streamedAnswer` view can collapse into the history list.
		if (!errorKey) {
			try {
				await queryClient.invalidateQueries({
					queryKey: ['ai_chat_messages', 'document', documentId]
				});
				streamedAnswer = '';
				currentUserQuestion = '';
			} catch {
				// Non-fatal — the next mount will pick up the write.
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
			class="bg-card/50 mt-4 rounded-md border-l-4 border-l-[#3366FF] p-4"
		>
			<div class="mb-3 flex items-center justify-between">
				<h3 class="text-foreground text-base font-semibold">{copy.followUpHeader}</h3>
				{#if priorMessages.length > 0}
					<button
						type="button"
						class="text-muted-foreground hover:text-foreground text-[12px] underline"
						disabled={isStreaming || clearDialogLoading}
						onclick={openClearDialog}
						aria-label={copy.clearConversation ?? 'Clear conversation'}
					>
						{copy.clearConversation ?? 'Clear conversation'}
					</button>
				{/if}
			</div>

			<!-- Persisted history: prior Q&A turns fetched from the server. -->
			{#if priorMessages.length > 0}
				<div class="mb-3 space-y-2" aria-label="Previous conversation">
					{#each priorMessages as m}
						<div
							class="rounded-md border px-3 py-2 text-[14px] leading-relaxed whitespace-pre-wrap"
						>
							<div class="text-muted-foreground mb-1 text-[11px] font-semibold uppercase">
								{m.role === 'user' ? copy.senderUser : copy.senderAi}
							</div>
							<div class="text-foreground">{m.text}</div>
						</div>
					{/each}
				</div>
			{/if}

			<form
				onsubmit={(e) => {
					e.preventDefault();
					handleSubmit();
				}}
				class="space-y-3"
			>
				<label for="follow-up-question" class="sr-only">{copy.followUpHeader}</label>
				<Textarea
					id="follow-up-question"
					bind:value={question}
					placeholder={copy.followUpPlaceholder}
					disabled={isStreaming}
					aria-label={copy.followUpQuestionAria}
					class="resize-none"
				/>
				<Button type="submit" disabled={isStreaming || !question.trim()} class="w-auto">
					{isStreaming ? copy.followUpGettingAnswer : copy.followUpAskButton}
				</Button>
			</form>

			<!-- In-flight stream: shows the current user question + streaming answer
			     until the stream completes, then the turn joins the persisted
			     history list above via query invalidation. -->
			<div aria-live="polite" class="mt-4 space-y-2">
				{#if currentUserQuestion}
					<div
						class="border-muted rounded-md border px-3 py-2 text-[14px] leading-relaxed whitespace-pre-wrap"
					>
						<div class="text-muted-foreground mb-1 text-[11px] font-semibold uppercase">
							{copy.senderUser}
						</div>
						<div class="text-foreground">{currentUserQuestion}</div>
					</div>
				{/if}
				{#if waitingForFirstChunk}
					<div
						aria-busy="true"
						aria-label={copy.followUpLoadingAria}
						class="bg-card border-border h-16 animate-pulse rounded-md border"
					></div>
				{:else if streamedAnswer}
					<div
						class="bg-card border-border rounded-md border px-3 py-2 text-[15px] leading-relaxed whitespace-pre-wrap"
					>
						<div class="text-muted-foreground mb-1 text-[11px] font-semibold uppercase">
							{copy.senderAi}
						</div>
						<div class="text-foreground">{streamedAnswer}</div>
					</div>
				{/if}
			</div>

			{#if errorMessage}
				<p role="alert" class="text-destructive mt-3 text-[13px]">{errorMessage}</p>
			{/if}
		</section>
	{/if}
{/if}

<ConfirmDialog
	bind:open={clearDialogOpen}
	title={copy.clearConversation}
	confirmLabel={copy.clearConversation}
	confirmVariant="destructive"
	loading={clearDialogLoading}
	onConfirm={performClearHistory}
>
	<p>{copy.clearConfirm}</p>
</ConfirmDialog>
