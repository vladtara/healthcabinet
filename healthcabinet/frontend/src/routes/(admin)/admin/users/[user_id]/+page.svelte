<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { getAdminUserDetail, updateAdminUserStatus } from '$lib/api/admin';
	import { ConfirmDialog } from '$lib/components/ui/confirm-dialog';
	import { Badge, accountStatusVariant, accountStatusLabel } from '$lib/components/ui/badge';

	const queryClient = useQueryClient();
	const userId = $derived($page.params.user_id ?? '');

	let showConfirmDialog = $state(false);
	let pendingStatus = $state<'active' | 'suspended'>('suspended');
	let isUpdating = $state(false);
	let updateError = $state('');

	const userQuery = createQuery(() => ({
		queryKey: ['admin', 'users', userId],
		queryFn: () => getAdminUserDetail(userId),
		enabled: userId.length > 0,
		refetchOnWindowFocus: false,
		refetchOnReconnect: false,
	}));

	function handleRefresh() {
		queryClient.invalidateQueries({ queryKey: ['admin', 'users', userId] });
	}

	function promptStatusChange(newStatus: 'active' | 'suspended') {
		pendingStatus = newStatus;
		showConfirmDialog = true;
	}

	async function confirmStatusChange() {
		isUpdating = true;
		updateError = '';
		try {
			await updateAdminUserStatus(userId, pendingStatus);
			queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
		} catch {
			updateError = `Failed to ${pendingStatus === 'suspended' ? 'suspend' : 'reactivate'} account. Please try again.`;
		} finally {
			isUpdating = false;
			showConfirmDialog = false;
		}
	}

	function formatDate(dateStr: string | null | undefined): string {
		if (!dateStr) return 'Never';
		return new Date(dateStr).toLocaleString('en-GB', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		});
	}
</script>

<div class="hc-admin-user-detail-page">
	<button
		type="button"
		class="btn-standard hc-admin-user-detail-back"
		onclick={() => goto('/admin/users')}
	>
		← Back to users
	</button>

	{#if userQuery.isPending}
		<div class="hc-admin-user-detail-skeleton" role="status" aria-label="Loading user details">
			<div class="hc-admin-user-detail-skeleton-title"></div>
			<div class="hc-admin-user-detail-skeleton-panel"></div>
		</div>
	{:else if userQuery.isError}
		<div class="hc-state hc-state-error">
			<div role="alert">
				<p class="hc-state-title">Unable to load user details</p>
				<p>The user may not exist or you may not have permission.</p>
			</div>
			<button type="button" class="btn-standard" onclick={handleRefresh}>
				Try again
			</button>
		</div>
	{:else if userQuery.data}
		{@const user = userQuery.data}
		<header class="hc-admin-user-detail-header">
			<div>
				<h1 class="hc-admin-user-detail-title">{user.email}</h1>
				<p class="hc-admin-user-detail-id">{user.user_id}</p>
			</div>
			<button
				type="button"
				class="btn-standard"
				onclick={handleRefresh}
				aria-label="Refresh user details"
			>
				Refresh
			</button>
		</header>

		<fieldset class="hc-fieldset">
			<legend>Account Information</legend>
			<dl class="hc-admin-user-detail-meta-grid">
				<div>
					<dt class="hc-admin-user-detail-meta-label">Status</dt>
					<dd class="hc-admin-user-detail-meta-value">
						<Badge variant={accountStatusVariant(user.account_status)}>
							{accountStatusLabel(user.account_status)}
						</Badge>
					</dd>
				</div>
				<div>
					<dt class="hc-admin-user-detail-meta-label">Registered</dt>
					<dd class="hc-admin-user-detail-meta-value">{formatDate(user.registration_date)}</dd>
				</div>
				<div>
					<dt class="hc-admin-user-detail-meta-label">Last Login</dt>
					<dd class="hc-admin-user-detail-meta-value">{formatDate(user.last_login)}</dd>
				</div>
				<div>
					<dt class="hc-admin-user-detail-meta-label">Documents Uploaded</dt>
					<dd class="hc-admin-user-detail-meta-value hc-admin-user-detail-meta-value-numeric">
						{user.upload_count}
					</dd>
				</div>
			</dl>
		</fieldset>

		{#if updateError}
			<div class="hc-state hc-state-error" role="alert">
				<p class="hc-state-title">{updateError}</p>
			</div>
		{/if}

		<div class="hc-admin-user-detail-actions">
			{#if user.account_status === 'active'}
				<button
					type="button"
					class="btn-destructive"
					onclick={() => promptStatusChange('suspended')}
				>
					Suspend Account
				</button>
			{:else}
				<button
					type="button"
					class="btn-primary"
					onclick={() => promptStatusChange('active')}
				>
					Reactivate Account
				</button>
			{/if}
		</div>
	{/if}
</div>

<ConfirmDialog
	bind:open={showConfirmDialog}
	title={pendingStatus === 'suspended' ? 'Suspend Account?' : 'Reactivate Account?'}
	confirmLabel={pendingStatus === 'suspended' ? 'Suspend' : 'Reactivate'}
	confirmVariant={pendingStatus === 'suspended' ? 'destructive' : 'primary'}
	loading={isUpdating}
	loadingLabel="Updating…"
	onConfirm={confirmStatusChange}
>
	{#if pendingStatus === 'suspended'}
		<p>This will immediately prevent the user from logging in or accessing the platform. Existing sessions will be terminated on their next API call.</p>
	{:else}
		<p>This will restore the user's access to the platform. They can log in normally.</p>
	{/if}
</ConfirmDialog>
