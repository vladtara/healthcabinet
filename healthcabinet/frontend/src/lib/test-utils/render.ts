import { render } from '@testing-library/svelte';

/**
 * Svelte test render helper.
 * Wraps @testing-library/svelte render with project-level defaults.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function renderComponent(component: any, props?: Record<string, unknown>) {
	return render(component, props);
}
