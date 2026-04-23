import { describe, expect, test, vi } from 'vitest';
import { fireEvent, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import ConfirmDialog from './confirm-dialog.svelte';

describe('ConfirmDialog', () => {
	test('renders dialog when open is true with role/aria-modal/aria-label', () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test Dialog',
			confirmLabel: 'Confirm',
			onConfirm: () => {}
		});

		const dialog = container.querySelector('[role="dialog"]');
		expect(dialog).toBeInTheDocument();
		expect(dialog?.getAttribute('aria-modal')).toBe('true');
		expect(dialog?.getAttribute('aria-label')).toBe('Test Dialog');
	});

	test('hidden when open is false', () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: false,
			title: 'Test',
			confirmLabel: 'Confirm',
			onConfirm: () => {}
		});
		expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
	});

	test('uses custom ariaLabel when provided', () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Short Title',
			ariaLabel: 'Long accessible description for screen readers',
			confirmLabel: 'Confirm',
			onConfirm: () => {}
		});
		const dialog = container.querySelector('[role="dialog"]');
		expect(dialog?.getAttribute('aria-label')).toBe(
			'Long accessible description for screen readers'
		);
	});

	test('renders title and body children', () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Delete Thing',
			confirmLabel: 'Delete',
			onConfirm: () => {},
			children: textSnippet('Are you sure you want to delete this?')
		});
		expect(container.querySelector('.hc-dialog-title')?.textContent).toContain('Delete Thing');
		expect(container.textContent).toContain('Are you sure you want to delete this?');
	});

	test('confirmVariant maps to btn-destructive by default', () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			onConfirm: () => {}
		});
		const confirmBtn = container.querySelector('.hc-dialog-actions .btn-destructive');
		expect(confirmBtn).toBeInTheDocument();
	});

	test('confirmVariant="primary" uses btn-primary', () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			confirmVariant: 'primary',
			onConfirm: () => {}
		});
		expect(container.querySelector('.hc-dialog-actions .btn-primary')).toBeInTheDocument();
		expect(container.querySelector('.hc-dialog-actions .btn-destructive')).not.toBeInTheDocument();
	});

	test('confirmVariant="standard" uses btn-standard for confirm', () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'OK',
			confirmVariant: 'standard',
			onConfirm: () => {}
		});
		// Cancel is always btn-standard; find the confirm by its label
		const buttons = container.querySelectorAll('.hc-dialog-actions button');
		expect(buttons.length).toBe(2);
		const confirmBtn = Array.from(buttons).find((b) => b.textContent?.trim() === 'OK');
		expect(confirmBtn?.classList.contains('btn-standard')).toBe(true);
	});

	test('confirm button disabled when canConfirm is false', () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			canConfirm: false,
			onConfirm: () => {}
		});
		const confirmBtn = container.querySelector('.btn-destructive') as HTMLButtonElement;
		expect(confirmBtn).toBeDisabled();
	});

	test('confirm button enabled when canConfirm is true', () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			canConfirm: true,
			onConfirm: () => {}
		});
		const confirmBtn = container.querySelector('.btn-destructive') as HTMLButtonElement;
		expect(confirmBtn).not.toBeDisabled();
	});

	test('loading state disables both buttons and swaps confirm label', () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Delete',
			loading: true,
			loadingLabel: 'Deleting...',
			onConfirm: () => {}
		});
		const buttons = container.querySelectorAll('.hc-dialog-actions button');
		buttons.forEach((btn) => expect(btn).toBeDisabled());
		const confirmBtn = container.querySelector('.btn-destructive');
		expect(confirmBtn?.textContent?.trim()).toBe('Deleting...');
	});

	test('calls onConfirm when confirm button clicked', async () => {
		const onConfirm = vi.fn();
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			onConfirm
		});
		const confirmBtn = container.querySelector('.btn-destructive') as HTMLButtonElement;
		await fireEvent.click(confirmBtn);
		expect(onConfirm).toHaveBeenCalledOnce();
	});

	test('disables the confirm button while onConfirm is in flight', async () => {
		let resolveConfirm: (() => void) | undefined;
		const onConfirm = vi.fn(
			() =>
				new Promise<void>((resolve) => {
					resolveConfirm = resolve;
				})
		);

		const { getByRole } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			onConfirm
		});

		const confirmBtn = getByRole('button', { name: 'Confirm' }) as HTMLButtonElement;

		await fireEvent.click(confirmBtn);

		await waitFor(() => {
			expect(confirmBtn).toBeDisabled();
		});

		await fireEvent.click(confirmBtn);
		expect(onConfirm).toHaveBeenCalledTimes(1);

		resolveConfirm?.();

		await waitFor(() => {
			expect(confirmBtn).not.toBeDisabled();
		});
	});

	test('Cancel button closes dialog via open binding', async () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			onConfirm: () => {}
		});
		const cancelBtn = container.querySelector('.btn-standard') as HTMLButtonElement;
		await fireEvent.click(cancelBtn);
		await tick();
		expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
	});

	test('backdrop click closes dialog', async () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			onConfirm: () => {}
		});
		const backdrop = container.querySelector('.hc-dialog-backdrop') as HTMLDivElement;
		await fireEvent.click(backdrop);
		await tick();
		expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
	});

	test('Escape key closes dialog', async () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			onConfirm: () => {}
		});
		const dialog = container.querySelector('[role="dialog"]') as HTMLDivElement;
		await fireEvent.keyDown(dialog, { key: 'Escape' });
		await tick();
		expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
	});

	test('Escape does NOT close when loading is true', async () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			loading: true,
			onConfirm: () => {}
		});
		const dialog = container.querySelector('[role="dialog"]') as HTMLDivElement;
		await fireEvent.keyDown(dialog, { key: 'Escape' });
		await tick();
		expect(container.querySelector('[role="dialog"]')).toBeInTheDocument();
	});

	test('backdrop click does NOT close when loading is true', async () => {
		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			loading: true,
			onConfirm: () => {}
		});
		const backdrop = container.querySelector('.hc-dialog-backdrop') as HTMLDivElement;
		await fireEvent.click(backdrop);
		await tick();
		expect(container.querySelector('[role="dialog"]')).toBeInTheDocument();
	});

	test('traps focus inside the dialog with Tab', async () => {
		vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
			callback(0);
			return 1;
		});

		const { container } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			onConfirm: () => {}
		});
		await tick();

		const dialog = container.querySelector('[role="dialog"]') as HTMLDivElement;
		const cancelBtn = container.querySelector(
			'.hc-dialog-actions .btn-standard'
		) as HTMLButtonElement;
		const confirmBtn = container.querySelector(
			'.hc-dialog-actions .btn-destructive'
		) as HTMLButtonElement;

		expect(document.activeElement).toBe(dialog);

		await fireEvent.keyDown(dialog, { key: 'Tab' });
		expect(document.activeElement).toBe(cancelBtn);

		await fireEvent.keyDown(cancelBtn, { key: 'Tab' });
		expect(document.activeElement).toBe(confirmBtn);

		// Wrap to first
		await fireEvent.keyDown(confirmBtn, { key: 'Tab' });
		expect(document.activeElement).toBe(cancelBtn);

		// Shift+Tab wraps backward
		await fireEvent.keyDown(cancelBtn, { key: 'Tab', shiftKey: true });
		expect(document.activeElement).toBe(confirmBtn);

		vi.unstubAllGlobals();
	});

	test('restores focus to the previously focused element when closed', async () => {
		vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
			callback(0);
			return 1;
		});

		const trigger = document.createElement('button');
		trigger.textContent = 'Open dialog';
		document.body.appendChild(trigger);
		trigger.focus();

		const { rerender } = renderComponent(ConfirmDialog, {
			open: true,
			title: 'Test',
			confirmLabel: 'Confirm',
			onConfirm: () => {}
		});
		await tick();

		await rerender({
			open: false,
			title: 'Test',
			confirmLabel: 'Confirm',
			onConfirm: () => {}
		});
		await tick();

		expect(document.activeElement).toBe(trigger);

		trigger.remove();
		vi.unstubAllGlobals();
	});
});
