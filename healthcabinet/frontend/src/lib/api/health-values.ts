import { apiFetch } from '$lib/api/client.svelte';
import type { FlagValueResponse } from '$lib/types/api';
import type { DashboardFilter } from '$lib/stores/dashboard-filter.svelte';

export interface HealthValue {
	id: string;
	user_id: string;
	document_id: string;
	biomarker_name: string;
	canonical_biomarker_name: string;
	value: number;
	unit: string | null;
	reference_range_low: number | null;
	reference_range_high: number | null;
	measured_at: string | null;
	confidence: number;
	needs_review: boolean;
	is_flagged: boolean;
	flagged_at: string | null;
	created_at: string;
	status: 'optimal' | 'borderline' | 'concerning' | 'action_needed' | 'unknown';
}

/**
 * Fetch extracted health values for the authenticated user.
 *
 * Story 15.3 — optional `documentKind` scopes the result via the backend
 * JOIN to documents. When omitted the pre-15.3 contract is preserved and
 * values owned by 'unknown' documents are included. When set, 'unknown' is
 * always excluded (even under 'all').
 */
export async function getHealthValues(documentKind?: DashboardFilter): Promise<HealthValue[]> {
	const path = documentKind
		? `/api/v1/health-values?document_kind=${encodeURIComponent(documentKind)}`
		: '/api/v1/health-values';
	return apiFetch<HealthValue[]>(path);
}

/**
 * Flag an extracted health value as potentially incorrect.
 * Idempotent — repeated calls preserve the original flagged_at timestamp.
 */
export async function flagHealthValue(healthValueId: string): Promise<FlagValueResponse> {
	return apiFetch<FlagValueResponse>(`/api/v1/health-values/${healthValueId}/flag`, {
		method: 'PUT'
	});
}

export interface RecommendationItem {
	test_name: string;
	rationale: string;
	frequency: string;
	category: 'general' | 'condition_specific';
}

export interface BaselineSummaryResponse {
	recommendations: RecommendationItem[];
	has_uploads: boolean;
}

/**
 * Fetch profile-based baseline recommendations for the empty-state dashboard.
 * Derived from profile data only — no health_values are queried.
 */
export async function getDashboardBaseline(): Promise<BaselineSummaryResponse> {
	return apiFetch<BaselineSummaryResponse>('/api/v1/health-values/baseline');
}

export interface HealthValueTimelineResponse {
	biomarker_name: string;
	canonical_biomarker_name: string;
	skipped_corrupt_records: number;
	values: HealthValue[]; // sorted oldest→newest
}

/**
 * Fetch all historical values for a single biomarker for the authenticated user.
 * Values are ordered oldest-first by measured_at.
 */
export async function getHealthValueTimeline(
	canonicalBiomarkerName: string
): Promise<HealthValueTimelineResponse> {
	return apiFetch<HealthValueTimelineResponse>(
		`/api/v1/health-values/timeline/${encodeURIComponent(canonicalBiomarkerName)}`
	);
}
