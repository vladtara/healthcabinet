import { apiFetch } from '$lib/api/client.svelte';
import type {
	AdminMetrics,
	AdminUserDetail,
	AdminUserListResponse,
	CorrectionRequest,
	CorrectionResponse,
	DocumentQueueDetail,
	ErrorQueueResponse,
	FlaggedReportListResponse,
	FlagReviewedResponse
} from '$lib/types/api';

/**
 * Fetch aggregate platform metrics. Requires admin role.
 */
export async function getAdminMetrics(): Promise<AdminMetrics> {
	return apiFetch<AdminMetrics>('/api/v1/admin/metrics');
}

/**
 * Fetch documents with extraction problems (failed/partial status, low confidence, or flagged values).
 * Requires admin role.
 */
export async function getErrorQueue(): Promise<ErrorQueueResponse> {
	return apiFetch<ErrorQueueResponse>('/api/v1/admin/queue');
}

/**
 * Fetch a document with all its health values for admin correction.
 * Requires admin role.
 */
export async function getDocumentForCorrection(documentId: string): Promise<DocumentQueueDetail> {
	return apiFetch<DocumentQueueDetail>(`/api/v1/admin/queue/${documentId}`);
}

/**
 * Submit a corrected value for a health data point.
 * Requires admin role.
 */
export async function submitCorrection(
	documentId: string,
	healthValueId: string,
	data: CorrectionRequest
): Promise<CorrectionResponse> {
	return apiFetch<CorrectionResponse>(
		`/api/v1/admin/queue/${documentId}/values/${healthValueId}/correct`,
		{
			method: 'POST',
			body: JSON.stringify(data),
			headers: { 'Content-Type': 'application/json' }
		}
	);
}

// --- Story 5.3: Admin user management & flag review ---

/**
 * Fetch searchable list of user accounts. No health data exposed.
 * Requires admin role.
 */
export async function getAdminUsers(query?: string): Promise<AdminUserListResponse> {
	const params = query ? `?q=${encodeURIComponent(query)}` : '';
	return apiFetch<AdminUserListResponse>(`/api/v1/admin/users${params}`);
}

/**
 * Fetch account metadata for a single user.
 * Requires admin role.
 */
export async function getAdminUserDetail(userId: string): Promise<AdminUserDetail> {
	return apiFetch<AdminUserDetail>(`/api/v1/admin/users/${userId}`);
}

/**
 * Suspend or reactivate a user account.
 * Requires admin role.
 */
export async function updateAdminUserStatus(
	userId: string,
	accountStatus: 'active' | 'suspended'
): Promise<AdminUserDetail> {
	return apiFetch<AdminUserDetail>(`/api/v1/admin/users/${userId}/status`, {
		method: 'PATCH',
		body: JSON.stringify({ account_status: accountStatus }),
		headers: { 'Content-Type': 'application/json' }
	});
}

/**
 * Fetch unreviewed flagged value reports.
 * Requires admin role.
 */
export async function getFlaggedReports(): Promise<FlaggedReportListResponse> {
	return apiFetch<FlaggedReportListResponse>('/api/v1/admin/flags');
}

/**
 * Mark a flagged value as reviewed.
 * Requires admin role.
 */
export async function markFlagReviewed(healthValueId: string): Promise<FlagReviewedResponse> {
	return apiFetch<FlagReviewedResponse>(`/api/v1/admin/flags/${healthValueId}/review`, {
		method: 'POST'
	});
}
