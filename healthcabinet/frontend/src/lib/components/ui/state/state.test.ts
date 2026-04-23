import { describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import EmptyState from './empty-state.svelte';
import LoadingState from './loading-state.svelte';
import ErrorState from './error-state.svelte';
import SuccessState from './success-state.svelte';
import WarningState from './warning-state.svelte';

describe('EmptyState', () => {
	test('renders with title', () => {
		const { container } = renderComponent(EmptyState, { title: 'No documents yet' });
		expect(container.textContent).toContain('No documents yet');
	});

	test('renders description', () => {
		const { container } = renderComponent(EmptyState, {
			title: 'Empty',
			description: 'Upload your first document'
		});
		expect(container.textContent).toContain('Upload your first document');
	});

	test('renders icon', () => {
		const { container } = renderComponent(EmptyState, {
			title: 'Empty',
			icon: '📄'
		});
		expect(container.textContent).toContain('📄');
	});

	test('renders action button and fires onclick', () => {
		const onclick = vi.fn();
		const { container } = renderComponent(EmptyState, {
			title: 'Empty',
			action: { label: 'Import', onclick }
		});
		const button = container.querySelector('button');
		expect(button).toBeInTheDocument();
		expect(button?.textContent).toContain('Import');
		button?.click();
		expect(onclick).toHaveBeenCalledOnce();
	});

	test('renders children snippet', () => {
		const { container } = renderComponent(EmptyState, {
			children: textSnippet('Custom content')
		});
		expect(container.textContent).toContain('Custom content');
	});

	test('applies hc-state and hc-state-empty classes', () => {
		const { container } = renderComponent(EmptyState, { title: 'Test' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('hc-state')).toBe(true);
		expect(el?.classList.contains('hc-state-empty')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(EmptyState, { title: 'Test', class: 'my-class' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('my-class')).toBe(true);
	});
});

describe('LoadingState', () => {
	test('renders 3 skeleton lines by default', () => {
		const { container } = renderComponent(LoadingState);
		const lines = container.querySelectorAll('.hc-skeleton-line');
		expect(lines.length).toBe(3);
	});

	test('respects lines prop', () => {
		const { container } = renderComponent(LoadingState, { lines: 5 });
		const lines = container.querySelectorAll('.hc-skeleton-line');
		expect(lines.length).toBe(5);
	});

	test('renders message with aria-live', () => {
		const { container } = renderComponent(LoadingState, { message: 'Loading biomarkers...' });
		expect(container.textContent).toContain('Loading biomarkers...');
		const liveRegion = container.querySelector('[aria-live="polite"]');
		expect(liveRegion).toBeInTheDocument();
		expect(liveRegion?.textContent).toContain('Loading biomarkers...');
	});

	test('has aria-busy attribute', () => {
		const { container } = renderComponent(LoadingState);
		const el = container.firstElementChild;
		expect(el?.getAttribute('aria-busy')).toBe('true');
	});

	test('applies hc-state and hc-state-loading classes', () => {
		const { container } = renderComponent(LoadingState);
		const el = container.firstElementChild;
		expect(el?.classList.contains('hc-state')).toBe(true);
		expect(el?.classList.contains('hc-state-loading')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(LoadingState, { class: 'mt-4' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('mt-4')).toBe(true);
	});
});

describe('ErrorState', () => {
	test('renders title', () => {
		const { container } = renderComponent(ErrorState, { title: 'Failed to load documents' });
		expect(container.textContent).toContain('Failed to load documents');
	});

	test('renders description', () => {
		const { container } = renderComponent(ErrorState, {
			title: 'Error',
			description: 'Please try again later'
		});
		expect(container.textContent).toContain('Please try again later');
	});

	test('renders default icon', () => {
		const { container } = renderComponent(ErrorState, { title: 'Error' });
		expect(container.textContent).toContain('!');
	});

	test('renders action button and fires onclick', () => {
		const onclick = vi.fn();
		const { container } = renderComponent(ErrorState, {
			title: 'Error',
			action: { label: 'Retry', onclick }
		});
		const button = container.querySelector('button');
		expect(button).toBeInTheDocument();
		expect(button?.textContent).toContain('Retry');
		button?.click();
		expect(onclick).toHaveBeenCalledOnce();
	});

	test('has role="alert"', () => {
		const { container } = renderComponent(ErrorState, { title: 'Error' });
		const el = container.firstElementChild;
		expect(el?.getAttribute('role')).toBe('alert');
	});

	test('applies hc-state-error class', () => {
		const { container } = renderComponent(ErrorState, { title: 'Error' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('hc-state')).toBe(true);
		expect(el?.classList.contains('hc-state-error')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(ErrorState, { title: 'Error', class: 'mt-4' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('mt-4')).toBe(true);
	});
});

describe('SuccessState', () => {
	test('renders title', () => {
		const { container } = renderComponent(SuccessState, { title: 'Profile updated' });
		expect(container.textContent).toContain('Profile updated');
	});

	test('renders description', () => {
		const { container } = renderComponent(SuccessState, {
			title: 'Success',
			description: 'Your changes have been saved'
		});
		expect(container.textContent).toContain('Your changes have been saved');
	});

	test('renders default icon', () => {
		const { container } = renderComponent(SuccessState, { title: 'Success' });
		expect(container.textContent).toContain('✓');
	});

	test('has role="status"', () => {
		const { container } = renderComponent(SuccessState, { title: 'Success' });
		const el = container.firstElementChild;
		expect(el?.getAttribute('role')).toBe('status');
	});

	test('applies hc-state-success class', () => {
		const { container } = renderComponent(SuccessState, { title: 'Success' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('hc-state')).toBe(true);
		expect(el?.classList.contains('hc-state-success')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(SuccessState, { title: 'Success', class: 'mb-2' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('mb-2')).toBe(true);
	});
});

describe('WarningState', () => {
	test('renders title', () => {
		const { container } = renderComponent(WarningState, { title: 'Partial extraction' });
		expect(container.textContent).toContain('Partial extraction');
	});

	test('renders description', () => {
		const { container } = renderComponent(WarningState, {
			title: 'Warning',
			description: 'Some values could not be extracted'
		});
		expect(container.textContent).toContain('Some values could not be extracted');
	});

	test('renders default icon', () => {
		const { container } = renderComponent(WarningState, { title: 'Warning' });
		expect(container.textContent).toContain('⚠');
	});

	test('renders action button and fires onclick', () => {
		const onclick = vi.fn();
		const { container } = renderComponent(WarningState, {
			title: 'Warning',
			action: { label: 'Re-upload', onclick }
		});
		const button = container.querySelector('button');
		expect(button).toBeInTheDocument();
		expect(button?.textContent).toContain('Re-upload');
		button?.click();
		expect(onclick).toHaveBeenCalledOnce();
	});

	test('has role="status"', () => {
		const { container } = renderComponent(WarningState, { title: 'Warning' });
		const el = container.firstElementChild;
		expect(el?.getAttribute('role')).toBe('status');
	});

	test('applies hc-state-warning class', () => {
		const { container } = renderComponent(WarningState, { title: 'Warning' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('hc-state')).toBe(true);
		expect(el?.classList.contains('hc-state-warning')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(WarningState, { title: 'Warning', class: 'p-4' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('p-4')).toBe(true);
	});
});
