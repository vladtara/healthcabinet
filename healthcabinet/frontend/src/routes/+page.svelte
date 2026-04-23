<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { Button } from '$lib/components/ui/button';
	import { LocaleToggle } from '$lib/components/ui/locale-toggle';
	import { authStore } from '$lib/stores/auth.svelte';
	import { localeStore } from '$lib/stores/locale.svelte';
	import { t } from '$lib/i18n/messages';

	const copy = $derived(t(localeStore.locale).landing);

	let showDeletedBanner = $state(false);

	$effect(() => {
		if (authStore.isAuthenticated) {
			goto('/dashboard').catch(() => {});
		}
	});

	$effect(() => {
		const deleted = $page.url.searchParams.get('deleted');
		if (deleted === 'true') {
			showDeletedBanner = true;
			// Remove the query param from URL without navigation
			const url = new URL(window.location.href);
			url.searchParams.delete('deleted');
			window.history.replaceState({}, '', url.pathname);
		}
	});
</script>

<svelte:head>
	<title>{copy.headTitle}</title>
	<meta name="description" content={copy.headDescription} />
</svelte:head>

{#if showDeletedBanner}
	<div class="hc-state hc-state-success" role="status" style="margin: 16px auto; max-width: 640px;">
		<p class="hc-state-title">{copy.deletedBanner}</p>
	</div>
{/if}

{#if !authStore.isAuthenticated}
<div class="hc-landing">
	<!-- Top bar -->
	<nav class="hc-landing-topbar" aria-label={copy.topbarAria}>
		<div class="hc-landing-brand">
			<span class="hc-landing-brand-icon" aria-hidden="true">⚕</span>
			<span>{copy.brand}</span>
		</div>
		<div class="hc-landing-topbar-actions">
			<div class="hc-landing-locale"><LocaleToggle /></div>
			<Button href="/login" variant="standard">{copy.topbarSignIn}</Button>
			<Button href="/register" variant="primary">{copy.topbarGetStarted}</Button>
		</div>
	</nav>

	<!-- Hero -->
	<main class="hc-landing-hero">
		<h1 class="hc-landing-heading">
			{copy.heroTitleTop}<br />
			<span class="hc-landing-accent">{copy.heroTitleBottom}</span>
		</h1>
		<p class="hc-landing-subtitle">
			{copy.heroSubtitle}
		</p>
		<div class="hc-landing-cta">
			<Button href="/register" variant="primary" class="hc-landing-cta-btn"
				>{copy.ctaCreateAccount}</Button
			>
		</div>
	</main>

	<!-- Trust signals -->
	<div class="hc-landing-trust">
		<div class="hc-landing-trust-badge"><span aria-hidden="true">🔒</span> {copy.trustAes}</div>
		<div class="hc-landing-trust-badge"><span aria-hidden="true">🇪🇺</span> {copy.trustEu}</div>
		<div class="hc-landing-trust-badge"><span aria-hidden="true">🛡️</span> {copy.trustGdpr}</div>
	</div>

	<!-- Preview teaser -->
	<div class="hc-landing-preview">
		<div class="hc-landing-preview-frame">
			<table class="hc-landing-preview-table" aria-label={copy.previewExampleAria}>
				<thead>
					<tr>
						<th>{copy.previewBiomarker}</th>
						<th>{copy.previewValue}</th>
						<th>{copy.previewRange}</th>
						<th>{copy.previewStatus}</th>
						<th>{copy.previewTrend}</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td class="hc-landing-biomarker-name">TSH</td>
						<td>3.8 mIU/L</td>
						<td>0.4 – 4.0</td>
						<td class="hc-status-optimal">{copy.previewStatusOptimal}</td>
						<td class="hc-trend-neutral"><span aria-label={copy.previewTrendStable}>→</span></td>
					</tr>
					<tr>
						<td class="hc-landing-biomarker-name">Vitamin D</td>
						<td>22 ng/mL</td>
						<td>30 – 100</td>
						<td class="hc-status-concerning">{copy.previewStatusLow}</td>
						<td class="hc-trend-down-bad"><span aria-label={copy.previewTrendDecreasing}>↓</span></td>
					</tr>
					<tr>
						<td class="hc-landing-biomarker-name">Hemoglobin</td>
						<td>11.8 g/dL</td>
						<td>12.0 – 15.5</td>
						<td class="hc-status-borderline">{copy.previewStatusBorderline}</td>
						<td class="hc-trend-down-warn"><span aria-label={copy.previewTrendDecreasing}>↓</span></td>
					</tr>
					<tr>
						<td class="hc-landing-biomarker-name">Ferritin</td>
						<td>45 ng/mL</td>
						<td>12 – 150</td>
						<td class="hc-status-optimal">{copy.previewStatusOptimal}</td>
						<td class="hc-trend-up-good"><span aria-label={copy.previewTrendIncreasing}>↑</span></td>
					</tr>
				</tbody>
			</table>
			<div class="hc-landing-preview-overlay">
				<div class="hc-landing-preview-overlay-text">{copy.previewOverlay}</div>
			</div>
		</div>
	</div>
</div>
{/if}
