/**
 * TypeScript interfaces mirroring API snake_case directly.
 * No transformation layer — match API response shapes exactly.
 */

export interface User {
	id: string;
	email: string;
	role: 'user' | 'admin';
	tier: 'free' | 'paid';
	created_at: string;
	updated_at: string;
}

export interface ConsentLog {
	id: string;
	consent_type: string;
	privacy_policy_version: string;
	consented_at: string;
}

export interface TokenResponse {
	access_token: string;
	token_type: 'bearer';
}

export interface HealthResponse {
	status: 'ok';
}

export type DocumentKind = 'analysis' | 'document' | 'unknown';

export interface Document {
	id: string;
	user_id: string;
	filename: string;
	file_size_bytes: number;
	file_type: string;
	status: 'pending' | 'processing' | 'completed' | 'partial' | 'failed';
	arq_job_id: string | null;
	keep_partial: boolean | null;
	// Document intelligence metadata (Story 15.2)
	document_kind: DocumentKind;
	needs_date_confirmation: boolean;
	partial_measured_at_text: string | null;
	created_at: string;
	updated_at: string;
}

export interface UploadUrlResponse {
	upload_url: string;
	document_id: string;
}

export interface HealthValueItem {
	id: string;
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
}

export interface FlagValueResponse {
	id: string;
	is_flagged: boolean;
	flagged_at: string | null;
}

export interface DocumentDetail {
	id: string;
	filename: string;
	file_size_bytes: number;
	file_type: string;
	status: 'pending' | 'processing' | 'completed' | 'partial' | 'failed';
	arq_job_id: string | null;
	keep_partial: boolean | null;
	// Document intelligence metadata (Story 15.2)
	document_kind: DocumentKind;
	needs_date_confirmation: boolean;
	partial_measured_at_text: string | null;
	created_at: string;
	updated_at: string;
	health_values: HealthValueItem[];
}

export interface KeepPartialResponse {
	kept: boolean;
}

export interface DeleteResponse {
	deleted: boolean;
}

export interface AdminMetrics {
	total_signups: number;
	total_uploads: number;
	upload_success_rate: number | null;
	documents_error_or_partial: number;
	ai_interpretation_completion_rate: number | null;
}

export interface ErrorQueueItem {
	document_id: string;
	user_id: string;
	filename: string;
	upload_date: string;
	status: string;
	value_count: number;
	low_confidence_count: number;
	flagged_count: number;
	failed: boolean;
}

export interface ErrorQueueResponse {
	items: ErrorQueueItem[];
	total: number;
}

export interface DocumentHealthValueDetail {
	id: string;
	biomarker_name: string;
	canonical_biomarker_name: string;
	value: number;
	unit: string | null;
	reference_range_low: number | null;
	reference_range_high: number | null;
	confidence: number;
	needs_review: boolean;
	is_flagged: boolean;
	flagged_at: string | null;
}

export interface DocumentQueueDetail {
	document_id: string;
	user_id: string;
	filename: string;
	upload_date: string;
	status: string;
	values: DocumentHealthValueDetail[];
}

export interface CorrectionRequest {
	new_value: number;
	reason: string;
}

export interface CorrectionResponse {
	audit_log_id: string;
	health_value_id: string;
	value_name: string;
	original_value: number;
	new_value: number;
	corrected_at: string;
}

// --- Story 5.3: Admin user management & flag review ---

export interface AdminUserListItem {
	user_id: string;
	email: string;
	registration_date: string;
	upload_count: number;
	account_status: 'active' | 'suspended';
}

export interface AdminUserListResponse {
	items: AdminUserListItem[];
	total: number;
}

export interface AdminUserDetail {
	user_id: string;
	email: string;
	registration_date: string;
	last_login: string | null;
	upload_count: number;
	account_status: 'active' | 'suspended';
}

export interface AdminUserStatusUpdate {
	account_status: 'active' | 'suspended';
}

export interface FlaggedReportItem {
	health_value_id: string;
	user_id: string;
	document_id: string;
	value_name: string;
	flagged_value: number;
	flagged_at: string;
}

export interface FlaggedReportListResponse {
	items: FlaggedReportItem[];
	total: number;
}

export interface FlagReviewedResponse {
	health_value_id: string;
	reviewed_at: string;
}

export interface UserProfile {
	id: string;
	user_id: string;
	age: number | null;
	sex: 'male' | 'female' | 'other' | 'prefer_not_to_say' | null;
	height_cm: number | null;
	weight_kg: number | null;
	known_conditions: string[];
	medications: string[];
	family_history: string | null;
	onboarding_step: number;
	created_at: string;
	updated_at: string;
}
