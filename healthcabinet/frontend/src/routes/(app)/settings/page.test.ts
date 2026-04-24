import { fireEvent, waitFor } from '@testing-library/svelte';
import axe from 'axe-core';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { renderComponent } from '$lib/test-utils/render';
import SettingsPage from './+page.svelte';

const mockMutate = vi.fn();
let mockIsPending = false;

vi.mock('$lib/api/users', () => ({
	getProfile: vi.fn().mockResolvedValue(null),
	updateProfile: vi.fn().mockResolvedValue(undefined),
	exportMyData: vi.fn().mockResolvedValue(undefined),
	deleteMyAccount: vi.fn().mockResolvedValue(undefined),
	getConsentHistory: vi.fn().mockResolvedValue([
		{
			id: 'cl-1',
			consent_type: 'health_data_processing',
			privacy_policy_version: '1.0',
			consented_at: '2026-01-15T10:30:00Z'
		}
	])
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn(),
	beforeNavigate: vi.fn()
}));

vi.mock('$lib/stores/auth.svelte', () => ({
	authStore: {
		user: { id: 'u-1', email: 'test@example.com', role: 'user', tier: 'free' },
		isAuthenticated: true,
		logout: vi.fn().mockResolvedValue(undefined)
	}
}));

vi.mock('@tanstack/svelte-query', () => ({
	createMutation: vi.fn(() => ({
		subscribe(run: (value: { mutate: ReturnType<typeof vi.fn>; isPending: boolean }) => void) {
			run({ mutate: mockMutate, isPending: mockIsPending });
			return () => {};
		}
	}))
}));

import { getConsentHistory, getProfile } from '$lib/api/users';
import { localeStore } from '$lib/stores/locale.svelte';

describe('Settings page', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockIsPending = false;
		vi.mocked(getProfile).mockResolvedValue(null);
		vi.mocked(getConsentHistory).mockResolvedValue([
			{
				id: 'cl-1',
				consent_type: 'health_data_processing',
				privacy_policy_version: '1.0',
				consented_at: '2026-01-15T10:30:00Z'
			}
		]);
		window.localStorage.clear();
		localeStore._resetForTests();
	});

	afterEach(() => {
		window.localStorage.clear();
		localeStore._resetForTests();
	});

	test('page title renders with correct class', () => {
		const { getByRole } = renderComponent(SettingsPage);
		const heading = getByRole('heading', { level: 1 });
		expect(heading).toHaveTextContent('Medical Profile');
		expect(heading).toHaveClass('hc-profile-title');
	});

	test('page container uses hc-profile-page class', () => {
		const { container } = renderComponent(SettingsPage);
		expect(container.querySelector('.hc-profile-page')).toBeInTheDocument();
	});

	test('fieldsets render with hc-fieldset class and correct legends', () => {
		const { container } = renderComponent(SettingsPage);
		const fieldsets = container.querySelectorAll('fieldset.hc-fieldset');
		const legends = container.querySelectorAll('fieldset.hc-fieldset > legend');
		const legendTexts = Array.from(legends).map((l) => l.textContent?.trim());
		expect(legendTexts).toContain('Basic Information');
		expect(legendTexts).toContain('Health Conditions');
		expect(legendTexts).toContain('Current Medications');
		expect(legendTexts).toContain('Family History');
		expect(legendTexts).toContain('Data Export');
		expect(fieldsets.length).toBeGreaterThanOrEqual(5);
	});

	test('form fields render with correct CSS classes', () => {
		const { getByLabelText, container } = renderComponent(SettingsPage);

		expect(getByLabelText(/^age$/i)).toHaveClass('hc-input');
		expect(getByLabelText(/height/i)).toHaveClass('hc-input');
		expect(getByLabelText(/weight/i)).toHaveClass('hc-input');
		expect(getByLabelText(/medications/i)).toHaveClass('hc-input');

		// Labels use hc-label
		const labels = container.querySelectorAll('label.hc-label');
		expect(labels.length).toBeGreaterThanOrEqual(3);
	});

	test('sex select dropdown renders with correct options', () => {
		const { getByLabelText } = renderComponent(SettingsPage);
		const select = getByLabelText(/sex/i);
		expect(select).toBeInTheDocument();
		expect(select.tagName).toBe('SELECT');
		const options = select.querySelectorAll('option');
		// "Select..." placeholder + 4 real options
		expect(options.length).toBe(5);
	});

	test('condition checkboxes render in grid and toggle on click', async () => {
		const { container } = renderComponent(SettingsPage);
		const checkboxGrid = container.querySelector('.hc-profile-checkbox-grid');
		expect(checkboxGrid).toBeInTheDocument();

		const checkboxes = checkboxGrid?.querySelectorAll('input[type="checkbox"].hc-checkbox');
		expect(checkboxes?.length).toBe(12);

		// Initially none are checked
		const checked = Array.from(checkboxes ?? []).filter((cb) => (cb as HTMLInputElement).checked);
		expect(checked.length).toBe(0);

		// Click the first checkbox (Type 2 Diabetes)
		const firstCheckbox = checkboxes?.[0] as HTMLInputElement;
		await fireEvent.click(firstCheckbox);

		await waitFor(() => {
			expect(firstCheckbox.checked).toBe(true);
		});
	});

	test('save button has btn-primary class', async () => {
		const { getByRole } = renderComponent(SettingsPage);
		await waitFor(() => {
			const saveBtn = getByRole('button', { name: /saved/i });
			expect(saveBtn).toHaveClass('btn-primary');
		});
	});

	test('add button has btn-standard class', () => {
		const { getByRole } = renderComponent(SettingsPage);
		const addBtn = getByRole('button', { name: /^add$/i });
		expect(addBtn).toHaveClass('btn-standard');
	});

	test('export button has btn-standard class', () => {
		const { getByRole } = renderComponent(SettingsPage);
		const exportBtn = getByRole('button', { name: /download my data/i });
		expect(exportBtn).toHaveClass('btn-standard');
	});

	test('family history renders as checkbox grid with presets', () => {
		const { container } = renderComponent(SettingsPage);
		const familyFieldset = Array.from(container.querySelectorAll('fieldset.hc-fieldset')).find(
			(fs) => fs.querySelector('legend')?.textContent?.trim() === 'Family History'
		);
		expect(familyFieldset).toBeInTheDocument();

		const checkboxes = familyFieldset?.querySelectorAll(
			'.hc-profile-checkbox-grid input[type="checkbox"]'
		);
		expect(checkboxes?.length).toBe(6);
		expect(familyFieldset?.textContent).toContain('High Blood Pressure');
		expect(familyFieldset?.textContent).toContain('Autoimmune Disease');
	});

	test('family history round-trips newer preset values and localizes them', async () => {
		vi.mocked(getProfile).mockResolvedValueOnce({
			id: 'profile-1',
			user_id: 'u-1',
			age: 30,
			sex: 'female',
			height_cm: 170,
			weight_kg: 65,
			known_conditions: [],
			medications: [],
			family_history: 'High Blood Pressure, Autoimmune Disease',
			onboarding_step: 3,
			created_at: '2026-01-01T00:00:00Z',
			updated_at: '2026-01-01T00:00:00Z'
		} as never);

		const { container } = renderComponent(SettingsPage);
		const familyFieldset = Array.from(container.querySelectorAll('fieldset.hc-fieldset')).find(
			(fs) => fs.querySelector('legend')?.textContent?.trim() === 'Family History'
		);

		await waitFor(() => {
			const checked = familyFieldset?.querySelectorAll(
				'.hc-profile-checkbox-grid input[type="checkbox"]:checked'
			);
			expect(checked?.length).toBe(2);
			expect(familyFieldset?.textContent).toContain('High Blood Pressure');
			expect(familyFieldset?.textContent).toContain('Autoimmune Disease');
		});

		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		const checkedUk = familyFieldset?.querySelectorAll(
			'.hc-profile-checkbox-grid input[type="checkbox"]:checked'
		);
		expect(checkedUk?.length).toBe(2);
		expect(familyFieldset?.textContent).toContain('Високий кровʼяний тиск');
		expect(familyFieldset?.textContent).toContain('Автоімунне захворювання');
	});

	test('validation errors render with hc-profile-field-error class and role=alert', async () => {
		const { getByLabelText, container } = renderComponent(SettingsPage);
		const ageInput = getByLabelText(/^age$/i);

		// Set invalid age
		await fireEvent.input(ageInput, { target: { value: '200' } });
		await fireEvent.blur(ageInput);

		await waitFor(() => {
			const errorEl = container.querySelector('.hc-profile-field-error');
			expect(errorEl).toBeInTheDocument();
			expect(errorEl).toHaveAttribute('role', 'alert');
			expect(errorEl).toHaveTextContent('Age must be between 1 and 120');
		});
	});

	test('GDPR text renders with correct class', () => {
		const { container } = renderComponent(SettingsPage);
		const gdprText = container.querySelector('.hc-profile-gdpr-text');
		expect(gdprText).toBeInTheDocument();
		expect(gdprText?.textContent).toContain('GDPR Article 20');
	});

	test('profile data loads from API into form fields', async () => {
		vi.mocked(getProfile).mockResolvedValue({
			id: 'p1',
			user_id: 'u1',
			age: 34,
			sex: 'female',
			height_cm: 165,
			weight_kg: 58,
			known_conditions: ["Hashimoto's", 'Anemia'],
			medications: ['Levothyroxine 50mcg'],
			family_history: 'Mother: hypertension',
			onboarding_step: 3,
			created_at: '2026-01-01T00:00:00Z',
			updated_at: '2026-01-01T00:00:00Z'
		});

		const { getByLabelText, container } = renderComponent(SettingsPage);

		await waitFor(() => {
			expect(getByLabelText(/^age$/i)).toHaveValue(34);
			expect(getByLabelText(/height/i)).toHaveValue(165);
			expect(getByLabelText(/weight/i)).toHaveValue(58);
		});

		// Check conditions are selected via checkboxes
		await waitFor(() => {
			const checkedBoxes = container.querySelectorAll(
				'.hc-profile-checkbox-grid input[type="checkbox"]:checked'
			);
			expect(checkedBoxes.length).toBe(2);
		});
	});

	test('no shadcn-svelte primitive imports exist in page source', async () => {
		// Story 12-1 removed shadcn Button/Input/Label/Textarea in favor of native HTML + 98.css.
		// 98.css component primitives (slide-over, confirm-dialog, etc.) under $lib/components/ui/
		// are allowed — they're part of the redesign's shared chrome.
		// Regexes require the import path to terminate with `/` (subpath) or `'` (folder index)
		// so `ui/button` doesn't accidentally match a future `ui/button-group`.
		const pageSource = await import('./+page.svelte?raw');
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/button['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/input['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/label['/]/);
		expect(pageSource.default).not.toMatch(/from '\$lib\/components\/ui\/textarea['/]/);
	});

	test('sections container uses hc-profile-sections class', () => {
		const { container } = renderComponent(SettingsPage);
		const sections = container.querySelector('.hc-profile-sections');
		expect(sections).toBeInTheDocument();
	});

	test('save row uses hc-profile-save-row class', () => {
		const { container } = renderComponent(SettingsPage);
		const saveRow = container.querySelector('.hc-profile-save-row');
		expect(saveRow).toBeInTheDocument();
	});

	test('export success banner appears after clicking Download My Data', async () => {
		const { getByRole } = renderComponent(SettingsPage);
		const exportBtn = getByRole('button', { name: /download my data/i });
		await fireEvent.click(exportBtn);

		await waitFor(() => {
			const exportFieldset = exportBtn.closest('fieldset');
			const successBanner = exportFieldset?.querySelector('.hc-state-success');
			expect(successBanner).toBeInTheDocument();
			expect(successBanner?.textContent).toContain('Export downloaded');
		});
	});

	test('export error banner appears when export fails', async () => {
		const { exportMyData } = await import('$lib/api/users');
		vi.mocked(exportMyData).mockRejectedValueOnce({
			detail: 'Export generation failed'
		});

		const { getByRole } = renderComponent(SettingsPage);
		const exportBtn = getByRole('button', { name: /download my data/i });
		await fireEvent.click(exportBtn);

		await waitFor(() => {
			const exportFieldset = exportBtn.closest('fieldset');
			const errorBanner = exportFieldset?.querySelector('.hc-state-error');
			expect(errorBanner).toBeInTheDocument();
			expect(errorBanner?.textContent).toContain('Export generation failed');
		});
	});

	// --- Unsaved Changes & Save Button State ---

	test('save button shows "Saved" and is disabled when form is clean', async () => {
		const { getByRole } = renderComponent(SettingsPage);

		await waitFor(() => {
			const saveBtn = getByRole('button', { name: /saved/i });
			expect(saveBtn).toBeInTheDocument();
			expect(saveBtn).toBeDisabled();
		});
	});

	test('save button shows "Save Profile" and is enabled after a field change', async () => {
		const { getByLabelText, getByRole } = renderComponent(SettingsPage);

		// Wait for baseline to be set
		await waitFor(() => {
			expect(getByRole('button', { name: /saved/i })).toBeDisabled();
		});

		// Change a field to make form dirty
		const ageInput = getByLabelText(/^age$/i);
		await fireEvent.input(ageInput, { target: { value: '30' } });

		await waitFor(() => {
			const saveBtn = getByRole('button', { name: /save profile/i });
			expect(saveBtn).toBeInTheDocument();
			expect(saveBtn).not.toBeDisabled();
		});
	});

	test('beforeNavigate is registered with a callback function', async () => {
		const { beforeNavigate } = await import('$app/navigation');
		renderComponent(SettingsPage);
		expect(beforeNavigate).toHaveBeenCalledWith(expect.any(Function));
	});

	// --- Data Export Section ---

	test('export section has contents summary', () => {
		const { container } = renderComponent(SettingsPage);
		const contents = container.querySelector('.hc-export-contents');
		expect(contents).toBeInTheDocument();
		expect(contents?.textContent).toContain('uploaded documents');
		expect(contents?.textContent).toContain('health values');
		expect(contents?.textContent).toContain('consent history');
	});

	test('export section has format note', () => {
		const { container } = renderComponent(SettingsPage);
		const formatNote = container.querySelector('.hc-export-format-note');
		expect(formatNote).toBeInTheDocument();
		expect(formatNote?.textContent).toContain('ZIP file');
		expect(formatNote?.textContent).toContain('machine-readable');
	});

	test('export section has timing note', () => {
		const { container } = renderComponent(SettingsPage);
		const timingNote = container.querySelector('.hc-export-timing-note');
		expect(timingNote).toBeInTheDocument();
		expect(timingNote?.textContent).toContain('few moments');
	});

	// --- Consent History Timeline ---

	test('consent history fieldset renders with correct legend', async () => {
		const { container } = renderComponent(SettingsPage);
		await waitFor(() => {
			const legends = container.querySelectorAll('fieldset.hc-fieldset > legend');
			const legendTexts = Array.from(legends).map((l) => l.textContent?.trim());
			expect(legendTexts).toContain('Consent History');
		});
	});

	test('consent timeline renders entries with formatted data', async () => {
		const { container } = renderComponent(SettingsPage);

		await waitFor(() => {
			const entries = container.querySelectorAll('.hc-consent-entry');
			expect(entries.length).toBe(1);
		});

		const typeEl = container.querySelector('.hc-consent-type');
		expect(typeEl).toHaveTextContent('Health Data Processing');

		const metaEl = container.querySelector('.hc-consent-meta');
		const expectedDate = new Intl.DateTimeFormat('en-GB', {
			day: '2-digit',
			month: 'short',
			year: 'numeric',
			timeZone: 'UTC'
		}).format(new Date('2026-01-15T10:30:00Z'));
		expect(metaEl?.textContent).toContain(expectedDate);
		expect(metaEl?.textContent).toContain('10:30 UTC');

		const policyLink = container.querySelector('.hc-consent-policy-link');
		expect(policyLink).toBeInTheDocument();
		expect(policyLink).toHaveTextContent('v1.0');
		expect(policyLink).toHaveAttribute('href', '/privacy?version=1.0');
		expect(policyLink).toHaveAttribute('aria-label', 'Privacy policy version 1.0');
	});

	test('consent history policy link targets a live privacy route (Story 6-3 AC2)', async () => {
		// Regression gate: prior to Story 6-3 the /privacy?version= link was a dead
		// URL (no route existed). If the /privacy +page.svelte is deleted, this
		// import throws and the test fails — catching the most common dead-link
		// regression (outright removal or path-relative move).
		//
		// LIMITATION: this is a FILE-EXISTENCE check, NOT a route-registration
		// check. A rename that preserves the href (e.g. `(marketing)/privacy/`
		// → `(marketing)/legal/privacy/` without updating `settings/+page.svelte`)
		// would still import successfully via this relative path if a stub file
		// is kept, even while the route 404s in production. The authoritative
		// route-registration test is a Playwright e2e that hits `/privacy` on a
		// live dev server — tracked in deferred-work.md.
		const privacyPageModule = await import('../../(marketing)/privacy/+page.svelte');
		expect(privacyPageModule.default).toBeDefined();

		const { container } = renderComponent(SettingsPage);
		await waitFor(() => {
			const policyLink = container.querySelector<HTMLAnchorElement>('.hc-consent-policy-link');
			expect(policyLink).not.toBeNull();
			const href = policyLink!.getAttribute('href') ?? '';
			// Assert exact path (not just startsWith) so a typo in the route name
			// — e.g. `/privacies?version=` or `/privacy/?version=` — fails here.
			expect(href).toMatch(/^\/privacy\?version=[^&]+$/);
		});
	});

	test('consent timeline is a semantic list', async () => {
		const { container } = renderComponent(SettingsPage);

		await waitFor(() => {
			const ul = container.querySelector('ul.hc-consent-timeline');
			expect(ul).toBeInTheDocument();
			const listItems = ul?.querySelectorAll('li.hc-consent-entry');
			expect(listItems?.length).toBe(1);
		});
	});

	test('consent history shows loading state', () => {
		vi.mocked(getConsentHistory).mockReturnValue(new Promise(() => {}));
		const { container } = renderComponent(SettingsPage);
		const loadingEl = container.querySelector('.hc-state-loading');
		expect(loadingEl).toBeInTheDocument();
		expect(loadingEl?.textContent).toContain('Loading consent history');
	});

	test('consent history shows error state on fetch failure', async () => {
		vi.mocked(getConsentHistory).mockRejectedValue(new Error('Network error'));
		const { container } = renderComponent(SettingsPage);

		await waitFor(() => {
			// Find the Consent History fieldset by its legend text
			const fieldsets = container.querySelectorAll('fieldset.hc-fieldset');
			const consentFieldset = Array.from(fieldsets).find(
				(fs) => fs.querySelector('legend')?.textContent?.trim() === 'Consent History'
			);
			const errorEl = consentFieldset?.querySelector('.hc-state-error');
			expect(errorEl).toBeInTheDocument();
			expect(errorEl).toHaveAttribute('role', 'alert');
			expect(errorEl?.textContent).toContain('Failed to load consent history');
		});
	});

	test('consent history shows empty state when no entries', async () => {
		vi.mocked(getConsentHistory).mockResolvedValue([]);
		const { container } = renderComponent(SettingsPage);

		await waitFor(() => {
			const fieldsets = container.querySelectorAll('fieldset.hc-fieldset');
			const consentFieldset = Array.from(fieldsets).find(
				(fs) => fs.querySelector('legend')?.textContent?.trim() === 'Consent History'
			);
			const emptyEl = consentFieldset?.querySelector('.hc-state-empty');
			expect(emptyEl).toBeInTheDocument();
			expect(emptyEl?.textContent).toContain('No consent records found');
		});
	});

	// --- Account Deletion ---

	test('delete account fieldset renders with legend and btn-destructive button', () => {
		const { container, getByRole } = renderComponent(SettingsPage);
		const legends = container.querySelectorAll('fieldset.hc-fieldset > legend');
		const legendTexts = Array.from(legends).map((l) => l.textContent?.trim());
		expect(legendTexts).toContain('Delete Account');

		const deleteBtn = getByRole('button', { name: /delete my account/i });
		expect(deleteBtn).toHaveClass('btn-destructive');
	});

	test('delete dialog opens on button click', async () => {
		const { getByRole, container } = renderComponent(SettingsPage);
		const deleteBtn = getByRole('button', { name: /delete my account/i });
		await fireEvent.click(deleteBtn);

		await waitFor(() => {
			const dialog = container.querySelector('[role="dialog"]');
			expect(dialog).toBeInTheDocument();
			expect(dialog).toHaveAttribute('aria-modal', 'true');
			expect(dialog).toHaveAttribute('aria-label', 'Account deletion confirmation');
		});
	});

	test('delete confirm button disabled until email matches', async () => {
		const { getByRole, getByLabelText, container } = renderComponent(SettingsPage);
		const openBtn = getByRole('button', { name: /delete my account/i });
		await fireEvent.click(openBtn);

		await waitFor(() => {
			const dialog = container.querySelector('[role="dialog"]');
			expect(dialog).toBeInTheDocument();
		});

		// Confirm button in dialog should be disabled initially
		const dialogConfirmBtn = container.querySelector(
			'[role="dialog"] .btn-destructive'
		) as HTMLButtonElement;
		expect(dialogConfirmBtn).toBeDisabled();

		// Type matching email
		const emailInput = getByLabelText(/type your email/i);
		await fireEvent.input(emailInput, { target: { value: 'test@example.com' } });

		await waitFor(() => {
			expect(dialogConfirmBtn).not.toBeDisabled();
		});
	});

	test('delete dialog closes on Cancel', async () => {
		const { getByRole, container } = renderComponent(SettingsPage);
		await fireEvent.click(getByRole('button', { name: /delete my account/i }));

		await waitFor(() => {
			expect(container.querySelector('[role="dialog"]')).toBeInTheDocument();
		});

		const cancelBtn = container.querySelector('[role="dialog"] .btn-standard');
		expect(cancelBtn).toBeInTheDocument();
		await fireEvent.click(cancelBtn!);

		await waitFor(() => {
			expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
		});
	});

	test('delete error state shows in dialog', async () => {
		const { deleteMyAccount } = await import('$lib/api/users');
		vi.mocked(deleteMyAccount).mockRejectedValueOnce({ detail: 'Deletion failed' });

		const { getByRole, getByLabelText, container } = renderComponent(SettingsPage);
		await fireEvent.click(getByRole('button', { name: /delete my account/i }));

		await waitFor(() => {
			expect(container.querySelector('[role="dialog"]')).toBeInTheDocument();
		});

		// Type correct email and click delete
		await fireEvent.input(getByLabelText(/type your email/i), {
			target: { value: 'test@example.com' }
		});
		await waitFor(() => {
			const confirmBtn = container.querySelector(
				'[role="dialog"] .btn-destructive'
			) as HTMLButtonElement;
			expect(confirmBtn).not.toBeDisabled();
		});

		const confirmBtn = container.querySelector(
			'[role="dialog"] .btn-destructive'
		) as HTMLButtonElement;
		await fireEvent.click(confirmBtn);

		await waitFor(() => {
			const errorEl = container.querySelector('[role="dialog"] .hc-state-error');
			expect(errorEl).toBeInTheDocument();
			expect(errorEl).toHaveAttribute('role', 'alert');
			expect(errorEl?.textContent).toContain('Deletion failed');
		});
	});

	test('successful deletion calls logout and redirects', async () => {
		const { goto } = await import('$app/navigation');
		const { authStore } = await import('$lib/stores/auth.svelte');

		const { getByRole, getByLabelText, container } = renderComponent(SettingsPage);
		await fireEvent.click(getByRole('button', { name: /delete my account/i }));

		await waitFor(() => {
			expect(container.querySelector('[role="dialog"]')).toBeInTheDocument();
		});

		await fireEvent.input(getByLabelText(/type your email/i), {
			target: { value: 'test@example.com' }
		});

		await waitFor(() => {
			const confirmBtn = container.querySelector(
				'[role="dialog"] .btn-destructive'
			) as HTMLButtonElement;
			expect(confirmBtn).not.toBeDisabled();
		});

		const confirmBtn = container.querySelector(
			'[role="dialog"] .btn-destructive'
		) as HTMLButtonElement;
		await fireEvent.click(confirmBtn);

		await waitFor(() => {
			expect(authStore.logout).toHaveBeenCalled();
			expect(goto).toHaveBeenCalledWith('/?deleted=true');
		});
	});

	test('axe accessibility audit passes', async () => {
		const { container } = renderComponent(SettingsPage);
		const results = await axe.run(container);
		expect(results.violations).toEqual([]);
	});

	// ── Story 15.7 — localization ─────────────────────────────────────────────

	test('switching to uk rerenders title, legends, and save button in Ukrainian', async () => {
		const { container, getByRole } = renderComponent(SettingsPage);

		// Baseline — English
		const heading = getByRole('heading', { level: 1 });
		expect(heading).toHaveTextContent('Medical Profile');
		const legendsEn = Array.from(container.querySelectorAll('fieldset.hc-fieldset > legend')).map(
			(l) => l.textContent?.trim()
		);
		expect(legendsEn).toContain('Basic Information');
		expect(legendsEn).toContain('Data Export');

		// Flip to uk
		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		expect(heading).toHaveTextContent('Медичний профіль');
		const legendsUk = Array.from(container.querySelectorAll('fieldset.hc-fieldset > legend')).map(
			(l) => l.textContent?.trim()
		);
		expect(legendsUk).toContain('Основна інформація');
		expect(legendsUk).toContain('Експорт даних');
		expect(legendsUk).toContain('Видалення акаунту');

		// Save button (initially in 'Saved' idle state, localized)
		const saveBtn = container.querySelector('.hc-profile-save-row .btn-primary');
		expect(saveBtn?.textContent?.trim()).toBe('Збережено');
	});

	test('dirty-state survives locale flip and Save-button label retranslates', async () => {
		// Seed with a saved profile so baseline is captured after mount.
		vi.mocked(getProfile).mockResolvedValueOnce({
			id: 'profile-1',
			user_id: 'u-1',
			age: 30,
			sex: 'female',
			height_cm: 170,
			weight_kg: 65,
			known_conditions: [],
			medications: [],
			family_history: null,
			onboarding_step: 3,
			created_at: '2026-01-01T00:00:00Z',
			updated_at: '2026-01-01T00:00:00Z'
		} as never);

		const { container } = renderComponent(SettingsPage);
		await waitFor(() => {
			const ageInput = container.querySelector('#age') as HTMLInputElement;
			expect(ageInput.value).toBe('30');
		});

		const ageInput = container.querySelector('#age') as HTMLInputElement;
		await fireEvent.input(ageInput, { target: { value: '31' } });

		await waitFor(() => {
			const saveBtn = container.querySelector(
				'.hc-profile-save-row .btn-primary'
			) as HTMLButtonElement;
			expect(saveBtn.textContent?.trim()).toBe('Save Profile');
			expect(saveBtn.disabled).toBe(false);
		});

		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		const saveBtn = container.querySelector(
			'.hc-profile-save-row .btn-primary'
		) as HTMLButtonElement;
		expect(saveBtn.textContent?.trim()).toBe('Зберегти профіль');
		expect(saveBtn.disabled).toBe(false);
	});

	test('preset condition labels render in Ukrainian while payload stays English', async () => {
		const { container } = renderComponent(SettingsPage);
		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		const grid = container.querySelector('.hc-profile-checkbox-grid')!;
		expect(grid.textContent).toContain('Діабет 2 типу');
		expect(grid.textContent).toContain('Гіпертонія');
		expect(grid.textContent).not.toContain('Type 2 Diabetes');

		// Click the first checkbox — its backing value should remain canonical English.
		const firstCb = grid.querySelector('input[type="checkbox"]') as HTMLInputElement;
		await fireEvent.click(firstCb);
		expect(firstCb.checked).toBe(true);
		// The hidden contract: stored condition strings remain English.
		// We assert this indirectly by toggling back to English and confirming the
		// same checkbox stays checked and its English label reappears in the same position.
		localeStore.setLocale('en');
		await new Promise((r) => setTimeout(r, 0));
		const refreshedFirst = grid.querySelector('input[type="checkbox"]') as HTMLInputElement;
		expect(refreshedFirst.checked).toBe(true);
		expect(grid.textContent).toContain('Type 2 Diabetes');
	});

	test('ConfirmDialog uses localized title, confirm, cancel, and loading labels', async () => {
		const { container, getByRole } = renderComponent(SettingsPage);
		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		// Open the delete confirmation dialog.
		const deleteBtn = getByRole('button', { name: /видалити мій акаунт/i });
		await fireEvent.click(deleteBtn);

		await waitFor(() => {
			const dialog = container.querySelector('[role="dialog"]');
			expect(dialog).toBeInTheDocument();
			expect(dialog?.textContent).toContain('Видалення акаунту');
			expect(dialog?.textContent).toContain('Введіть свій email для підтвердження');
			// Cancel button from confirm-dialog defaults (localized)
			const cancelBtn = dialog?.querySelector('button.btn-standard');
			expect(cancelBtn?.textContent?.trim()).toBe('Скасувати');
		});
	});

	test('consent timeline localizes consent labels and date formatting under uk', async () => {
		const { container } = renderComponent(SettingsPage);

		await waitFor(() => {
			expect(container.querySelector('.hc-consent-entry')).toBeInTheDocument();
		});

		localeStore.setLocale('uk');
		await new Promise((r) => setTimeout(r, 0));

		const expectedDate = new Intl.DateTimeFormat('uk-UA', {
			day: '2-digit',
			month: 'short',
			year: 'numeric',
			timeZone: 'UTC'
		}).format(new Date('2026-01-15T10:30:00Z'));

		expect(container.querySelector('.hc-consent-type')).toHaveTextContent('Обробка медичних даних');
		expect(container.querySelector('.hc-consent-meta')?.textContent).toContain(expectedDate);
		expect(container.querySelector('.hc-consent-meta')?.textContent).toContain('10:30 UTC');
		expect(container.querySelector('.hc-consent-policy-link')).toHaveAttribute(
			'aria-label',
			'Версія політики конфіденційності 1.0'
		);
	});
});
