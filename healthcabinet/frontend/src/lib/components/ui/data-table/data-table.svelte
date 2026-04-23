<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';

	export interface Column {
		key: string;
		label: string;
		sortable?: boolean;
		align?: 'left' | 'center' | 'right';
		class?: string;
	}

	interface Props extends Omit<HTMLAttributes<HTMLDivElement>, 'children'> {
		columns: Column[];
		rows: Record<string, unknown>[];
		onRowClick?: (row: Record<string, unknown>) => void;
		children?: Snippet<[Record<string, unknown>, Column]>;
	}

	let { columns, rows, onRowClick, children, class: className, ...rest }: Props = $props();
	let classes = $derived(`hc-data-table ${className ?? ''}`.trim());

	let sortKey = $state<string | null>(null);
	let sortDir = $state<'asc' | 'desc'>('asc');

	function toggleSort(key: string) {
		if (sortKey === key) {
			sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDir = 'asc';
		}
	}

	let sortedRows = $derived.by(() => {
		if (!sortKey) return rows;
		const key = sortKey;
		return [...rows].sort((a, b) => {
			const av = a[key];
			const bv = b[key];
			const cmp = av == null && bv == null ? 0 : av == null ? -1 : bv == null ? 1 : av < bv ? -1 : av > bv ? 1 : 0;
			return sortDir === 'asc' ? cmp : -cmp;
		});
	});

	function handleRowKeydown(e: KeyboardEvent, row: Record<string, unknown>) {
		if ((e.key === 'Enter' || e.key === ' ') && onRowClick) {
			if (e.key === ' ') e.preventDefault();
			onRowClick(row);
		}
	}

	function ariaSortValue(colKey: string): 'ascending' | 'descending' | 'none' {
		if (sortKey !== colKey) return 'none';
		return sortDir === 'asc' ? 'ascending' : 'descending';
	}
</script>

<div class={classes} {...rest}>
	<table>
		<thead>
			<tr>
				{#each columns as col}
					<th
						style={col.align ? `text-align: ${col.align}` : undefined}
						class={col.class ?? undefined}
						aria-sort={col.sortable ? ariaSortValue(col.key) : undefined}
					>
						{#if col.sortable}
							<button
								type="button"
								class="hc-sort-button"
								onclick={() => toggleSort(col.key)}
							>
								{col.label}
								<span class="hc-sort-indicator {sortKey === col.key ? 'hc-sort-active' : ''}" aria-hidden="true">
									{#if sortKey === col.key}
										{sortDir === 'asc' ? '▲' : '▼'}
									{:else}
										⇅
									{/if}
								</span>
							</button>
						{:else}
							{col.label}
						{/if}
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each sortedRows as row}
				<tr
					class={onRowClick ? 'hc-row-interactive' : undefined}
					role={onRowClick ? 'button' : undefined}
					onclick={onRowClick ? () => onRowClick!(row) : undefined}
					onkeydown={onRowClick ? (e: KeyboardEvent) => handleRowKeydown(e, row) : undefined}
					tabindex={onRowClick ? 0 : undefined}
				>
					{#each columns as col}
						<td style={col.align ? `text-align: ${col.align}` : undefined} class={col.class ?? undefined}>
							{#if children}
								{@render children(row, col)}
							{:else}
								{row[col.key] ?? ''}
							{/if}
						</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
</div>
