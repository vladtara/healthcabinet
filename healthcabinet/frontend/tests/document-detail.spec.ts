import { expect, test } from '@playwright/test';
import { setupAuth } from './helpers/auth';
import { setupSSEMock, dispatchSSEEvents } from './helpers/sse';

const DOC_ID = 'doc-detail-123';

const MOCK_PENDING_DOCUMENT = {
	id: DOC_ID,
	user_id: 'user-1',
	filename: 'blood_test_march.pdf',
	file_size_bytes: 204800,
	file_type: 'application/pdf',
	status: 'pending',
	arq_job_id: 'job-abc',
	keep_partial: null,
	health_values: [],
	created_at: '2026-03-20T09:00:00Z',
	updated_at: '2026-03-20T09:00:00Z'
};

const MOCK_HEALTH_VALUES = [
	{
		id: 'hv-10',
		user_id: 'user-1',
		document_id: DOC_ID,
		biomarker_name: 'TSH',
		canonical_biomarker_name: 'tsh',
		value: 2.4,
		unit: 'mIU/L',
		reference_range_low: 0.4,
		reference_range_high: 4.0,
		measured_at: '2026-03-20T00:00:00Z',
		confidence: 0.97,
		needs_review: false,
		is_flagged: false,
		flagged_at: null,
		created_at: '2026-03-20T10:00:00Z',
		status: 'optimal'
	},
	{
		id: 'hv-11',
		user_id: 'user-1',
		document_id: DOC_ID,
		biomarker_name: 'Free T4',
		canonical_biomarker_name: 'free_t4',
		value: 0.8,
		unit: 'ng/dL',
		reference_range_low: 0.7,
		reference_range_high: 1.9,
		measured_at: '2026-03-20T00:00:00Z',
		confidence: 0.91,
		needs_review: false,
		is_flagged: false,
		flagged_at: null,
		created_at: '2026-03-20T10:00:00Z',
		status: 'optimal'
	}
];

const MOCK_COMPLETED_DOCUMENT = {
	...MOCK_PENDING_DOCUMENT,
	status: 'completed',
	health_values: MOCK_HEALTH_VALUES
};

const MOCK_INTERPRETATION = {
	document_id: DOC_ID,
	interpretation:
		'Your TSH and Free T4 values are within normal reference ranges, indicating normal thyroid function.',
	model_version: 'claude-sonnet-4',
	generated_at: '2026-03-20T10:05:00Z',
	reasoning: null
};

const MOCK_PATTERNS = { patterns: [] };

test.describe('Document detail page', () => {
	test.beforeEach(async ({ page }) => {
		await setupAuth(page);
		await page.route(`**/api/v1/ai/documents/${DOC_ID}/interpretation`, (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_INTERPRETATION)
			})
		);
		await page.route('**/api/v1/ai/patterns', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_PATTERNS)
			})
		);
		await page.route('**/api/v1/ai/chat', (route) => route.abort());
	});

	test('shows document filename as page heading', async ({ page }) => {
		await page.route(`**/api/v1/documents/${DOC_ID}`, (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_COMPLETED_DOCUMENT)
			})
		);

		await page.goto(`/documents/${DOC_ID}`);
		await expect(page.getByRole('heading', { name: 'blood_test_march.pdf' })).toBeVisible();
	});

	test('shows document metadata: date and file size', async ({ page }) => {
		await page.route(`**/api/v1/documents/${DOC_ID}`, (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_COMPLETED_DOCUMENT)
			})
		);

		await page.goto(`/documents/${DOC_ID}`);
		// File size 204800 bytes → "200.0 KB"
		await expect(page.getByText(/200\.0 KB/)).toBeVisible();
	});

	test('shows extracted health values count and list', async ({ page }) => {
		await page.route(`**/api/v1/documents/${DOC_ID}`, (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_COMPLETED_DOCUMENT)
			})
		);

		await page.goto(`/documents/${DOC_ID}`);
		await expect(page.getByRole('heading', { name: 'Extracted Values (2)' })).toBeVisible();
		// Use exact match: 'TSH' also appears inside the AI interpretation text
		await expect(page.getByText('TSH', { exact: true })).toBeVisible();
		await expect(page.getByText('Free T4', { exact: true })).toBeVisible();
	});

	test('shows "No extracted health values" for completed doc with empty values', async ({
		page
	}) => {
		await page.route(`**/api/v1/documents/${DOC_ID}`, (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ ...MOCK_COMPLETED_DOCUMENT, health_values: [] })
			})
		);

		await page.goto(`/documents/${DOC_ID}`);
		await expect(page.getByText('No extracted health values.')).toBeVisible();
	});

	test('shows "← Back to Documents" link', async ({ page }) => {
		await page.route(`**/api/v1/documents/${DOC_ID}`, (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_COMPLETED_DOCUMENT)
			})
		);

		await page.goto(`/documents/${DOC_ID}`);
		await expect(page.getByRole('link', { name: /back to documents/i })).toHaveAttribute(
			'href',
			'/documents'
		);
	});

	test('shows processing pipeline for pending document', async ({ page }) => {
		await setupSSEMock(page);
		await page.route(`**/api/v1/documents/${DOC_ID}`, (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_PENDING_DOCUMENT)
			})
		);

		await page.goto(`/documents/${DOC_ID}`);
		// ProcessingPipeline renders the 5 stage labels
		await expect(page.getByText('Uploading')).toBeVisible();
		await expect(page.getByText('Reading document')).toBeVisible();
		await expect(page.getByText('Extracting values')).toBeVisible();
	});

	test('pipeline completion on detail page refreshes document data', async ({ page }) => {
		await setupSSEMock(page);

		let callCount = 0;
		await page.route(`**/api/v1/documents/${DOC_ID}`, (route) => {
			callCount++;
			const doc = callCount === 1 ? MOCK_PENDING_DOCUMENT : MOCK_COMPLETED_DOCUMENT;
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(doc)
			});
		});

		await page.goto(`/documents/${DOC_ID}`);
		await dispatchSSEEvents(page, DOC_ID, [
			'document.upload_started',
			'document.reading',
			'document.extracting',
			'document.generating',
			'document.completed'
		]);

		// After completion, document is re-fetched and shows extracted values
		await expect(page.getByRole('heading', { name: 'Extracted Values (2)' })).toBeVisible();
	});

	test('shows error state with alert for failed document fetch', async ({ page }) => {
		await page.route(`**/api/v1/documents/${DOC_ID}`, (route) =>
			route.fulfill({ status: 404, body: '{}' })
		);

		await page.goto(`/documents/${DOC_ID}`);
		// TanStack Query retries 3× before setting isError — allow up to 15s
		await expect(page.getByRole('alert')).toBeVisible({ timeout: 15_000 });
		await expect(page.getByText('Failed to load document. Please try again.')).toBeVisible();
	});

	test('yearless analysis shows confirmation banner and updates dashboard after year confirmed', async ({
		page
	}) => {
		const MOCK_PARTIAL_DOCUMENT = {
			...MOCK_COMPLETED_DOCUMENT,
			status: 'partial',
			document_kind: 'analysis',
			needs_date_confirmation: true,
			partial_measured_at_text: '03.12',
			health_values: MOCK_HEALTH_VALUES.map((v) => ({ ...v, measured_at: null }))
		};
		const MOCK_CONFIRMED_DOCUMENT = {
			...MOCK_COMPLETED_DOCUMENT,
			status: 'completed',
			document_kind: 'analysis',
			needs_date_confirmation: false,
			partial_measured_at_text: null,
			health_values: MOCK_HEALTH_VALUES.map((v) => ({
				...v,
				measured_at: '2025-12-03T00:00:00Z'
			}))
		};
		const DASHBOARD_INTERPRETATION_BEFORE =
			'Draft dashboard interpretation before year confirmation.';
		const DASHBOARD_INTERPRETATION_AFTER =
			'Dashboard interpretation after year confirmation for 2025.';
		const CONFIRMED_DASHBOARD_VALUES = MOCK_CONFIRMED_DOCUMENT.health_values.map((value) => ({
			...value,
			measured_at: '2025-12-03T00:00:00Z'
		}));
		let submittedYear: number | null = null;
		let hasConfirmedYear = false;

		await page.route('**/api/v1/health-values/baseline', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ recommendations: [], has_uploads: true })
			})
		);
		await page.route('**/api/v1/health-values*', (route) => {
			const url = new URL(route.request().url());
			if (url.pathname.endsWith('/baseline')) return route.fallback();
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(hasConfirmedYear ? CONFIRMED_DASHBOARD_VALUES : [])
			});
		});
		await page.route('**/api/v1/ai/dashboard/interpretation*', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					document_id: null,
					document_kind: 'all',
					source_document_ids: [DOC_ID],
					interpretation: hasConfirmedYear
						? DASHBOARD_INTERPRETATION_AFTER
						: DASHBOARD_INTERPRETATION_BEFORE,
					model_version: 'claude-sonnet-4',
					generated_at: '2026-03-20T10:05:00Z',
					reasoning: null
				})
			})
		);

		await page.route('**/api/v1/documents', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify([hasConfirmedYear ? MOCK_CONFIRMED_DOCUMENT : MOCK_PARTIAL_DOCUMENT])
			})
		);

		await page.route(`**/api/v1/documents/${DOC_ID}`, (route) => {
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(hasConfirmedYear ? MOCK_CONFIRMED_DOCUMENT : MOCK_PARTIAL_DOCUMENT)
			});
		});

		await page.route(`**/api/v1/documents/${DOC_ID}/confirm-date-year`, (route) => {
			submittedYear = route.request().postDataJSON()?.year ?? null;
			hasConfirmedYear = submittedYear === 2025;
			return route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_CONFIRMED_DOCUMENT)
			});
		});

		await page.goto('/dashboard');
		await expect(page.getByText(DASHBOARD_INTERPRETATION_BEFORE)).toBeVisible();

		await page.getByRole('link', { name: 'Documents' }).click();
		await page.goto('/documents');

		// Select the yearless document from the list to open the detail panel.
		const row = page.getByRole('row').filter({ hasText: 'blood_test_march.pdf' });
		await expect(row).toBeVisible();
		await row.click();

		// Banner + Confirm year button are visible.
		await expect(page.getByText('03.12, year?')).toBeVisible();
		const confirmBtn = page.getByRole('button', { name: 'Confirm year' });
		await expect(confirmBtn).toBeVisible();
		await confirmBtn.click();

		// Year picker opens with a select (aria-label 'Year') and a Save button.
		const yearSelect = page.getByRole('combobox', { name: 'Year' });
		await expect(yearSelect).toBeVisible();
		await yearSelect.selectOption('2025');
		await page.getByRole('button', { name: 'Save' }).click();

		// Banner gone, selected year was submitted, and the confirmed date is rendered.
		await expect(page.getByRole('button', { name: 'Confirm year' })).toHaveCount(0);
		await expect(page.getByText('03.12, year?')).toHaveCount(0);
		await expect(page.getByText('Dec 3, 2025')).toBeVisible();
		expect(submittedYear).toBe(2025);

		await page.getByRole('link', { name: 'Dashboard' }).click();
		await expect(page.getByText(DASHBOARD_INTERPRETATION_AFTER)).toBeVisible();
		await expect(page.getByRole('cell', { name: 'TSH' })).toBeVisible();
	});
});
