/**
 * Global feedback store using Svelte 5 runes.
 * Manages transient toast notifications with auto-dismiss.
 */

export type ToastType = 'success' | 'error' | 'warning';

export interface Toast {
	id: string;
	type: ToastType;
	message: string;
}

let nextId = 0;
const timers = new Map<string, ReturnType<typeof setTimeout>>();

class FeedbackStore {
	toasts = $state<Toast[]>([]);

	addToast(type: ToastType, message: string, autoDismissMs = 3000): string {
		const id = `toast-${++nextId}`;
		this.toasts.push({ id, type, message });

		if (autoDismissMs > 0) {
			const timer = setTimeout(() => this.dismissToast(id), autoDismissMs);
			timers.set(id, timer);
		}

		return id;
	}

	dismissToast(id: string): void {
		const timer = timers.get(id);
		if (timer) {
			clearTimeout(timer);
			timers.delete(id);
		}
		this.toasts = this.toasts.filter((t) => t.id !== id);
	}

	clearAll(): void {
		for (const timer of timers.values()) {
			clearTimeout(timer);
		}
		timers.clear();
		this.toasts = [];
	}
}

export const feedbackStore = new FeedbackStore();

export function showSuccess(message: string): string {
	return feedbackStore.addToast('success', message);
}

export function showError(message: string): string {
	return feedbackStore.addToast('error', message, 0); // Errors persist until dismissed
}

export function showWarning(message: string): string {
	return feedbackStore.addToast('warning', message);
}

export function dismissToast(id: string): void {
	feedbackStore.dismissToast(id);
}

export function clearAll(): void {
	feedbackStore.clearAll();
}
