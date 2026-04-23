import { describe, expect, test, vi } from 'vitest';
import { fireEvent } from '@testing-library/svelte';
import { tick } from 'svelte';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import SlideOver from './slide-over.svelte';

describe('SlideOver', () => {
	test('renders when open is true', () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Details',
			children: textSnippet('Panel content')
		});
		expect(container.querySelector('.hc-slide-over')).toBeInTheDocument();
		expect(container.textContent).toContain('Panel content');
	});

	test('hidden when open is false', () => {
		const { container } = renderComponent(SlideOver, {
			open: false,
			title: 'Details'
		});
		expect(container.querySelector('.hc-slide-over')).not.toBeInTheDocument();
	});

	test('renders title in title bar', () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Document Details'
		});
		const titleText = container.querySelector('.title-bar-text');
		expect(titleText?.textContent).toContain('Document Details');
	});

	test('renders children content', () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Test',
			children: textSnippet('Custom body content')
		});
		expect(container.textContent).toContain('Custom body content');
	});

	test('has role="dialog" and aria-modal', () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Test'
		});
		const panel = container.querySelector('.hc-slide-over');
		expect(panel?.getAttribute('role')).toBe('dialog');
		expect(panel?.getAttribute('aria-modal')).toBe('true');
	});

	test('has aria-label matching title', () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'My Panel'
		});
		const panel = container.querySelector('.hc-slide-over');
		expect(panel?.getAttribute('aria-label')).toBe('My Panel');
	});

	test('renders backdrop', () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Test'
		});
		expect(container.querySelector('.hc-slide-over-backdrop')).toBeInTheDocument();
	});

	test('renders close button in title bar', () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Test'
		});
		const closeBtn = container.querySelector('.title-bar-controls button');
		expect(closeBtn).toBeInTheDocument();
		expect(closeBtn?.getAttribute('type')).toBe('button');
		expect(closeBtn?.getAttribute('aria-label')).toBe('Close');
	});

	test('has scrollable body', () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Test',
			children: textSnippet('Body')
		});
		expect(container.querySelector('.hc-slide-over-body')).toBeInTheDocument();
	});

	test('applies custom class to panel', () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Test',
			class: 'extra-wide'
		});
		const panel = container.querySelector('.hc-slide-over');
		expect(panel?.classList.contains('extra-wide')).toBe(true);
	});

	test('backdrop click closes the panel', async () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Test'
		});
		const backdrop = container.querySelector('.hc-slide-over-backdrop') as HTMLDivElement;
		await fireEvent.click(backdrop);
		await tick();
		expect(container.querySelector('.hc-slide-over')).not.toBeInTheDocument();
	});

	test('Escape closes the panel', async () => {
		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Test'
		});
		const panel = container.querySelector('.hc-slide-over') as HTMLDivElement;
		await fireEvent.keyDown(panel, { key: 'Escape' });
		await tick();
		expect(container.querySelector('.hc-slide-over')).not.toBeInTheDocument();
	});

	test('traps focus inside the panel', async () => {
		vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
			callback(0);
			return 1;
		});

		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Test',
			children: textSnippet('<button type="button" id="inner-button">Inner action</button>')
		});
		await tick();

		const panel = container.querySelector('.hc-slide-over') as HTMLDivElement;
		const closeButton = container.querySelector('.title-bar-controls button') as HTMLButtonElement;
		const innerButton = container.querySelector('#inner-button') as HTMLButtonElement;

		expect(document.activeElement).toBe(panel);

		await fireEvent.keyDown(panel, { key: 'Tab' });
		expect(document.activeElement).toBe(closeButton);

		await fireEvent.keyDown(closeButton, { key: 'Tab' });
		expect(document.activeElement).toBe(innerButton);

		await fireEvent.keyDown(innerButton, { key: 'Tab' });
		expect(document.activeElement).toBe(closeButton);

		vi.unstubAllGlobals();
	});

	test('restores focus to the previously focused element when closed', async () => {
		vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
			callback(0);
			return 1;
		});

		const trigger = document.createElement('button');
		trigger.textContent = 'Open panel';
		document.body.appendChild(trigger);
		trigger.focus();

		const { rerender } = renderComponent(SlideOver, {
			open: true,
			title: 'Test'
		});
		await tick();

		await rerender({ open: false, title: 'Test' });
		await tick();

		expect(document.activeElement).toBe(trigger);

		trigger.remove();
		vi.unstubAllGlobals();
	});

	test('applies enter class for slide-in transition', async () => {
		vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
			callback(0);
			return 1;
		});

		const { container } = renderComponent(SlideOver, {
			open: true,
			title: 'Test'
		});
		await tick();

		expect(container.querySelector('.hc-slide-over')?.classList.contains('hc-slide-over-enter')).toBe(true);

		vi.unstubAllGlobals();
	});
});
