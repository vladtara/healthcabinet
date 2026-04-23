import { createRawSnippet } from 'svelte';
import type { Snippet } from 'svelte';

type TableColumn = {
	key: string;
	label: string;
};

export function textSnippet(text: string) {
	return createRawSnippet(() => ({
		render: () => `<span>${text}</span>`
	}));
}

export function tableCellSnippet(): Snippet<[Record<string, unknown>, TableColumn]> {
	return createRawSnippet<[Record<string, unknown>, TableColumn]>((getRow, getColumn) => ({
		render: () => {
			const row = getRow();
			const column = getColumn();
			return `<span>${column.label}: ${String(row[column.key] ?? '')}</span>`;
		}
	}));
}
