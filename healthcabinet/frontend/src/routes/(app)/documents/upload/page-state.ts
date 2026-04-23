import type { Document } from '$lib/types/api';

export type UploadState = 'idle' | 'success' | 'done' | 'partial' | 'failed';
export type FailureReason = 'failed' | 'partial' | 'stream-error';

export interface UploadPageModel {
	uploadState: UploadState;
	documentId: string | null;
}

export function handleUploadSuccess(doc: Document): UploadPageModel {
	return {
		uploadState: 'success',
		documentId: doc.id
	};
}

export function handleProcessingComplete(
	queryClient: { invalidateQueries: (arg: { queryKey: string[] }) => unknown },
	model: UploadPageModel
): UploadPageModel {
	queryClient.invalidateQueries({ queryKey: ['documents'] });
	queryClient.invalidateQueries({ queryKey: ['health_values'] });
	// Story 15.3 — rebuild dashboard AI aggregate from the new persisted row.
	queryClient.invalidateQueries({ queryKey: ['ai_dashboard_interpretation'] });
	return {
		...model,
		uploadState: 'done'
	};
}

export function handleProcessingFailure(
	queryClient: { invalidateQueries: (arg: { queryKey: string[] }) => unknown },
	model: UploadPageModel,
	reason: FailureReason = 'failed'
): UploadPageModel {
	if (reason === 'partial') {
		queryClient.invalidateQueries({ queryKey: ['documents'] });
		queryClient.invalidateQueries({ queryKey: ['health_values'] });
		// Story 15.3 — partial still produces an AiMemory row when values extracted.
		queryClient.invalidateQueries({ queryKey: ['ai_dashboard_interpretation'] });
		return {
			...model,
			uploadState: 'partial'
		};
	}

	return {
		...model,
		uploadState: 'failed'
	};
}
