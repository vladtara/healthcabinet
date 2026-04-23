<script lang="ts">
	import { goto } from '$app/navigation';
	import { register } from '$lib/api/auth';
	import type { ApiError } from '$lib/api/client.svelte';
	import { PRIVACY_POLICY_VERSION } from '$lib/constants';
	import { authStore } from '$lib/stores/auth.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	const copy = $derived(t(localeStore.locale).register);

	type EmailErrorKey = '' | 'required' | 'invalid' | 'taken';
	type PasswordErrorKey = '' | 'length' | 'tooLong';
	type FormErrorKey = '' | 'passwordMismatch' | 'inputGeneric' | 'registrationFailed' | 'custom';

	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let consentChecked = $state(false);
	let isSubmitting = $state(false);
	let emailErrorKey = $state<EmailErrorKey>('');
	let passwordErrorKey = $state<PasswordErrorKey>('');
	let formErrorKey = $state<FormErrorKey>('');
	let customFormError = $state('');
	let showPassword = $state(false);
	let showConfirmPassword = $state(false);

	const emailError = $derived.by(() => {
		switch (emailErrorKey) {
			case 'required':
				return copy.errorEmailRequired;
			case 'invalid':
				return copy.errorEmailInvalid;
			case 'taken':
				return copy.errorEmailTaken;
			default:
				return '';
		}
	});

	const passwordError = $derived.by(() => {
		switch (passwordErrorKey) {
			case 'length':
				return copy.errorPasswordLength;
			case 'tooLong':
				return copy.errorPasswordTooLong;
			default:
				return '';
		}
	});

	const formError = $derived.by(() => {
		switch (formErrorKey) {
			case 'passwordMismatch':
				return copy.errorPasswordMismatch;
			case 'inputGeneric':
				return copy.errorInputGeneric;
			case 'registrationFailed':
				return copy.errorRegistrationFailed;
			case 'custom':
				return customFormError;
			default:
				return '';
		}
	});

	function validateEmail() {
		if (!email) {
			emailErrorKey = 'required';
		} else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
			emailErrorKey = 'invalid';
		} else {
			emailErrorKey = '';
		}
	}

	// blur: only validate if user has typed something (skip pristine empty field)
	function validatePasswordBlur() {
		if (!password) return;
		if (password.length < 8) {
			passwordErrorKey = 'length';
		} else if (new TextEncoder().encode(password).length > 72) {
			passwordErrorKey = 'tooLong';
		} else {
			passwordErrorKey = '';
		}
	}

	// submit: full validation including empty check
	function validatePasswordSubmit() {
		if (!password || password.length < 8) {
			passwordErrorKey = 'length';
		} else if (new TextEncoder().encode(password).length > 72) {
			passwordErrorKey = 'tooLong';
		} else {
			passwordErrorKey = '';
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		if (!consentChecked || isSubmitting) return;

		formErrorKey = '';
		customFormError = '';
		validateEmail();
		validatePasswordSubmit();
		if (emailError || passwordError) return;

		if (password !== confirmPassword) {
			formErrorKey = 'passwordMismatch';
			return;
		}

		isSubmitting = true;
		emailErrorKey = '';
		passwordErrorKey = '';

		try {
			const response = await register(email, password, true, PRIVACY_POLICY_VERSION);
			authStore.setAccessToken(response.access_token);
			await goto('/onboarding');
		} catch (err) {
			const apiError = err as ApiError;
			if (apiError.status === 409) {
				emailErrorKey = 'taken';
			} else {
				const detail = apiError.detail;
				if (Array.isArray(detail)) {
					formErrorKey = 'inputGeneric';
				} else if (typeof detail === 'string' && detail.trim().length > 0) {
					customFormError = detail;
					formErrorKey = 'custom';
				} else {
					formErrorKey = 'registrationFailed';
				}
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
	<div class="hc-auth-dialog hc-auth-register">
		<h1 class="hc-auth-dialog-header"><span aria-hidden="true">📝</span> {copy.dialogHeader}</h1>
		<div class="hc-auth-dialog-subtitle">{copy.dialogSubtitle}</div>
		<div class="hc-auth-dialog-body">
			<form onsubmit={handleSubmit} novalidate>
				<div class="hc-auth-field-group">
					<Label for="email">{copy.emailLabel}</Label>
					<Input
						id="email"
						type="email"
						bind:value={email}
						onblur={validateEmail}
						aria-describedby={emailError ? 'email-error' : undefined}
						autocomplete="email"
						placeholder={copy.emailPlaceholder}
						required
					/>
					{#if emailError}
						<p id="email-error" class="hc-auth-field-error">{emailError}</p>
					{/if}
				</div>

				<div class="hc-auth-field-group">
					<Label for="password">{copy.passwordLabel}</Label>
					<div class="hc-password-wrapper">
						<Input
							id="password"
							type={showPassword ? 'text' : 'password'}
							bind:value={password}
							onblur={validatePasswordBlur}
							aria-describedby={passwordError ? 'password-error password-hint' : 'password-hint'}
							autocomplete="new-password"
							placeholder={copy.passwordPlaceholder}
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
					<div id="password-hint" class="hc-auth-helper-text">{copy.passwordHint}</div>
					{#if passwordError}
						<p id="password-error" class="hc-auth-field-error">{passwordError}</p>
					{/if}
				</div>

				<div class="hc-auth-field-group">
					<Label for="confirm-password">{copy.confirmPasswordLabel}</Label>
					<div class="hc-password-wrapper">
						<Input
							id="confirm-password"
							type={showConfirmPassword ? 'text' : 'password'}
							bind:value={confirmPassword}
							autocomplete="new-password"
							placeholder={copy.confirmPasswordPlaceholder}
							required
						/>
						<button
							type="button"
							class="hc-password-toggle"
							onclick={() => (showConfirmPassword = !showConfirmPassword)}
							aria-label={showConfirmPassword ? copy.hidePassword : copy.showPassword}
						>
							{#if showConfirmPassword}
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

				<div class="hc-auth-gdpr-section">
					<div class="hc-auth-consent-row">
						<Checkbox id="gdpr-consent" bind:checked={consentChecked} aria-describedby="gdpr-description" />
						<div>
							<label class="hc-auth-consent-label" for="gdpr-consent">{copy.consentLabel}</label>
							<div id="gdpr-description" class="hc-auth-consent-desc">
								{copy.consentDesc}
							</div>
							<a href="/privacy-policy" class="hc-auth-consent-link">{copy.consentLink}</a>
						</div>
					</div>
				</div>

				{#if formError}
					<div class="hc-auth-error" role="alert">
						<span aria-hidden="true">⚠</span> {formError}
					</div>
				{/if}

				<Button type="submit" variant="primary" class="hc-auth-submit" disabled={!consentChecked || isSubmitting}>
					{isSubmitting ? copy.submitting : copy.submit}
				</Button>
			</form>

			<div class="hc-auth-link">
				{copy.linkPrompt} <a href="/login">{copy.linkTarget}</a>
			</div>
		</div>
	</div>

	<div class="hc-auth-trust-below">
		<div class="hc-landing-trust-badge"><span aria-hidden="true">🔒</span> {copy.trustAes}</div>
		<div class="hc-landing-trust-badge"><span aria-hidden="true">🇪🇺</span> {copy.trustEu}</div>
		<div class="hc-landing-trust-badge"><span aria-hidden="true">🛡️</span> {copy.trustGdpr}</div>
	</div>
</main>
