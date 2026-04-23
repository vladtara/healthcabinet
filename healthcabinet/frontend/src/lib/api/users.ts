import { apiFetch, apiStream, type ApiError } from '$lib/api/client.svelte';
import type { ConsentLog, UserProfile } from '$lib/types/api';

export type ProfileUpdateData = {
	age?: number | null;
	sex?: 'male' | 'female' | 'other' | 'prefer_not_to_say' | null;
	height_cm?: number | null;
	weight_kg?: number | null;
	known_conditions?: string[];
	medications?: string[];
	family_history?: string | null;
};

export async function getProfile(): Promise<UserProfile | null> {
	return apiFetch<UserProfile>('/api/v1/users/me/profile').catch((err) => {
		// Only suppress 404 (profile not yet created). All other errors
		// (401, 500, network) should propagate so apiFetch's token-refresh
		// and redirect logic can handle them.
		if (
			err &&
			typeof err === 'object' &&
			'status' in err &&
			(err as { status: number }).status === 404
		) {
			return null;
		}
		throw err;
	});
}

export async function updateProfile(data: ProfileUpdateData): Promise<UserProfile> {
	return apiFetch<UserProfile>('/api/v1/users/me/profile', {
		method: 'PUT',
		body: JSON.stringify(data)
	});
}

export async function saveOnboardingStep(step: number): Promise<void> {
	return apiFetch<void>('/api/v1/users/me/onboarding-step', {
		method: 'PATCH',
		body: JSON.stringify({ step })
	});
}

export async function getConsentHistory(): Promise<ConsentLog[]> {
	const res = await apiFetch<{ items: ConsentLog[] }>('/api/v1/users/me/consent-history');
	return res.items;
}

export async function deleteMyAccount(): Promise<void> {
	await apiFetch<void>('/api/v1/users/me', { method: 'DELETE' });
}

async function parseApiError(response: Response): Promise<ApiError> {
	const fallback: ApiError = {
		type: 'about:blank',
		title: response.statusText || 'Request Failed',
		status: response.status
	};

	const contentType = response.headers.get('content-type') ?? '';
	if (contentType.includes('json')) {
		return response.json().catch(() => fallback);
	}

	const detail = await response.text().catch(() => '');
	return detail ? { ...fallback, detail } : fallback;
}

export async function exportMyData(): Promise<void> {
	const response = await apiStream('/api/v1/users/me/export', {
		method: 'POST',
		credentials: 'include'
	});
	if (!response.ok) {
		throw await parseApiError(response);
	}
	const blob = await response.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download =
		response.headers.get('content-disposition')?.match(/filename="(.+)"/)?.[1] ??
		'healthcabinet-export.zip';
	a.style.display = 'none';
	document.body.appendChild(a);
	a.click();
	setTimeout(() => {
		URL.revokeObjectURL(url);
		a.remove();
	}, 0);
}
