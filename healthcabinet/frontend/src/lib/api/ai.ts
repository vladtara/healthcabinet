import { apiFetch, apiStream } from './client.svelte';
import type { DashboardFilter } from '$lib/stores/dashboard-filter.svelte';
import type { Locale } from '$lib/stores/locale.svelte';

export type ValueStatus = 'normal' | 'high' | 'low' | 'unknown';

export interface ValueReasoning {
	name: string;
	value: number;
	unit: string | null;
	ref_low: number | null;
	ref_high: number | null;
	status: ValueStatus;
}

export interface ReasoningContext {
	values_referenced: ValueReasoning[];
	uncertainty_flags: string[];
	prior_documents_referenced: string[];
}

export interface AiInterpretationResponse {
	document_id: string;
	interpretation: string;
	model_version: string | null;
	generated_at: string;
	reasoning: ReasoningContext | null;
}

export interface PatternObservation {
	description: string;
	document_dates: string[];
	recommendation: string;
}

export interface AiPatternsResponse {
	patterns: PatternObservation[];
}

export async function getDocumentInterpretation(
	documentId: string
): Promise<AiInterpretationResponse> {
	return apiFetch<AiInterpretationResponse>(`/api/v1/ai/documents/${documentId}/interpretation`);
}

export interface AiChatRequest {
	document_id: string;
	question: string;
	locale?: Locale;
}

export async function streamAiChat(
	payload: AiChatRequest,
	signal?: AbortSignal
): Promise<Response> {
	return apiStream('/api/v1/ai/chat', {
		method: 'POST',
		body: JSON.stringify(payload),
		signal
	});
}

export async function getAiPatterns(locale: Locale = 'en'): Promise<AiPatternsResponse> {
	return apiFetch<AiPatternsResponse>(`/api/v1/ai/patterns?locale=${encodeURIComponent(locale)}`);
}

// ──────────────────────────────────────────────────────────────────────────
// Story 15.3 — dashboard-scoped aggregate AI
// ──────────────────────────────────────────────────────────────────────────

export interface DashboardInterpretationResponse {
	document_id: null;
	document_kind: DashboardFilter;
	source_document_ids: string[];
	interpretation: string;
	model_version: string | null;
	generated_at: string;
	reasoning: ReasoningContext | null;
}

export interface DashboardChatRequest {
	document_kind: DashboardFilter;
	question: string;
	locale?: Locale;
}

export async function getDashboardInterpretation(
	documentKind: DashboardFilter,
	locale: Locale = 'en'
): Promise<DashboardInterpretationResponse> {
	return apiFetch<DashboardInterpretationResponse>(
		`/api/v1/ai/dashboard/interpretation?document_kind=${encodeURIComponent(documentKind)}&locale=${encodeURIComponent(locale)}`
	);
}

export async function regenerateDashboardInterpretation(
	documentKind: DashboardFilter,
	locale: Locale = 'en'
): Promise<DashboardInterpretationResponse> {
	return apiFetch<DashboardInterpretationResponse>(
		`/api/v1/ai/dashboard/interpretation/regenerate?document_kind=${encodeURIComponent(documentKind)}&locale=${encodeURIComponent(locale)}`,
		{ method: 'POST' }
	);
}

export async function streamDashboardChat(
	payload: DashboardChatRequest,
	signal?: AbortSignal
): Promise<Response> {
	return apiStream('/api/v1/ai/dashboard/chat', {
		method: 'POST',
		body: JSON.stringify(payload),
		signal
	});
}
