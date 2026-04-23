import { describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import { textSnippet } from '$lib/test-utils/snippet';
import WindowFrame from './window-frame.svelte';

describe('WindowFrame', () => {
	test('renders title text', () => {
		const { getByText } = renderComponent(WindowFrame, { title: 'Test Window' });
		expect(getByText('Test Window')).toBeInTheDocument();
	});

	test('renders with window and hc-window classes', () => {
		const { container } = renderComponent(WindowFrame, { title: 'Test' });
		const windowEl = container.querySelector('.window.hc-window');
		expect(windowEl).toBeInTheDocument();
	});

	test('renders snippet children inside window-body', () => {
		const { container, getByText } = renderComponent(WindowFrame, {
			title: 'Test',
			children: textSnippet('Body content')
		});
		const body = container.querySelector('.window-body');
		expect(body).toBeInTheDocument();
		expect(body).toContainElement(getByText('Body content'));
	});

	test('does not render controls by default', () => {
		const { container } = renderComponent(WindowFrame, { title: 'Test' });
		const controls = container.querySelector('.title-bar-controls');
		expect(controls).toBeNull();
	});

	test('renders controls when showControls is true', () => {
		const { container } = renderComponent(WindowFrame, { title: 'Test', showControls: true });
		const controls = container.querySelector('.title-bar-controls');
		const minimizeButton = container.querySelector(
			'button[aria-label="Minimize"]'
		) as HTMLButtonElement;
		const maximizeButton = container.querySelector(
			'button[aria-label="Maximize"]'
		) as HTMLButtonElement;
		const closeButton = container.querySelector(
			'button[aria-label="Close"]'
		) as HTMLButtonElement;

		expect(controls).toBeInTheDocument();
		expect(minimizeButton).toBeInTheDocument();
		expect(maximizeButton).toBeInTheDocument();
		expect(closeButton).toBeInTheDocument();
		expect(minimizeButton.type).toBe('button');
		expect(maximizeButton.type).toBe('button');
		expect(closeButton.type).toBe('button');
	});

	test('calls onClose when close button is clicked', async () => {
		const onClose = vi.fn();
		const { container } = renderComponent(WindowFrame, { title: 'Test', showControls: true, onClose });
		const closeBtn = container.querySelector('button[aria-label="Close"]') as HTMLButtonElement;
		closeBtn.click();
		expect(onClose).toHaveBeenCalledOnce();
	});

	test('applies custom class', () => {
		const { container } = renderComponent(WindowFrame, { title: 'Test', class: 'w-full' });
		const windowEl = container.querySelector('.window.hc-window');
		expect(windowEl?.classList.contains('w-full')).toBe(true);
	});
});
