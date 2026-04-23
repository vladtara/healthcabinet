<script lang="ts">
	import { onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { getAdminUsers, getFlaggedReports, markFlagReviewed } from '$lib/api/admin';
	import { DataTable, type Column } from '$lib/components/ui/data-table';
	import { Badge, accountStatusVariant, accountStatusLabel } from '$lib/components/ui/badge';

	const queryClient = useQueryClient();

	let searchQuery = $state('');
	let debouncedQuery = $state('');
	let debounceTimer: ReturnType<typeof setTimeout> | undefined;
	let reviewError = $state('');
	let reviewingIds = $state(new Set<string>());

	function handleSearch(value: string) {
		searchQuery = value;
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			debouncedQuery = value.trim();
		}, 300);
	}

	const usersQuery = createQuery(() => ({
		queryKey: ['admin', 'users', debouncedQuery],
		queryFn: () => getAdminUsers(debouncedQuery || undefined),
		refetchOnWindowFocus: false,
		refetchOnReconnect: false,
	}));

	const flagsQuery = createQuery(() => ({
		queryKey: ['admin', 'flags'],
		queryFn: getFlaggedReports,
		refetchOnWindowFocus: false,
		refetchOnReconnect: false,
	}));

	function handleRefresh() {
		queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
		queryClient.invalidateQueries({ queryKey: ['admin', 'flags'] });
	}

	async function handleReviewFlag(healthValueId: string) {
		if (reviewingIds.has(healthValueId)) return;
		reviewingIds = new Set([...reviewingIds, healthValueId]);
		reviewError = '';
		try {
			await markFlagReviewed(healthValueId);
			queryClient.invalidateQueries({ queryKey: ['admin', 'flags'] });
			queryClient.invalidateQueries({ queryKey: ['admin', 'queue'] });
		} catch {
			reviewError = 'Failed to mark flag as reviewed. Please try again.';
		} finally {
			reviewingIds = new Set([...reviewingIds].filter((id) => id !== healthValueId));
		}
	}

	onDestroy(() => {
		clearTimeout(debounceTimer);
	});

	function truncateId(id: string): string {
		return id.slice(0, 8) + '…';
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
		});
	}

	const columns: Column[] = [
		{ key: 'email', label: 'Email', sortable: true },
		{ key: 'user_id', label: 'User ID', sortable: true },
		{ key: 'registration_date', label: 'Registered', sortable: true },
		{ key: 'upload_count', label: 'Uploads', sortable: true, align: 'center' },
		{ key: 'account_status', label: 'Status', sortable: true },
	];

	let rows = $derived(
		(usersQuery.data?.items ?? []).map((user) => ({
			email: user.email,
			user_id: user.user_id,
			registration_date: user.registration_date,
			upload_count: user.upload_count,
			account_status: user.account_status,
		}))
	);

	function handleRowClick(row: Record<string, unknown>) {
		const id = row.user_id;
		if (typeof id === 'string') {
			goto(`/admin/users/${id}`);
		}
	}
</script>

<div class="hc-admin-users-page">
	<header class="hc-admin-users-header">
		<div>
			<h1 class="hc-admin-users-title">User Management</h1>
			<p class="hc-admin-users-subtitle">
				View accounts, manage suspension, and review flagged values
			</p>
		</div>
		<button
			type="button"
			class="btn-standard"
			onclick={handleRefresh}
			aria-label="Refresh user list"
		>
			Refresh
		</button>
	</header>

	<label class="hc-admin-users-search-label">
		<span class="hc-admin-users-search-label-text">Search users</span>
		<input
			type="text"
			placeholder="Search by email or user ID…"
			value={searchQuery}
			oninput={(e) => handleSearch(e.currentTarget.value)}
			class="hc-input hc-admin-users-search"
			aria-label="Search users"
		/>
	</label>

	{#if usersQuery.isPending}
		<div class="hc-admin-users-skeleton" role="status" aria-label="Loading users">
			{#each Array(5) as _}
				<div class="hc-admin-users-skeleton-row"></div>
			{/each}
		</div>
	{:else if usersQuery.isError}
		<div class="hc-state hc-state-error">
			<div role="alert">
				<p class="hc-state-title">Unable to load user list</p>
				<p>Try refreshing the page or contact support if the issue persists.</p>
			</div>
			<button type="button" class="btn-standard" onclick={handleRefresh}>
				Try again
			</button>
		</div>
	{:else if usersQuery.data}
		{@const data = usersQuery.data}
		{#if data.items.length === 0}
			<div class="hc-admin-users-empty-panel">
				<div class="hc-state hc-state-empty">
					<p class="hc-state-title">{debouncedQuery ? 'No users match your search' : 'No users found'}</p>
					<p>
						{debouncedQuery ? 'Try a different search term.' : 'Users will appear here after registration.'}
					</p>
				</div>
			</div>
		{:else}
			<DataTable {columns} {rows} onRowClick={handleRowClick}>
				{#snippet children(row, col)}
					{#if col.key === 'user_id'}
						<span>{truncateId(String(row.user_id))}</span>
					{:else if col.key === 'registration_date'}
						{formatDate(String(row.registration_date))}
					{:else if col.key === 'upload_count'}
						<span class="hc-admin-users-count-cell">{row.upload_count}</span>
					{:else if col.key === 'account_status'}
						<Badge variant={accountStatusVariant(String(row.account_status))}>
							{accountStatusLabel(String(row.account_status))}
						</Badge>
					{:else}
						{row[col.key] ?? ''}
					{/if}
				{/snippet}
			</DataTable>
			<p class="hc-admin-users-footer-count">
				Showing {data.items.length} user{data.items.length !== 1 ? 's' : ''}
			</p>
		{/if}
	{/if}

	<section class="hc-admin-users-flags-section">
		<h2 class="hc-admin-users-section-title">Flagged Value Reports</h2>

		{#if reviewError}
			<div class="hc-state hc-state-error" role="alert">
				<p class="hc-state-title">{reviewError}</p>
			</div>
		{/if}

		{#if flagsQuery.isPending}
			<div class="hc-admin-users-flags-skeleton" role="status" aria-label="Loading flagged reports">
				{#each Array(3) as _}
					<div class="hc-admin-users-flags-skeleton-row"></div>
				{/each}
			</div>
		{:else if flagsQuery.isError}
			<div class="hc-state hc-state-error" role="alert">
				<p class="hc-state-title">Unable to load flagged reports</p>
			</div>
		{:else if flagsQuery.data}
			{@const flags = flagsQuery.data}
			{#if flags.items.length === 0}
				<div class="hc-admin-users-flags-empty">
					<div class="hc-state hc-state-empty">
						<p>No unreviewed flagged values.</p>
					</div>
				</div>
			{:else}
				<div class="hc-data-table hc-admin-users-flags-table">
					<table>
						<thead>
							<tr>
								<th>Biomarker</th>
								<th>Flagged Value</th>
								<th>User ID</th>
								<th>Document ID</th>
								<th>Flagged At</th>
								<th>Actions</th>
							</tr>
						</thead>
						<tbody>
							{#each flags.items as flag (flag.health_value_id)}
								<tr>
									<td>{flag.value_name}</td>
									<td class="hc-admin-users-flag-value">{flag.flagged_value}</td>
									<td>
										<button
											type="button"
											class="hc-admin-users-flag-userlink"
											onclick={() => goto(`/admin/users/${flag.user_id}`)}
										>
											{truncateId(flag.user_id)}
										</button>
									</td>
									<td>{truncateId(flag.document_id)}</td>
									<td>{formatDate(flag.flagged_at)}</td>
									<td>
										<div class="hc-admin-users-flag-actions">
											<button
												type="button"
												class="btn-standard"
												onclick={() =>
													goto(
														`/admin/documents/${flag.document_id}?health_value_id=${flag.health_value_id}`
													)}
											>
												Open correction flow
											</button>
											<button
												type="button"
												class="btn-primary"
												onclick={() => handleReviewFlag(flag.health_value_id)}
												disabled={reviewingIds.has(flag.health_value_id)}
											>
												{reviewingIds.has(flag.health_value_id) ? 'Reviewing…' : 'Mark Reviewed'}
											</button>
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
				<p class="hc-admin-users-flags-footer-count">
					{flags.total} unreviewed flag{flags.total !== 1 ? 's' : ''}
				</p>
			{/if}
		{/if}
	</section>
</div>
