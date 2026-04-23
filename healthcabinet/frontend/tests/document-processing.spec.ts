import { expect, test } from '@playwright/test';
import { setupAuth, MOCK_TOKEN } from './helpers/auth';
import { setupSSEMock, dispatchSSEEvents, triggerSSEErrors } from './helpers/sse';

const MOCK_DOC_ID = 'mock-doc-id';

const MOCK_DOCUMENT = {
	id: MOCK_DOC_ID,
	user_id: 'user-1',
	filename: 'lab_results.pdf',
	file_size_bytes: 1024,
	file_type: 'application/pdf',
	status: 'pending',
	arq_job_id: null,
	keep_partial: null,
	created_at: new Date().toISOString(),
	updated_at: new Date().toISOString()
};

const ALL_PIPELINE_EVENTS = [
	'document.upload_started',
	'document.reading',
	'document.extracting',
	'document.generating',
	'document.completed'
];

test.describe('document processing upload flow', () => {
	test.beforeEach(async ({ page }) => {
		await setupSSEMock(page);
		await setupAuth(page);
		await page.route('**/api/v1/documents/upload', (route) =>
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify(MOCK_DOCUMENT)
			})
		);
	});

	test('upload page renders heading and description', async ({ page }) => {
		await page.goto('/documents/upload');
		await expect(page.getByText('Upload Health Document')).toBeVisible();
		await expect(
			page.getByText('Upload a PDF or photo of your health document for AI-powered analysis.')
		).toBeVisible();
	});

	test('upload zone is present with correct aria label', async ({ page }) => {
		await page.goto('/documents/upload');
		await expect(
			page.getByRole('button', {
				name: /upload health document/i
			})
		).toBeVisible();
	});

	test('happy path: upload → SSE pipeline stages → success state', async ({ page }) => {
		await page.goto('/documents/upload');
		await page.locator('#file-input').setInputFiles({
			name: 'lab_results.pdf',
			mimeType: 'application/pdf',
			buffer: Buffer.from('fake-pdf-content')
		});

		await dispatchSSEEvents(page, MOCK_DOC_ID, ALL_PIPELINE_EVENTS);

		await expect(page.getByText('Your document has been processed successfully.')).toBeVisible();
		await expect(page.getByRole('link', { name: 'View your results' })).toBeVisible();
	});

	test('pipeline shows all 5 stage labels during processing', async ({ page }) => {
		await page.goto('/documents/upload');
		await page.locator('#file-input').setInputFiles({
			name: 'lab_results.pdf',
			mimeType: 'application/pdf',
			buffer: Buffer.from('fake-pdf-content')
		});

		// Wait for pipeline to render before full completion
		await page.waitForFunction(
			() => (window as Window & { __eventSources?: unknown[] }).__eventSources?.length === 1
		);

		await expect(page.getByText('Uploading')).toBeVisible();
		await expect(page.getByText('Reading document')).toBeVisible();
		await expect(page.getByText('Extracting values')).toBeVisible();
		await expect(page.getByText('Generating insights')).toBeVisible();
		await expect(page.getByText('Complete')).toBeVisible();
	});

	test('failure path: document.failed → PartialExtractionCard with recovery options', async ({
		page
	}) => {
		await page.goto('/documents/upload');
		await page.locator('#file-input').setInputFiles({
			name: 'lab_results.pdf',
			mimeType: 'application/pdf',
			buffer: Buffer.from('fake-pdf-content')
		});

		await dispatchSSEEvents(page, MOCK_DOC_ID, ['document.failed']);

		// documentId is set → PartialExtractionCard renders, not simple error text
		await expect(page.getByRole('heading', { name: 'Extraction failed' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Re-upload document' })).toBeVisible();
	});

	test('partial path: document.partial → partial state with recovery affordances', async ({
		page
	}) => {
		await page.goto('/documents/upload');
		await page.locator('#file-input').setInputFiles({
			name: 'lab_results.pdf',
			mimeType: 'application/pdf',
			buffer: Buffer.from('fake-pdf-content')
		});

		await dispatchSSEEvents(page, MOCK_DOC_ID, ['document.partial']);

		await expect(page.getByText('Processing finished with partial extraction.')).toBeVisible();
		await expect(page.getByRole('link', { name: 'view your results' })).toBeVisible();
	});

	test('SSE stream error: 3 consecutive errors → PartialExtractionCard with recovery options', async ({
		page
	}) => {
		await page.goto('/documents/upload');
		await page.locator('#file-input').setInputFiles({
			name: 'lab_results.pdf',
			mimeType: 'application/pdf',
			buffer: Buffer.from('fake-pdf-content')
		});

		await triggerSSEErrors(page, 3);

		// documentId is set → PartialExtractionCard renders
		await expect(page.getByRole('heading', { name: 'Extraction failed' })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Re-upload document' })).toBeVisible();
	});

	test('unsupported file type shows error in upload zone', async ({ page }) => {
		await page.goto('/documents/upload');
		await page.locator('#file-input').setInputFiles({
			name: 'spreadsheet.xlsx',
			mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
			buffer: Buffer.from('fake-content')
		});

		// Text appears in both aria-live (sr-only) and role="alert" — scope to visible alert
		await expect(page.getByRole('alert')).toContainText(
			'Unsupported file type — please upload a PDF or image.'
		);
	});

	test('upload API failure shows error with retry button', async ({ page }) => {
		await page.unroute('**/api/v1/documents/upload');
		await page.route('**/api/v1/documents/upload', (route) =>
			route.fulfill({ status: 500, body: JSON.stringify({ detail: 'Internal error' }) })
		);

		await page.goto('/documents/upload');
		await page.locator('#file-input').setInputFiles({
			name: 'lab_results.pdf',
			mimeType: 'application/pdf',
			buffer: Buffer.from('fake-pdf-content')
		});

		// Text appears in both aria-live (sr-only) and role="alert" — scope to visible alert
		await expect(page.getByRole('alert')).toContainText('Upload failed. Tap to retry.');
		await expect(page.getByRole('button', { name: 'Retry upload' })).toBeVisible();
	});

	test('multi-file sequential queue processes files one at a time and shows batch summary', async ({
		page
	}) => {
		// Story 15.7 AC3 — regression gate for Story 15.4 (sequential multi-upload
		// queue). The current production code uses fetch-based streaming via
		// apiStream() for /status (Story 14.1), not EventSource — so this test
		// does not use the SSE EventSource helpers. It asserts sequentiality
		// through upload-request ordering and the batch summary render.
		await page.unroute('**/api/v1/documents/upload');

		const eventLog: string[] = [];

		await page.route('**/api/v1/documents/upload', async (route) => {
			const req = route.request();
			const postData = req.postDataBuffer();
			const bodyText = postData ? postData.toString('utf-8') : '';
			const isAlpha = bodyText.includes('alpha.pdf');
			eventLog.push(`upload:${isAlpha ? 'alpha' : 'beta'}`);
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					...MOCK_DOCUMENT,
					id: isAlpha ? 'doc-alpha' : 'doc-beta',
					filename: isAlpha ? 'alpha.pdf' : 'beta.pdf'
				})
			});
		});

		// Per-doc status stream. Fetch-based SSE: parser splits body on \n\n,
		// reads the "data: " line as JSON. The pipeline's onEvent sees the
		// terminal event and aborts the controller, which unblocks the queue.
		await page.route('**/api/v1/documents/doc-alpha/status*', async (route) => {
			eventLog.push('status:alpha');
			const frame = {
				event: 'document.completed',
				document_id: 'doc-alpha',
				progress: 1,
				message: 'alpha done'
			};
			await route.fulfill({
				status: 200,
				contentType: 'text/event-stream',
				body: `data: ${JSON.stringify(frame)}\n\n`
			});
		});
		await page.route('**/api/v1/documents/doc-beta/status*', async (route) => {
			eventLog.push('status:beta');
			const frame = {
				event: 'document.partial',
				document_id: 'doc-beta',
				progress: 1,
				message: 'beta partial'
			};
			await route.fulfill({
				status: 200,
				contentType: 'text/event-stream',
				body: `data: ${JSON.stringify(frame)}\n\n`
			});
		});

		await page.goto('/documents/upload');
		await page.locator('#file-input').setInputFiles([
			{ name: 'alpha.pdf', mimeType: 'application/pdf', buffer: Buffer.from('alpha-bytes') },
			{ name: 'beta.pdf', mimeType: 'application/pdf', buffer: Buffer.from('beta-bytes') }
		]);

		// Wait for the batch summary — means both files flowed through.
		await expect(
			page.getByRole('heading', { name: 'Batch complete', level: 3 })
		).toBeVisible({ timeout: 15_000 });
		await expect(page.getByText(/✓ 1 complete/)).toBeVisible();
		await expect(page.getByText(/⚠ 1 partial/)).toBeVisible();

		// Sequentiality invariant: the second upload cannot begin until the
		// first file reaches a terminal status and its stream handler resolves.
		expect(eventLog).toEqual(['upload:alpha', 'status:alpha', 'upload:beta', 'status:beta']);
	});

	test('SSE URL includes auth token', async ({ page }) => {
		await page.goto('/documents/upload');
		await page.locator('#file-input').setInputFiles({
			name: 'lab_results.pdf',
			mimeType: 'application/pdf',
			buffer: Buffer.from('fake-pdf-content')
		});

		await page.waitForFunction(
			() => (window as Window & { __eventSources?: unknown[] }).__eventSources?.length === 1
		);

		const sseUrl = await page.evaluate(() => {
			const win = window as Window & { __eventSources?: Array<{ url: string }> };
			return win.__eventSources?.[0]?.url ?? '';
		});

		expect(sseUrl).toContain(MOCK_DOC_ID);
		expect(sseUrl).toContain(MOCK_TOKEN);
		expect(sseUrl).toContain('/status');
	});
});
