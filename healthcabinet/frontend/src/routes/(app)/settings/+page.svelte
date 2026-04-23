<script lang="ts">
	import { beforeNavigate, goto } from '$app/navigation';
	import { createMutation } from '@tanstack/svelte-query';
	import {
		deleteMyAccount,
		exportMyData,
		getConsentHistory,
		getProfile,
		updateProfile
	} from '$lib/api/users';
	import type { ProfileUpdateData } from '$lib/api/users';
	import { authStore } from '$lib/stores/auth.svelte';
	import type { ConsentLog, UserProfile } from '$lib/types/api';
	import { ConfirmDialog } from '$lib/components/ui/confirm-dialog';
	import { formatTime } from '$lib/i18n/format';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const PRESET_CONDITIONS = [
		'Type 2 Diabetes',
		'Hypertension',
		'Hypothyroidism',
		"Hashimoto's",
		'Hyperthyroidism',
		'High Cholesterol',
		'Asthma',
		'PCOS',
		'Anemia',
		'Cardiovascular Disease',
		'Kidney Disease',
		'Liver Disease'
	];

	const PRESET_FAMILY_HISTORY = [
		'Heart Disease',
		'Diabetes',
		'Thyroid Disease',
		'Cancer',
		'High Blood Pressure',
		'Autoimmune Disease'
	];

	let selectedFamilyHistory = $state<string[]>([]);
	let legacyFamilyHistory = $state('');

	// Form fields
	let age = $state<number | null>(null);
	let sex = $state<'male' | 'female' | 'other' | 'prefer_not_to_say' | ''>('');
	let heightCm = $state<number | null>(null);
	let weightKg = $state<number | null>(null);
	let selectedConditions = $state<string[]>([]);
	let medications = $state('');
	let familyHistory = $state('');
	let otherCondition = $state('');
	// Success/error banner sentinels — resolved against locale at render so a
	// mid-flight locale toggle retranslates the banner without losing the state.
	let successState = $state<'saved' | ''>('');
	let errorState = $state<'saveFailed' | ''>('');
	let errors = $state<Record<string, 'age' | 'height' | 'weight'>>({});
	let exportLoading = $state(false);
	let exportSuccess = $state(false);
	// Export error: either a resolved backend `detail`/`title` string (passthrough
	// per Story 15.6 AC 5) or a sentinel that maps to localized fallback copy.
	let exportErrorBackend = $state<string | null>(null);
	let exportErrorFallback = $state(false);

	// Account deletion
	let deleteDialogOpen = $state(false);
	let confirmEmail = $state('');
	let deleteLoading = $state(false);
	let deleteErrorBackend = $state<string | null>(null);
	let deleteErrorFallback = $state(false);
	let emailMatches = $derived(
		confirmEmail.trim().toLowerCase() === (authStore.user?.email ?? '').toLowerCase()
	);

	// Consent history
	let consentLogs = $state<ConsentLog[]>([]);
	let consentLoading = $state(true);
	let consentErrored = $state(false);

	// Localized copy bundles — read through $derived so every toggle flip
	// retranslates visible text without clearing state.
	const copy = $derived(t(localeStore.locale).settings);
	const presets = $derived(t(localeStore.locale).presets);
	const confirmDialogCopy = $derived(t(localeStore.locale).confirmDialog);

	function errorMessage(kind: 'age' | 'height' | 'weight'): string {
		if (kind === 'age') return copy.errorAgeRange;
		if (kind === 'height') return copy.errorHeightRange;
		return copy.errorWeightRange;
	}

	// Dirty state tracking
	interface FormBaseline {
		age: number | null;
		sex: string | null;
		heightCm: number | null;
		weightKg: number | null;
		conditions: string[];
		medications: string;
		familyHistory: string[];
	}
	let baseline = $state<FormBaseline | null>(null);
	let isDirty = $derived(
		baseline !== null &&
			(age !== baseline.age ||
				sex !== baseline.sex ||
				heightCm !== baseline.heightCm ||
				weightKg !== baseline.weightKg ||
				medications !== baseline.medications ||
				JSON.stringify([...selectedConditions].sort()) !==
					JSON.stringify([...baseline.conditions].sort()) ||
				JSON.stringify([...selectedFamilyHistory].sort()) !==
					JSON.stringify([...baseline.familyHistory].sort()))
	);

	function captureBaseline(): FormBaseline {
		return {
			age,
			sex,
			heightCm,
			weightKg,
			conditions: [...selectedConditions],
			medications,
			familyHistory: [...selectedFamilyHistory]
		};
	}

	function formatConsentType(type: string): string {
		return (
			copy.consentTypes[type as keyof typeof copy.consentTypes] ??
			type
			.replace(/_/g, ' ')
			.replace(/\b\w/g, (c) => c.toUpperCase())
		);
	}

	function formatConsentDate(iso: string): string {
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;

		// Keep English output stable while switching Ukrainian users onto a
		// localized month/date rendering instead of a hard-coded English locale.
		const date = new Intl.DateTimeFormat(localeStore.locale === 'uk' ? 'uk-UA' : 'en-GB', {
			day: '2-digit',
			month: 'short',
			year: 'numeric',
			timeZone: 'UTC'
		}).format(d);
		const time = formatTime(iso, localeStore.locale, {
			hour: '2-digit',
			minute: '2-digit',
			hour12: false,
			timeZone: 'UTC'
		});
		return `${date}, ${time} UTC`;
	}

	function clearError(field: string) {
		const nextErrors = { ...errors };
		delete nextErrors[field];
		errors = nextErrors;
	}

	function handleAgeBlur() {
		if (age !== null && (age < 1 || age > 120)) {
			errors = { ...errors, age: 'age' };
		} else {
			clearError('age');
		}
	}

	function handleHeightBlur() {
		if (heightCm !== null && (heightCm < 50 || heightCm > 300)) {
			errors = { ...errors, height_cm: 'height' };
		} else {
			clearError('height_cm');
		}
	}

	function handleWeightBlur() {
		if (weightKg !== null && (weightKg < 10 || weightKg > 500)) {
			errors = { ...errors, weight_kg: 'weight' };
		} else {
			clearError('weight_kg');
		}
	}

	// Load profile on mount
	$effect(() => {
		getProfile().then((profile) => {
			if (!profile) {
				baseline = captureBaseline();
				return;
			}
			if (profile.age !== null) age = profile.age;
			if (profile.sex) sex = profile.sex;
			if (profile.height_cm !== null) heightCm = profile.height_cm;
			if (profile.weight_kg !== null) weightKg = profile.weight_kg;
			if (profile.known_conditions?.length) selectedConditions = [...profile.known_conditions];
			if (profile.medications?.length) medications = profile.medications.join(', ');
			if (profile.family_history) {
				const parts = profile.family_history.split(',').map((s: string) => s.trim()).filter(Boolean);
				const matched = new Set<string>();
				const unmatched: string[] = [];
				for (const part of parts) {
					const preset = PRESET_FAMILY_HISTORY.find(
						(p) => p.toLowerCase() === part.toLowerCase()
					);
					if (preset && !matched.has(preset)) {
						matched.add(preset);
					} else if (!preset) {
						unmatched.push(part);
					}
				}
				selectedFamilyHistory = [...matched];
				legacyFamilyHistory = unmatched.join(', ');
			}
			baseline = captureBaseline();
		});
	});

	// Load consent history on mount
	$effect(() => {
		consentLoading = true;
		consentErrored = false;
		getConsentHistory()
			.then((logs) => {
				consentLogs = logs;
			})
			.catch(() => {
				consentErrored = true;
			})
			.finally(() => {
				consentLoading = false;
			});
	});

	// Navigation guards for unsaved changes
	let bypassNavGuard = false;

	beforeNavigate((navigation) => {
		if (isDirty && !bypassNavGuard) {
			navigation.cancel();
			if (confirm(copy.unsavedChangesConfirm)) {
				bypassNavGuard = true;
				goto(navigation.to?.url.pathname ?? '/dashboard');
			}
		}
		bypassNavGuard = false;
	});

	// Browser beforeunload guard (tab close, refresh, external URL)
	$effect(() => {
		if (typeof window === 'undefined') return;
		const handler = (e: BeforeUnloadEvent) => {
			e.preventDefault();
		};
		if (isDirty) {
			window.addEventListener('beforeunload', handler);
		}
		return () => window.removeEventListener('beforeunload', handler);
	});

	const saveMutation = createMutation<UserProfile, Error, ProfileUpdateData>(() => ({
		mutationFn: (data: ProfileUpdateData) => updateProfile(data),
		onSuccess: () => {
			successState = 'saved';
			errorState = '';
			baseline = captureBaseline();
			setTimeout(() => {
				successState = '';
			}, 3000);
		},
		onError: () => {
			errorState = 'saveFailed';
			successState = '';
		}
	}));

	function toggleCondition(condition: string) {
		if (selectedConditions.includes(condition)) {
			selectedConditions = selectedConditions.filter((c) => c !== condition);
		} else {
			selectedConditions = [...selectedConditions, condition];
		}
	}

	function addOtherCondition() {
		const trimmed = otherCondition.trim();
		if (trimmed && !selectedConditions.includes(trimmed)) {
			selectedConditions = [...selectedConditions, trimmed];
			otherCondition = '';
		}
	}

	function handleOtherConditionKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addOtherCondition();
		}
	}

	function handleSave() {
		const medList = medications
			.split(',')
			.map((m) => m.trim())
			.filter(Boolean);

		const familyParts = [...selectedFamilyHistory];
		if (legacyFamilyHistory.trim()) {
			familyParts.push(legacyFamilyHistory.trim());
		}
		const familyHistoryText = familyParts.join(', ') || null;

		saveMutation.mutate({
			age: age ?? undefined,
			sex: sex || undefined,
			height_cm: heightCm ?? undefined,
			weight_kg: weightKg ?? undefined,
			known_conditions: selectedConditions,
			medications: medList,
			family_history: familyHistoryText
		} satisfies ProfileUpdateData);
	}

	// Returns a backend-provided `detail` or `title` if present (passthrough per
	// Story 15.6 AC 5), otherwise `null` so the caller renders the localized fallback.
	function readBackendErrorDetail(error: unknown): string | null {
		if (error && typeof error === 'object') {
			const detail = 'detail' in error ? error.detail : undefined;
			if (typeof detail === 'string' && detail.trim().length > 0) {
				return detail;
			}
			const title = 'title' in error ? error.title : undefined;
			if (typeof title === 'string' && title.trim().length > 0) {
				return title;
			}
		}
		return null;
	}

	async function handleExport() {
		exportLoading = true;
		exportSuccess = false;
		exportErrorBackend = null;
		exportErrorFallback = false;
		try {
			await exportMyData();
			exportSuccess = true;
			setTimeout(() => {
				exportSuccess = false;
			}, 3000);
		} catch (error) {
			const backend = readBackendErrorDetail(error);
			if (backend) {
				exportErrorBackend = backend;
			} else {
				exportErrorFallback = true;
			}
		} finally {
			exportLoading = false;
		}
	}

	function openDeleteDialog() {
		confirmEmail = '';
		deleteErrorBackend = null;
		deleteErrorFallback = false;
		deleteDialogOpen = true;
	}

	async function handleDeleteAccount() {
		deleteLoading = true;
		deleteErrorBackend = null;
		deleteErrorFallback = false;
		try {
			await deleteMyAccount();
			deleteDialogOpen = false;
			try { await authStore.logout(); } catch { /* best-effort cookie clear */ }
			goto('/?deleted=true');
		} catch (error) {
			const backend = readBackendErrorDetail(error);
			if (backend) {
				deleteErrorBackend = backend;
			} else {
				deleteErrorFallback = true;
			}
		} finally {
			deleteLoading = false;
		}
	}
</script>

<div class="hc-profile-page">
	<h1 class="hc-profile-title">{copy.title}</h1>

	{#if successState}
		<div class="hc-state hc-state-success" role="status">
			<p class="hc-state-title">{copy.saveSuccess}</p>
		</div>
	{/if}

	{#if errorState}
		<div class="hc-state hc-state-error" role="alert">
			<p class="hc-state-title">{copy.saveError}</p>
		</div>
	{/if}

	<div class="hc-profile-sections">
		<!-- Basic Information -->
		<fieldset class="hc-fieldset">
			<legend>{copy.legendBasicInfo}</legend>

			<div class="hc-profile-inline-fields">
				<div class="hc-profile-field-group">
					<label class="hc-label" for="age">{copy.ageLabel}</label>
					<input
						id="age"
						type="number"
						class="hc-input"
						style="width:100%"
						min="1"
						max="120"
						bind:value={age}
						onblur={handleAgeBlur}
						aria-invalid={!!errors.age}
						aria-describedby={errors.age ? 'age-error' : undefined}
					/>
					{#if errors.age}
						<p id="age-error" class="hc-profile-field-error" role="alert">{errorMessage(errors.age)}</p>
					{/if}
				</div>

				<div class="hc-profile-field-group">
					<label class="hc-label" for="sex">{copy.sexLabel}</label>
					<select
						id="sex"
						class="hc-input"
						style="width:100%"
						bind:value={sex}
					>
						<option value="" disabled>{presets.sex.select}</option>
						<option value="female">{presets.sex.female}</option>
						<option value="male">{presets.sex.male}</option>
						<option value="other">{presets.sex.other}</option>
						<option value="prefer_not_to_say">{presets.sex.prefer_not_to_say}</option>
					</select>
				</div>

				<div class="hc-profile-field-group">
					<label class="hc-label" for="height">{copy.heightLabel}</label>
					<input
						id="height"
						type="number"
						class="hc-input"
						style="width:100%"
						min="50"
						max="300"
						step="0.1"
						bind:value={heightCm}
						onblur={handleHeightBlur}
						aria-invalid={!!errors.height_cm}
						aria-describedby={errors.height_cm ? 'height-error' : undefined}
					/>
					{#if errors.height_cm}
						<p id="height-error" class="hc-profile-field-error" role="alert">
							{errorMessage(errors.height_cm)}
						</p>
					{/if}
				</div>

				<div class="hc-profile-field-group">
					<label class="hc-label" for="weight">{copy.weightLabel}</label>
					<input
						id="weight"
						type="number"
						class="hc-input"
						style="width:100%"
						min="10"
						max="500"
						step="0.1"
						bind:value={weightKg}
						onblur={handleWeightBlur}
						aria-invalid={!!errors.weight_kg}
						aria-describedby={errors.weight_kg ? 'weight-error' : undefined}
					/>
					{#if errors.weight_kg}
						<p id="weight-error" class="hc-profile-field-error" role="alert">
							{errorMessage(errors.weight_kg)}
						</p>
					{/if}
				</div>
			</div>
		</fieldset>

		<!-- Health Conditions -->
		<fieldset class="hc-fieldset">
			<legend>{copy.legendHealthConditions}</legend>

			<div style="margin-bottom:8px; font-size:14px;">{copy.conditionsPrompt}</div>
			<div class="hc-profile-checkbox-grid" role="group" aria-label={copy.conditionsGroupAria}>
				{#each PRESET_CONDITIONS as condition}
					<label>
						<input
							type="checkbox"
							class="hc-checkbox"
							checked={selectedConditions.includes(condition)}
							onchange={() => toggleCondition(condition)}
						/>
						{presets.conditions[condition as keyof typeof presets.conditions] ?? condition}
					</label>
				{/each}
			</div>

			<div class="hc-profile-add-condition">
				<input
					class="hc-input"
					bind:value={otherCondition}
					placeholder={copy.conditionOtherPlaceholder}
					onkeydown={handleOtherConditionKeydown}
					aria-label={copy.conditionOtherAria}
				/>
				<button type="button" class="btn-standard" onclick={addOtherCondition}>{copy.conditionAdd}</button>
			</div>

			{#if selectedConditions.some((c) => !PRESET_CONDITIONS.includes(c))}
				<div class="hc-profile-custom-conditions">
					{#each selectedConditions.filter((c) => !PRESET_CONDITIONS.includes(c)) as custom}
						<label>
							<input
								type="checkbox"
								class="hc-checkbox"
								checked={true}
								onchange={() => toggleCondition(custom)}
							/>
							{custom}
						</label>
					{/each}
				</div>
			{/if}
		</fieldset>

		<!-- Current Medications -->
		<fieldset class="hc-fieldset">
			<legend>{copy.legendMedications}</legend>
			<input
				id="medications"
				type="text"
				class="hc-input"
				bind:value={medications}
				placeholder={copy.medicationsPlaceholder}
				aria-label={copy.medicationsAria}
			/>
		</fieldset>

		<!-- Family History -->
		<fieldset class="hc-fieldset">
			<legend>{copy.legendFamilyHistory}</legend>

			<div class="hc-profile-checkbox-grid" role="group" aria-label={copy.familyGroupAria}>
				{#each PRESET_FAMILY_HISTORY as condition}
					<label>
						<input
							type="checkbox"
							class="hc-checkbox"
							checked={selectedFamilyHistory.includes(condition)}
							onchange={() => {
								if (selectedFamilyHistory.includes(condition)) {
									selectedFamilyHistory = selectedFamilyHistory.filter((c) => c !== condition);
								} else {
									selectedFamilyHistory = [...selectedFamilyHistory, condition];
								}
							}}
						/>
						{presets.familyHistory[condition as keyof typeof presets.familyHistory] ?? condition}
					</label>
				{/each}
			</div>

			{#if legacyFamilyHistory}
				<p class="hc-profile-field-error" style="color: var(--text-secondary); margin-top: 8px; font-size: 13px;">
					{copy.familyAdditionalNotes} {legacyFamilyHistory}
				</p>
			{/if}
		</fieldset>

		<!-- Save Button -->
		<div class="hc-profile-save-row">
			<button
				type="button"
				class="btn-primary"
				onclick={handleSave}
				disabled={saveMutation.isPending || !isDirty}
			>
				{saveMutation.isPending ? copy.saving : isDirty ? copy.saveProfile : copy.saved}
			</button>
		</div>

		<!-- Data Export -->
		<fieldset class="hc-fieldset">
			<legend>{copy.legendDataExport}</legend>

			<p class="hc-profile-gdpr-text">{copy.dataExportGdprText}</p>

			<p class="hc-export-contents">{copy.dataExportContents}</p>

			<p class="hc-export-format-note">{copy.dataExportFormatNote}</p>

			{#if exportSuccess}
				<div class="hc-state hc-state-success" role="status">
					<p class="hc-state-title">{copy.exportSuccess}</p>
				</div>
			{/if}

			{#if exportErrorBackend || exportErrorFallback}
				<div class="hc-state hc-state-error" role="alert">
					<p class="hc-state-title">{exportErrorBackend ?? copy.exportErrorFallback}</p>
				</div>
			{/if}

			<div class="hc-profile-export-row">
				<button
					type="button"
					class="btn-standard"
					onclick={handleExport}
					disabled={exportLoading}
				>
					{exportLoading ? copy.exportGenerating : copy.exportDownload}
				</button>
			</div>

			<p class="hc-export-timing-note">{copy.dataExportTimingNote}</p>
		</fieldset>

		<!-- Consent History -->
		<fieldset class="hc-fieldset">
			<legend>{copy.legendConsentHistory}</legend>

			{#if consentLoading}
				<div class="hc-state hc-state-loading">
					<p class="hc-state-title">{copy.consentLoading}</p>
				</div>
			{:else if consentErrored}
				<div class="hc-state hc-state-error" role="alert">
					<p class="hc-state-title">{copy.consentError}</p>
				</div>
			{:else if consentLogs.length === 0}
				<div class="hc-state hc-state-empty">
					<p class="hc-state-title">{copy.consentEmpty}</p>
				</div>
			{:else}
				<ul class="hc-consent-timeline" aria-label={copy.consentHistoryAria}>
					{#each consentLogs as log}
						<li class="hc-consent-entry">
							<p class="hc-consent-type">{formatConsentType(log.consent_type)}</p>
							<div class="hc-consent-meta">
								<span>{formatConsentDate(log.consented_at)}</span>
								{#if log.privacy_policy_version?.trim()}
									<a
										class="hc-consent-policy-link"
										href="/privacy?version={log.privacy_policy_version}"
										aria-label="{copy.consentPolicyLinkAriaPrefix} {log.privacy_policy_version}"
										>v{log.privacy_policy_version}</a
									>
								{:else}
									<span>{copy.consentNotAvailable}</span>
								{/if}
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</fieldset>

		<!-- Delete Account -->
		<fieldset class="hc-fieldset">
			<legend>{copy.legendDeleteAccount}</legend>

			<p class="hc-delete-section-warning">{copy.deleteWarning}</p>

			<div class="hc-profile-export-row">
				<button type="button" class="btn-destructive" onclick={openDeleteDialog}>
					{copy.deleteButton}
				</button>
			</div>
		</fieldset>
	</div>
</div>

<ConfirmDialog
	bind:open={deleteDialogOpen}
	title={copy.deleteDialogTitle}
	ariaLabel={copy.deleteDialogAria}
	confirmLabel={copy.deleteDialogConfirm}
	confirmVariant="destructive"
	cancelLabel={confirmDialogCopy.cancel}
	loadingLabel={copy.deleteDialogLoading}
	canConfirm={emailMatches}
	loading={deleteLoading}
	onConfirm={handleDeleteAccount}
>
	<p id="delete-warning">{copy.deleteDialogWarning}</p>

	{#if deleteErrorBackend || deleteErrorFallback}
		<div class="hc-state hc-state-error" role="alert">
			<p class="hc-state-title">{deleteErrorBackend ?? copy.deleteErrorFallback}</p>
		</div>
	{/if}

	<div>
		<label class="hc-delete-email-label" for="delete-confirm-email">
			{copy.deleteDialogEmailLabel}
		</label>
		<input
			id="delete-confirm-email"
			class="hc-input"
			type="email"
			bind:value={confirmEmail}
			aria-describedby="delete-warning"
			autocomplete="off"
		/>
	</div>
</ConfirmDialog>
