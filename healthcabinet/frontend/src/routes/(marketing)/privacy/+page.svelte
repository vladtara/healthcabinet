<script lang="ts">
	import { page } from '$app/stores';

	// Shape-validation for the policy-version query parameter. Wide enough to
	// accept SemVer 2.0 (build metadata via `+`, pre-release suffixes) up to
	// 64 chars. Unmatched input falls back to "current" so the heading stays
	// deterministic. XSS is already blocked by Svelte's auto-escaping of text
	// interpolation below; this regex is belt-and-suspenders for shape only,
	// NOT a security barrier — do NOT rely on it if future code binds the
	// version into {@html} or an href/src attribute.
	const VERSION_PATTERN = /^[A-Za-z0-9._+-]{1,64}$/;

	const versionRaw = $derived($page.url.searchParams.get('version'));
	const version = $derived(versionRaw && VERSION_PATTERN.test(versionRaw) ? versionRaw : 'current');
</script>

<svelte:head>
	<title>Privacy Policy — HealthCabinet</title>
	<meta
		name="description"
		content="HealthCabinet privacy policy and version history for user consent records."
	/>
</svelte:head>

<main class="hc-privacy-page">
	<header class="hc-privacy-header">
		<h1 class="hc-privacy-heading">Privacy Policy</h1>
		<h2 class="hc-privacy-subheading" data-testid="privacy-version">Version {version}</h2>
	</header>

	<section class="hc-privacy-body" aria-label="Policy placeholder">
		<p>
			HealthCabinet records every privacy policy version you accept so you can always verify what
			you agreed to. The full text for this version is being finalised.
		</p>
		<p>
			If you need a copy of the policy that applied on a specific date, contact
			<a class="hc-privacy-support-link" href="mailto:support@healthcabinet.local">
				support@healthcabinet.local
			</a>
			and include the version you see above.
		</p>
	</section>

	<footer class="hc-privacy-footer">
		<a class="hc-privacy-back-link" href="/">Return to HealthCabinet</a>
	</footer>
</main>
