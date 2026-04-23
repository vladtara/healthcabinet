<script lang="ts">
	import { goto } from '$app/navigation';
	import { getProfile, saveOnboardingStep, updateProfile } from '$lib/api/users';
	import type { ProfileUpdateData } from '$lib/api/users';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';
	import { LocaleToggle } from '$lib/components/ui/locale-toggle';

	const TOTAL_STEPS = 3;

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

	let currentStep = $state(1);
	let isSubmitting = $state(false);
	let isSaving = $state(false);
	let submitError = $state(false);

	// Form fields
	let age = $state<number | null>(null);
	let sex = $state<'male' | 'female' | 'other' | 'prefer_not_to_say' | null>(null);
	let heightCm = $state<number | null>(null);
	let weightKg = $state<number | null>(null);
	let selectedConditions = $state<string[]>([]);
	let medications = $state('');
	let selectedFamilyHistory = $state<string[]>([]);
	let otherCondition = $state('');

	// Validation errors keyed by field; each value is a sentinel the template
	// maps back to localized copy via `t(locale).onboarding.*`, so a locale
	// flip retranslates the error text without clearing the validation state.
	let errors = $state<Record<string, 'age' | 'height' | 'weight'>>({});

	const copy = $derived(t(localeStore.locale).onboarding);
	const presets = $derived(t(localeStore.locale).presets);

	const stepLabel = $derived(
		currentStep === 1
			? copy.stepLabelBasic
			: currentStep === 2
				? copy.stepLabelConditions
				: copy.stepLabelFamily
	);

	function errorMessage(kind: 'age' | 'height' | 'weight'): string {
		if (kind === 'age') return copy.errorAgeRange;
		if (kind === 'height') return copy.errorHeightRange;
		return copy.errorWeightRange;
	}

	// Load existing profile on mount
	$effect(() => {
		let cancelled = false;
		getProfile().then((profile) => {
			if (cancelled) return;
			if (!profile) return;
			if (profile.onboarding_step >= TOTAL_STEPS) {
				goto('/dashboard');
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
				for (const part of parts) {
					const preset = PRESET_FAMILY_HISTORY.find(
						(p) => p.toLowerCase() === part.toLowerCase()
					);
					if (preset && !selectedFamilyHistory.includes(preset)) {
						selectedFamilyHistory = [...selectedFamilyHistory, preset];
					}
				}
			}
			if (profile.onboarding_step > 1) currentStep = Math.min(profile.onboarding_step, TOTAL_STEPS);
		});
		return () => { cancelled = true; };
	});

	function toggleCondition(condition: string) {
		if (selectedConditions.includes(condition)) {
			selectedConditions = selectedConditions.filter((c) => c !== condition);
		} else {
			selectedConditions = [...selectedConditions, condition];
		}
	}

	function toggleFamilyHistory(condition: string) {
		if (selectedFamilyHistory.includes(condition)) {
			selectedFamilyHistory = selectedFamilyHistory.filter((c) => c !== condition);
		} else {
			selectedFamilyHistory = [...selectedFamilyHistory, condition];
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

	function validateStep1(): boolean {
		const errs: Record<string, 'age' | 'height' | 'weight'> = {};
		if (age !== null && (age < 1 || age > 120)) {
			errs.age = 'age';
		}
		if (heightCm !== null && (heightCm < 50 || heightCm > 300)) {
			errs.height_cm = 'height';
		}
		if (weightKg !== null && (weightKg < 10 || weightKg > 500)) {
			errs.weight_kg = 'weight';
		}
		errors = errs;
		return Object.keys(errs).length === 0;
	}

	async function goToNextStep() {
		if (isSaving) return;
		if (currentStep === 1 && !validateStep1()) return;
		isSaving = true;
		try {
			const next = currentStep + 1;
			await saveOnboardingStep(next);
			currentStep = next;
		} finally {
			isSaving = false;
		}
	}

	async function goToPrevStep() {
		if (currentStep > 1) {
			const prev = currentStep - 1;
			await saveOnboardingStep(prev);
			currentStep = prev;
		}
	}

	async function handleSubmit() {
		isSubmitting = true;
		submitError = false;
		try {
			const medList = medications
				.split(',')
				.map((m) => m.trim())
				.filter(Boolean);

			const familyHistoryText = selectedFamilyHistory.join(', ') || null;

			await saveOnboardingStep(TOTAL_STEPS);
			await updateProfile({
				age: age ?? undefined,
				sex: sex ?? undefined,
				height_cm: heightCm ?? undefined,
				weight_kg: weightKg ?? undefined,
				known_conditions: selectedConditions,
				medications: medList,
				family_history: familyHistoryText
			} satisfies ProfileUpdateData);
			await goto('/dashboard');
		} catch {
			submitError = true;
		} finally {
			isSubmitting = false;
		}
	}

	function handleAgeBlur() {
		if (age !== null && (age < 1 || age > 120)) {
			errors = { ...errors, age: 'age' };
		} else {
			const { age: _, ...rest } = errors;
			errors = rest;
		}
	}

	function handleHeightBlur() {
		if (heightCm !== null && (heightCm < 50 || heightCm > 300)) {
			errors = { ...errors, height_cm: 'height' };
		} else {
			const { height_cm: _, ...rest } = errors;
			errors = rest;
		}
	}

	function handleWeightBlur() {
		if (weightKg !== null && (weightKg < 10 || weightKg > 500)) {
			errors = { ...errors, weight_kg: 'weight' };
		} else {
			const { weight_kg: _, ...rest } = errors;
			errors = rest;
		}
	}
</script>

<main class="hc-onboarding-page">
	<div class="hc-wizard-dialog">
		<div class="hc-wizard-header">
			<span><span aria-hidden="true">📋</span> {copy.header}</span>
			<LocaleToggle class="hc-wizard-locale" />
		</div>

		<!-- Step indicator -->
		<div class="hc-wizard-step-indicator" aria-hidden="true">
			{#each Array(TOTAL_STEPS) as _, i}
				{@const stepNum = i + 1}
				<div
					class="hc-wizard-step-circle {stepNum < currentStep ? 'done' : stepNum === currentStep ? 'current' : ''}"
				>
					{#if stepNum < currentStep}✓{:else}{stepNum}{/if}
				</div>
				{#if i < TOTAL_STEPS - 1}
					<div class="hc-wizard-step-line {stepNum < currentStep ? 'done' : ''}"></div>
				{/if}
			{/each}
		</div>
		<div
			class="hc-wizard-step-label"
			role="progressbar"
			aria-valuenow={currentStep}
			aria-valuemin={1}
			aria-valuemax={TOTAL_STEPS}
			aria-label={copy.progressAria}
		>
			{copy.stepIndicatorPrefix} {currentStep} {copy.stepIndicatorMid} {TOTAL_STEPS} — {stepLabel}
		</div>

		<div class="hc-wizard-body">
			<!-- Step 1: Basic info -->
			{#if currentStep === 1}
				<div class="hc-profile-inline-fields">
					<div class="hc-profile-field-group" style="flex:1">
						<label class="hc-label" for="ob-age">{copy.ageLabel}</label>
						<input
							id="ob-age"
							type="number"
							class="hc-input"
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

					<div class="hc-profile-field-group" style="flex:1">
						<label class="hc-label" for="ob-sex">{copy.sexLabel}</label>
						<select id="ob-sex" class="hc-input" bind:value={sex}>
							<option value={null} disabled selected>{presets.sex.select}</option>
							<option value="female">{presets.sex.female}</option>
							<option value="male">{presets.sex.male}</option>
							<option value="other">{presets.sex.other}</option>
							<option value="prefer_not_to_say">{presets.sex.prefer_not_to_say}</option>
						</select>
					</div>

					<div class="hc-profile-field-group" style="flex:1">
						<label class="hc-label" for="ob-height">{copy.heightLabel}</label>
						<input
							id="ob-height"
							type="number"
							class="hc-input"
							min="50"
							max="300"
							step="0.1"
							bind:value={heightCm}
							onblur={handleHeightBlur}
							aria-invalid={!!errors.height_cm}
							aria-describedby={errors.height_cm ? 'height-error' : undefined}
						/>
						{#if errors.height_cm}
							<p id="height-error" class="hc-profile-field-error" role="alert">{errorMessage(errors.height_cm)}</p>
						{/if}
					</div>

					<div class="hc-profile-field-group" style="flex:1">
						<label class="hc-label" for="ob-weight">{copy.weightLabel}</label>
						<input
							id="ob-weight"
							type="number"
							class="hc-input"
							min="10"
							max="500"
							step="0.1"
							bind:value={weightKg}
							onblur={handleWeightBlur}
							aria-invalid={!!errors.weight_kg}
							aria-describedby={errors.weight_kg ? 'weight-error' : undefined}
						/>
						{#if errors.weight_kg}
							<p id="weight-error" class="hc-profile-field-error" role="alert">{errorMessage(errors.weight_kg)}</p>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Step 2: Health conditions -->
			{#if currentStep === 2}
				<div class="hc-wizard-section-label">{copy.conditionsSectionLabel}</div>
				<div class="hc-wizard-section-desc">{copy.conditionsSectionDesc}</div>
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

				<div class="hc-profile-add-condition" style="margin-top:12px">
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
					<div class="hc-profile-custom-conditions" style="margin-top:8px">
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

				<div class="hc-wizard-section-label" style="margin-top:18px">{copy.medicationsSectionLabel}</div>
				<input
					type="text"
					class="hc-input"
					bind:value={medications}
					placeholder={copy.medicationsPlaceholder}
					aria-label={copy.medicationsAria}
				/>
			{/if}

			<!-- Step 3: Family history -->
			{#if currentStep === 3}
				<div class="hc-wizard-section-desc">{copy.familySectionDesc}</div>
				<div class="hc-profile-checkbox-grid" role="group" aria-label={copy.familyGroupAria}>
					{#each PRESET_FAMILY_HISTORY as condition}
						<label>
							<input
								type="checkbox"
								class="hc-checkbox"
								checked={selectedFamilyHistory.includes(condition)}
								onchange={() => toggleFamilyHistory(condition)}
							/>
							{presets.familyHistory[condition as keyof typeof presets.familyHistory] ?? condition}
						</label>
					{/each}
				</div>
			{/if}

			{#if submitError}
				<p role="alert" class="hc-profile-field-error" style="margin-top:12px">{copy.submitError}</p>
			{/if}
		</div>

		<!-- Navigation buttons -->
		<div class="hc-wizard-footer">
			{#if currentStep > 1}
				<button type="button" class="btn-standard" onclick={goToPrevStep}>{copy.back}</button>
			{:else}
				<div></div>
			{/if}

			{#if currentStep < TOTAL_STEPS}
				<button type="button" class="btn-primary" onclick={goToNextStep} disabled={isSaving}>
					{isSaving ? copy.continueSaving : copy.continue}
				</button>
			{:else}
				<button type="button" class="btn-primary" onclick={handleSubmit} disabled={isSubmitting}>
					{isSubmitting ? copy.completing : copy.complete}
				</button>
			{/if}
		</div>
	</div>
</main>
