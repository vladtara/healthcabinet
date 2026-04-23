<script lang="ts">
	import { tick } from 'svelte';
	import { streamAiChat, streamDashboardChat } from '$lib/api/ai';
	import type { DashboardFilter } from '$lib/stores/dashboard-filter.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';
	import { formatTime } from '$lib/i18n/format';
	import { marked } from 'marked';
	import { isNearBottom } from './ai-chat-scroll';

	const copy = $derived(t(localeStore.locale).aiChat);

	marked.setOptions({ breaks: true, gfm: true });

	interface ChatMessage {
		role: 'user' | 'ai';
		text: string;
		/** Raw send timestamp. Rendered via `formatTime(..., localeStore.locale)` in the template so the displayed time retranslates on locale flip. */
		timestamp: Date;
	}

	type ChatErrorKey = '' | 'generic' | 'network' | 'streaming' | 'custom';

	interface StickySnapshot {
		wasSticky: boolean;
		scrollTop: number | null;
	}

	type Props =
		| { mode: 'document'; documentId: string | null; hasContext?: boolean }
		| { mode: 'dashboard'; documentKind: DashboardFilter; hasContext?: boolean };

	const props: Props = $props();

	// Derive the identity + gating signals up front so the template stays
	// simple and reactive updates stay predictable.
	const identity = $derived(
		props.mode === 'document' ? props.documentId ?? '' : `dashboard:${props.documentKind}`
	);

	const canSubmit = $derived.by(() => {
		if (props.mode === 'document') return props.documentId != null;
		// Dashboard mode: treat an undefined `hasContext` as "not yet known" and
		// refuse to submit. This prevents a pre-hydration user click from
		// producing a 409 when the parent's dashboardHasContext signal is still
		// pending. Parents that genuinely have context must assert `true`.
		return props.hasContext === true;
	});

	const showNoContextHint = $derived(
		props.mode === 'dashboard' && props.hasContext === false
	);

	let minimized = $state(false);
	let maximized = $state(false);
	let question = $state('');
	let editorEl: HTMLDivElement | undefined = $state(undefined);
	let messages = $state<ChatMessage[]>([]);
	let isStreaming = $state(false);
	let errorKey = $state<ChatErrorKey>('');
	let errorCustomMessage = $state('');
	let messagesEl: HTMLDivElement | undefined = $state(undefined);

	const errorMessage = $derived.by(() => {
		switch (errorKey) {
			case 'generic':
				return copy.errorGeneric;
			case 'network':
				return copy.errorNetwork;
			case 'streaming':
				return copy.errorStreaming;
			case 'custom':
				return errorCustomMessage;
			default:
				return '';
		}
	});
	// Tracks whether the user is currently sticky-to-bottom. Auto-scroll only
	// fires when this was true immediately before a messages[] mutation, so
	// scrolling upward to read history is never yanked back by new chunks.
	let stickyBottom = $state(true);

	let activeController: AbortController | null = null;

	// Removed — messages now hold a raw `Date` timestamp and the template formats
	// it via `formatTime` at render time, so existing transcripts retranslate on
	// locale flip instead of being frozen at send-time.

	// Reset state when the bound identity flips (document switch OR filter change).
	$effect(() => {
		void identity;
		messages = [];
		clearEditor();
		isStreaming = false;
		errorKey = '';
		errorCustomMessage = '';
		stickyBottom = true;
		activeController?.abort();
		activeController = null;
	});

	function handleMessagesScroll() {
		stickyBottom = isNearBottom(messagesEl);
	}

	function captureStickySnapshot(): StickySnapshot {
		if (!messagesEl) return { wasSticky: stickyBottom, scrollTop: null };
		return { wasSticky: isNearBottom(messagesEl), scrollTop: messagesEl.scrollTop };
	}

	async function applyStickyScroll(snapshot: StickySnapshot) {
		// tick() waits until pending $state updates (the messages[] mutation
		// that triggered this call) are flushed to the DOM, so scrollHeight is
		// already the post-append value when we read it.
		// https://svelte.dev/docs/svelte/svelte#tick
		await tick();
		if (!snapshot.wasSticky || !messagesEl) return;
		const userMovedSinceCapture =
			snapshot.scrollTop !== null && Math.abs(messagesEl.scrollTop - snapshot.scrollTop) > 1;
		if (userMovedSinceCapture) {
			stickyBottom = isNearBottom(messagesEl);
			return;
		}
		messagesEl.scrollTop = messagesEl.scrollHeight;
		stickyBottom = true;
	}

	function getEditorText(): string {
		if (!editorEl) return question.trim();
		return (editorEl.innerText || '').trim();
	}

	function clearEditor() {
		question = '';
		if (editorEl) {
			editorEl.innerHTML = '';
			editorEl.textContent = '';
			editorEl.innerText = '';
		}
	}

	function execFormat(cmd: string, value?: string) {
		document.execCommand(cmd, false, value);
		editorEl?.focus();
	}

	async function openChatStream(trimmed: string, signal: AbortSignal): Promise<Response> {
		if (props.mode === 'document') {
			// Narrowed: documentId must be non-null (canSubmit guard).
			return streamAiChat(
				{ document_id: props.documentId as string, question: trimmed },
				signal
			);
		}
		return streamDashboardChat({ document_kind: props.documentKind, question: trimmed }, signal);
	}

	async function handleSubmit() {
		const trimmed = getEditorText();
		if (!trimmed || isStreaming || !canSubmit) return;

		activeController?.abort();
		activeController = new AbortController();
		const { signal } = activeController;

		const userSticky = captureStickySnapshot();
		messages = [...messages, { role: 'user', text: trimmed, timestamp: new Date() }];
		clearEditor();
		isStreaming = true;
		errorKey = '';
		errorCustomMessage = '';
		void applyStickyScroll(userSticky);

		let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
		let aiText = '';

		try {
			const response = await openChatStream(trimmed, signal);

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

			const placeholderSticky = captureStickySnapshot();
			messages = [...messages, { role: 'ai', text: '', timestamp: new Date() }];
			void applyStickyScroll(placeholderSticky);
			const decoder = new TextDecoder();

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				aiText += decoder.decode(value, { stream: true });
				const chunkSticky = captureStickySnapshot();
				messages = [
					...messages.slice(0, -1),
					{
						role: 'ai',
						text: aiText,
						timestamp: messages[messages.length - 1].timestamp
					}
				];
				void applyStickyScroll(chunkSticky);
			}
		} catch (err) {
			if ((err as { name?: string })?.name === 'AbortError') {
				reader?.cancel().catch(() => {});
				return;
			}
			errorKey = 'network';
		} finally {
			isStreaming = false;
			if (activeController?.signal === signal) {
				activeController = null;
			}
		}
	}
</script>

<div
	class="hc-ai-chat {minimized ? 'hc-ai-chat-minimized' : ''} {maximized
		? 'hc-ai-chat-maximized'
		: ''}"
>
	<div class="hc-ai-chat-titlebar">
		<span class="hc-ai-chat-titlebar-icon" aria-hidden="true">🩺</span>
		<span class="hc-ai-chat-titlebar-title">{copy.title}</span>
		<div class="hc-ai-chat-titlebar-btns">
			<button
				class="hc-ai-chat-tb-btn"
				aria-label={minimized ? copy.restore : copy.minimize}
				onclick={() => {
					minimized = !minimized;
					maximized = false;
				}}>_</button
			>
			<button
				class="hc-ai-chat-tb-btn"
				aria-expanded={maximized}
				aria-label={maximized ? copy.restore : copy.maximize}
				onclick={() => {
					maximized = !maximized;
					minimized = false;
				}}>□</button
			>
		</div>
	</div>

	<div class="hc-ai-chat-body">
		<div
			class="hc-ai-chat-messages"
			role="log"
			aria-live="polite"
			aria-label={copy.messagesLabel}
			bind:this={messagesEl}
			onscroll={handleMessagesScroll}
		>
			<div class="hc-ai-chat-msg-system">
				{copy.systemGreeting}
			</div>
			{#each messages as msg}
				<div
					class="hc-ai-chat-msg {msg.role === 'user'
						? 'hc-ai-chat-msg-user'
						: 'hc-ai-chat-msg-ai'}"
				>
					<div class="hc-ai-chat-msg-header">
						<span class="hc-ai-chat-msg-avatar">{msg.role === 'user' ? '👤' : '🩺'}</span>
						{msg.role === 'user' ? copy.senderUser : copy.senderAi}
						<span class="hc-ai-chat-msg-time">{formatTime(msg.timestamp, localeStore.locale)}</span>
					</div>
					<div class="hc-ai-chat-msg-text">
						{#if msg.role === 'ai'}
							{@html marked(msg.text)}
						{:else}
							{msg.text}
						{/if}
						{#if msg.role === 'ai' && msg.text === '' && isStreaming}
							<span class="animate-pulse">…</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>

		<div class="hc-ai-chat-inputbar">
			<div class="hc-ai-chat-toolbar">
				<button type="button" title={copy.toolbarBold} onclick={() => execFormat('bold')}><b>B</b></button>
				<button type="button" title={copy.toolbarItalic} onclick={() => execFormat('italic')}><i>I</i></button>
				<button type="button" title={copy.toolbarUnderline} onclick={() => execFormat('underline')}
					><u>U</u></button
				>
			</div>
			<div class="hc-ai-chat-input">
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="hc-ai-chat-editor"
					contenteditable="true"
					role="textbox"
					aria-label={copy.editorLabel}
					aria-multiline="true"
					tabindex="0"
					data-placeholder={copy.editorPlaceholder}
					bind:this={editorEl}
					oninput={() => {
						question = editorEl?.innerText?.trim() ?? '';
					}}
					onkeydown={(e) => {
						if (e.key === 'Enter' && !e.shiftKey) {
							e.preventDefault();
							handleSubmit();
						}
					}}
				></div>
				<button
					type="button"
					class="hc-ai-chat-sendbtn"
					disabled={isStreaming || !question.trim() || !canSubmit}
					onclick={handleSubmit}
				>
					{isStreaming ? copy.sendingIndicator : copy.send}
				</button>
			</div>
			{#if showNoContextHint}
				<div class="hc-ai-chat-hint" data-testid="dashboard-chat-no-context-hint">
					{copy.hintNoContext}
				</div>
			{:else}
				<div class="hc-ai-chat-hint">
					{copy.hintTip}
				</div>
			{/if}
		</div>

		{#if errorMessage}
			<p
				role="alert"
				style="font-size: 11px; color: var(--color-status-action); padding: 3px 8px;"
			>
				{errorMessage}
			</p>
		{/if}
	</div>

	<div class="hc-ai-chat-disclaimer">{copy.disclaimer}</div>
</div>
