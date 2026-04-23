<script lang="ts">
	import { goto } from '$app/navigation';
	import { login, me } from '$lib/api/auth';
	import { authStore } from '$lib/stores/auth.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	const copy = $derived(t(localeStore.locale).login);

	type LoginErrorKey = '' | 'suspended' | 'invalid' | 'generic';

	let email = $state('');
	let password = $state('');
	let errorKey = $state<LoginErrorKey>('');
	let isSubmitting = $state(false);
	let showPassword = $state(false);

	const error = $derived.by(() => {
		switch (errorKey) {
			case 'suspended':
				return copy.errorSuspended;
			case 'invalid':
				return copy.errorInvalid;
			case 'generic':
				return copy.errorGeneric;
			default:
				return '';
		}
	});

	async function handleSubmit(event: Event) {
		event.preventDefault();
		if (isSubmitting) return;

		isSubmitting = true;
		errorKey = '';

		try {
			const response = await login(email, password);
			authStore.setAccessToken(response.access_token);
			// Populate authStore.user so components can access profile data immediately.
			// me() is also called in authStore._doTryRefresh() (session restore on reload).
			// Both call sites are intentional — different code paths, safe independently.
			// Non-critical: session works even if /me fails (e.g. transient error).
			try {
				const userData = await me();
				authStore.setUser(userData);
			} catch {
				// Best-effort — do not block navigation on user profile fetch failure
			}
			await goto('/dashboard');
		} catch (e: unknown) {
			// Distinguish error types for user-facing messaging:
			// 401 = wrong credentials, 403 = account suspended, else = server/network error
			const status = (e as { status?: number })?.status;
			if (status === 403) {
				errorKey = 'suspended';
			} else if (status === 401) {
				errorKey = 'invalid';
			} else {
				errorKey = 'generic';
			}
		} finally {
			isSubmitting = false;
		}
	}
</script>

<svelte:head>
	<title>{copy.headTitle}</title>
	<meta name="description" content={copy.headDescription} />
	<meta name="robots" content="noindex" />
</svelte:head>

<main class="hc-auth-page">
	<div class="hc-auth-dialog hc-auth-login">
		<h1 class="hc-auth-dialog-header"><span aria-hidden="true">🔑</span> {copy.dialogHeader}</h1>
		<div class="hc-auth-dialog-subtitle">{copy.dialogSubtitle}</div>
		<div class="hc-auth-dialog-body">
			{#if error}
				<div id="form-error" class="hc-auth-error" role="alert">
					<span aria-hidden="true">⚠</span> {error}
				</div>
			{/if}

			<form onsubmit={handleSubmit} novalidate>
				<div class="hc-auth-field-group">
					<Label for="email">{copy.emailLabel}</Label>
					<Input
						id="email"
						type="email"
						bind:value={email}
						autocomplete="email"
						placeholder={copy.emailPlaceholder}
						aria-describedby={error ? 'form-error' : undefined}
						required
					/>
				</div>

				<div class="hc-auth-field-group">
					<Label for="password">{copy.passwordLabel}</Label>
					<div class="hc-password-wrapper">
						<Input
							id="password"
							type={showPassword ? 'text' : 'password'}
							bind:value={password}
							autocomplete="current-password"
							placeholder={copy.passwordPlaceholder}
							aria-describedby={error ? 'form-error' : undefined}
							required
						/>
						<button
							type="button"
							class="hc-password-toggle"
							onclick={() => (showPassword = !showPassword)}
							aria-label={showPassword ? copy.hidePassword : copy.showPassword}
						>
							{#if showPassword}
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
									<path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
								</svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
									<path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
									<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
								</svg>
							{/if}
						</button>
					</div>
				</div>

				<Button type="submit" variant="primary" class="hc-auth-submit" disabled={isSubmitting}>
					{isSubmitting ? copy.submitting : copy.submit}
				</Button>
			</form>

			<div class="hc-auth-link">
				{copy.linkPrompt} <a href="/register">{copy.linkTarget}</a>
			</div>
		</div>
		<div class="hc-auth-trust">
			<span aria-hidden="true">🔒</span> {copy.trust}
		</div>
	</div>
</main>
