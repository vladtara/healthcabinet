import { describe, expect, test, vi } from 'vitest';
import { tick } from 'svelte';
import { renderComponent } from '$lib/test-utils/render';
import { tableCellSnippet } from '$lib/test-utils/snippet';
import DataTable from './data-table.svelte';

const columns = [
	{ key: 'name', label: 'Name', sortable: true },
	{ key: 'value', label: 'Value', sortable: true, align: 'right' as const },
	{ key: 'status', label: 'Status' }
];

const rows = [
	{ name: 'TSH', value: 5.82, status: 'Borderline' },
	{ name: 'T3', value: 120, status: 'Optimal' },
	{ name: 'Glucose', value: 95, status: 'Optimal' }
];

describe('DataTable', () => {
	test('renders column headers', () => {
		const { container } = renderComponent(DataTable, { columns, rows });
		const headers = container.querySelectorAll('th');
		expect(headers.length).toBe(3);
		expect(headers[0].textContent).toContain('Name');
		expect(headers[1].textContent).toContain('Value');
		expect(headers[2].textContent).toContain('Status');
	});

	test('renders data rows', () => {
		const { container } = renderComponent(DataTable, { columns, rows });
		const tds = container.querySelectorAll('tbody td');
		expect(tds.length).toBe(9); // 3 rows × 3 columns
		expect(tds[0].textContent).toContain('TSH');
		expect(tds[1].textContent).toContain('5.82');
	});

	test('renders sort indicator on sortable columns', () => {
		const { container } = renderComponent(DataTable, { columns, rows });
		const indicators = container.querySelectorAll('.hc-sort-indicator');
		expect(indicators.length).toBe(2); // Name and Value are sortable
	});

	test('sort toggles on header click', async () => {
		const { container } = renderComponent(DataTable, { columns, rows });
		const sortButton = container.querySelector('.hc-sort-button') as HTMLButtonElement;
		expect(sortButton).toBeInTheDocument();

		// Click to sort ascending by name
		sortButton.click();
		await tick();
		const firstCellAfterSort = container.querySelector('tbody tr:first-child td');
		expect(firstCellAfterSort?.textContent).toContain('Glucose'); // G < T alphabetically

		// Click again to sort descending
		sortButton.click();
		await tick();
		const firstCellDesc = container.querySelector('tbody tr:first-child td');
		expect(firstCellDesc?.textContent).toContain('TSH'); // T > G
	});

	test('row click fires callback', () => {
		const onRowClick = vi.fn();
		const { container } = renderComponent(DataTable, { columns, rows, onRowClick });
		const firstRow = container.querySelector('tbody tr') as HTMLTableRowElement;
		expect(firstRow).toBeInTheDocument();
		firstRow.click();
		expect(onRowClick).toHaveBeenCalledOnce();
		expect(onRowClick).toHaveBeenCalledWith(rows[0]);
	});

	test('Enter key fires row click callback', () => {
		const onRowClick = vi.fn();
		const { container } = renderComponent(DataTable, { columns, rows, onRowClick });
		const firstRow = container.querySelector('tbody tr') as HTMLTableRowElement;
		firstRow.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
		expect(onRowClick).toHaveBeenCalledOnce();
	});

	test('interactive rows have tabindex', () => {
		const onRowClick = vi.fn();
		const { container } = renderComponent(DataTable, { columns, rows, onRowClick });
		const firstRow = container.querySelector('tbody tr') as HTMLTableRowElement;
		expect(firstRow.getAttribute('role')).toBe('button');
		expect(firstRow.getAttribute('tabindex')).toBe('0');
	});

	test('non-interactive rows lack tabindex', () => {
		const { container } = renderComponent(DataTable, { columns, rows });
		const firstRow = container.querySelector('tbody tr') as HTMLTableRowElement;
		expect(firstRow.getAttribute('tabindex')).toBeNull();
	});

	test('sorted column header has aria-sort attribute', async () => {
		const { container } = renderComponent(DataTable, { columns, rows });
		const sortButton = container.querySelector('.hc-sort-button') as HTMLButtonElement;
		sortButton.click();
		await tick();
		const th = sortButton.closest('th');
		expect(th?.getAttribute('aria-sort')).toBe('ascending');
	});

	test('applies hc-data-table class', () => {
		const { container } = renderComponent(DataTable, { columns, rows });
		const el = container.firstElementChild;
		expect(el?.classList.contains('hc-data-table')).toBe(true);
	});

	test('applies custom class', () => {
		const { container } = renderComponent(DataTable, { columns, rows, class: 'mt-4' });
		const el = container.firstElementChild;
		expect(el?.classList.contains('mt-4')).toBe(true);
	});

	test('renders custom cell snippet when provided', () => {
		const { container } = renderComponent(DataTable, {
			columns,
			rows,
			children: tableCellSnippet()
		});
		expect(container.textContent).toContain('Name: TSH');
		expect(container.textContent).toContain('Value: 5.82');
	});
});
