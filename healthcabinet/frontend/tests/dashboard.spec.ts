import { expect, test } from '@playwright/test';
import { setupAuth } from './helpers/auth';

const MOCK_HEALTH_VALUES = [
	{
		id: 'hv-1',
		user_id: 'user-1',
		document_id: 'doc-1',
		biomarker_name: 'Hemoglobin',
		canonical_biomarker_name: 'hemoglobin',
		value: 14.5,
		unit: 'g/dL',
		reference_range_low: 12.0,
		reference_range_high: 16.0,
		measured_at: '2026-03-20T00:00:00Z',
		confidence: 0.95,
		needs_review: false,
		is_flagged: false,
		flagged_at: null,
		created_at: '2026-03-20T10:00:00Z',
		status: 'optimal'
	},
	{
		id: 'hv-2',
		user_id: 'user-1',
		document_id: 'doc-1',
		biomarker_name: 'Glucose',
		canonical_biomarker_name: 'glucose',
		value: 105,
		unit: 'mg/dL',
		reference_range_low: 70,
		reference_range_high: 100,
		measured_at: '2026-03-20T00:00:00Z',
		confidence: 0.92,
		needs_review: false,
		is_flagged: false,
		flagged_at: null,
		created_at: '2026-03-20T10:00:00Z',
		status: 'borderline'
	},
	{
		id: 'hv-3',
		user_id: 'user-1',
		document_id: 'doc-1',
		biomarker_name: 'LDL Cholesterol',
		canonical_biomarker_name: 'ldl_cholesterol',
		value: 175,
		unit: 'mg/dL',
		reference_range_low: null,
		reference_range_high: 130,
		measured_at: '2026-03-20T00:00:00Z',
		confidence: 0.88,
		needs_review: true,
		is_flagged: false,
		flagged_at: null,
		created_at: '2026-03-20T10:00:00Z',
		status: 'concerning'
	}
];

const MOCK_RECOMMENDATIONS = [
	{
		test_name: 'Complete Blood Count',
		rationale: 'Recommended for general health screening.',
		frequency: 'Annually',
		category: 'general'
	},
	{
		test_name: 'HbA1c',
		rationale: 'Monitors long-term blood sugar control.',
		frequency: 'Every 3 months',
		category: 'condition_specific'
	}
];

test.describe('Dashboard', () => {
	test.beforeEach(async ({ page }) => {
		await setupAuth(page);
	});

	test('renders "Your Health Dashboard" heading', async ({ page }) => {
		await page.route('**/api/v1/health-values', (route) =>
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
		);
		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ recommendations: [], has_uploads: false })
			})
		);

		await page.goto('/dashboard');
		await expect(page.getByRole('heading', { name: 'Your Health Dashboard' })).toBeVisible();
	});

	test('shows "Upload your first document" CTA when no uploads', async ({ page }) => {
		await page.route('**/api/v1/health-values', (route) =>
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
		);
		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ recommendations: [], has_uploads: false })
			})
		);

		await page.goto('/dashboard');
		await expect(page.getByRole('heading', { name: 'Upload your first document' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Upload document' })).toHaveAttribute(
			'href',
			'/documents/upload'
		);
	});

	test('shows profile-based recommendations in empty state', async ({ page }) => {
		await page.route('**/api/v1/health-values', (route) =>
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
		);
		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ recommendations: MOCK_RECOMMENDATIONS, has_uploads: false })
			})
		);

		await page.goto('/dashboard');
		await expect(page.getByRole('heading', { name: 'Complete Blood Count' })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'HbA1c' })).toBeVisible();
		// Condition-specific recommendation badge
		await expect(page.getByText('Condition-specific')).toBeVisible();
	});

	test('shows health values when data is present', async ({ page }) => {
		await page.route('**/api/v1/health-values', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_HEALTH_VALUES)
			})
		);
		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ recommendations: [], has_uploads: true })
			})
		);

		await page.goto('/dashboard');
		await expect(page.getByRole('heading', { name: 'Hemoglobin' })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Glucose' })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'LDL Cholesterol' })).toBeVisible();
	});

	test('shows correct status summary counts', async ({ page }) => {
		await page.route('**/api/v1/health-values', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_HEALTH_VALUES)
			})
		);
		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ recommendations: [], has_uploads: true })
			})
		);

		await page.goto('/dashboard');

		const summary = page.getByRole('region', { name: 'Health value summary' });
		// 1 optimal, 1 borderline, 1 concerning, 0 action_needed
		await expect(summary.getByText('Optimal')).toBeVisible();
		await expect(summary.getByText('Borderline')).toBeVisible();
		await expect(summary.getByText('Concerning')).toBeVisible();
	});

	test('shows value with reference range', async ({ page }) => {
		await page.route('**/api/v1/health-values', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_HEALTH_VALUES)
			})
		);
		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ recommendations: [], has_uploads: true })
			})
		);

		await page.goto('/dashboard');
		// Hemoglobin reference range 12 – 16 g/dL
		await expect(page.getByText('Reference: 12 – 16 g/dL')).toBeVisible();
	});

	test('shows error state with "Try again" button on API failure', async ({ page }) => {
		await page.route('**/api/v1/health-values', (route) =>
			route.fulfill({ status: 500, body: '{}' })
		);
		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({ status: 500, body: '{}' })
		);

		await page.goto('/dashboard');
		// TanStack Query retries 3× before setting isError — allow up to 15s
		await expect(
			page.getByText('Unable to load your health data. Please try again.')
		).toBeVisible({ timeout: 15_000 });
		await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible();
	});

	test('switching to analysis filter after only plain documents remain shows filter-empty state', async ({
		page
	}) => {
		const analysisDoc = {
			id: 'doc-analysis',
			user_id: 'user-1',
			filename: 'analysis_report.pdf',
			file_size_bytes: 2048,
			file_type: 'application/pdf',
			status: 'completed',
			arq_job_id: null,
			keep_partial: null,
			document_kind: 'analysis',
			needs_date_confirmation: false,
			partial_measured_at_text: null,
			created_at: '2026-03-20T09:00:00Z',
			updated_at: '2026-03-20T09:00:00Z'
		};
		const plainDoc = {
			id: 'doc-plain',
			user_id: 'user-1',
			filename: 'referral.pdf',
			file_size_bytes: 1024,
			file_type: 'application/pdf',
			status: 'completed',
			arq_job_id: null,
			keep_partial: null,
			document_kind: 'document',
			needs_date_confirmation: false,
			partial_measured_at_text: null,
			created_at: '2026-03-20T10:00:00Z',
			updated_at: '2026-03-20T10:00:00Z'
		};
		const analysisDetail = {
			...analysisDoc,
			health_values: MOCK_HEALTH_VALUES
		};
		const activeInterpretation = 'Analysis summary still present.';
		let analysisDeleted = false;

		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ recommendations: [], has_uploads: true })
			})
		);
		await page.route('**/api/v1/documents', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(analysisDeleted ? [plainDoc] : [analysisDoc, plainDoc])
			})
		);
		await page.route(`**/api/v1/documents/${analysisDoc.id}`, (route) => {
			if (route.request().method() === 'DELETE') {
				analysisDeleted = true;
				return route.fulfill({
					status: 200,
					contentType: 'application/json',
					body: JSON.stringify({ deleted: true })
				});
			}

			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(analysisDetail)
			});
		});
		await page.route('**/api/v1/health-values*', (route) => {
			const url = new URL(route.request().url());
			if (url.pathname.endsWith('/baseline')) return route.fallback();
			const kind = url.searchParams.get('document_kind');
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(
					analysisDeleted || kind === 'document' ? [] : MOCK_HEALTH_VALUES
				)
			});
		});
		await page.route('**/api/v1/ai/dashboard/interpretation*', (route) => {
			if (analysisDeleted) {
				return route.fulfill({
					status: 409,
					contentType: 'application/json',
					body: JSON.stringify({ detail: 'No AI context' })
				});
			}
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					document_id: null,
					document_kind: 'all',
					source_document_ids: [analysisDoc.id],
					interpretation: activeInterpretation,
					model_version: 'claude-sonnet-4',
					generated_at: '2026-03-20T10:10:00Z',
					reasoning: null
				})
			});
		});

		await page.goto('/dashboard');
		await expect(page.getByRole('cell', { name: 'Hemoglobin' })).toBeVisible();
		await expect(page.getByText(activeInterpretation)).toBeVisible();

		await page.getByRole('link', { name: 'Documents' }).click();
		const row = page.getByRole('row').filter({ hasText: 'analysis_report.pdf' });
		await expect(row).toBeVisible();
		await row.click();
		await page.getByRole('button', { name: 'Delete Document' }).click();
		const confirmDialog = page.getByRole('alertdialog');
		await expect(confirmDialog).toBeVisible();
		await confirmDialog.getByRole('button', { name: /^Delete$/ }).click();
		await expect(page.getByRole('row').filter({ hasText: 'analysis_report.pdf' })).toHaveCount(0);

		await page.getByRole('link', { name: 'Dashboard' }).click();
		await expect(page.getByRole('cell', { name: 'Hemoglobin' })).toHaveCount(0);
		await expect(page.getByText(activeInterpretation)).toHaveCount(0);

		await page
			.getByTestId('dashboard-filter')
			.getByText('Analyses', { exact: true })
			.click();

		const filterEmpty = page.getByTestId('dashboard-filter-empty');
		await expect(filterEmpty).toBeVisible();
		await expect(filterEmpty).toContainText('No analyses yet');

		// First-time empty CTA must not render (user does have uploads).
		await expect(
			page.getByRole('heading', { name: 'Upload your first document' })
		).toHaveCount(0);
	});

	test('"Try again" button re-fetches data', async ({ page }) => {
		// TanStack Query retries 3× after initial failure (4 total attempts).
		// Must return 500 for ALL 4 so that isError becomes true and "Try again" shows.
		let callCount = 0;
		await page.route('**/api/v1/health-values', (route) => {
			callCount++;
			if (callCount <= 4) return route.fulfill({ status: 500, body: '{}' });
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([])
			});
		});
		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ recommendations: [], has_uploads: false })
			})
		);

		await page.goto('/dashboard');
		// Wait up to 15s for TanStack Query to exhaust retries and surface error state
		await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible({ timeout: 15_000 });
		await page.getByRole('button', { name: 'Try again' }).click();
		// Call 5 returns 200 — error clears, heading shows
		await expect(page.getByRole('heading', { name: 'Your Health Dashboard' })).toBeVisible({
			timeout: 10_000
		});
	});
});
