<script lang="ts">
	import { m } from '#lib/paraglide/messages.js';
	import { localizeHref, type Locale } from '#lib/paraglide/runtime.js';
	import { licence } from '#lib/licences.ts';
	import { tartVersion } from '#lib/version.ts';

	let { dataLicence, locale }: { dataLicence: string; locale: Locale } = $props();
</script>

<footer class="site-footer">
	<nav aria-label={m.footer_nav_label()}>
		<ul>
			<!-- "Powered by TART" is rendered by the platform, not configured (ADR 0011 §7). -->
			<li>
				<a href={localizeHref('/about/tart')}>{m.footer_powered_by({ version: tartVersion })}</a>
			</li>
			<li>
				<a href={localizeHref('/about/data-licence')}
					>{m.footer_data_licence({ licence: licence(dataLicence, locale).label })}</a
				>
			</li>
			<li><a href={localizeHref('/about/contact')}>{m.footer_contact()}</a></li>
			<li><a href={localizeHref('/about/terms')}>{m.footer_terms()}</a></li>
			<li><a href={localizeHref('/about/privacy')}>{m.footer_privacy()}</a></li>
		</ul>
	</nav>
</footer>

<style>
	.site-footer {
		margin-block-start: 3rem;
		padding: 1.5rem var(--gutter);
		border-block-start: 1px solid var(--border);
		color: var(--text-muted);
	}

	ul {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1.5rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	a {
		display: inline-block;
		padding-block: 0.25rem;
	}
</style>
