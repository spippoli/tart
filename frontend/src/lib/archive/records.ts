/**
 * How Archive records read (archive-records spec, Public record pages; ADR 0015): the
 * words of Conditions, Attributions, and Evidence levels, record URLs, and Location
 * titles. The API derives every value; this module only words it, in the UI language.
 */
import type { components } from '../api/schema';
import { m } from '#lib/paraglide/messages.js';
import { localizeHref, type Locale } from '#lib/paraglide/runtime.js';
import {
	formatPeriod,
	formatUncertainDate,
	type DateFormatContext,
	type Period,
	type UncertainDate
} from './uncertain-date';

type Schemas = components['schemas'];
export type RecordLink = Schemas['RecordLink'];
export type Kind = RecordLink['kind'];
export type ConditionView = Schemas['ConditionView'];
export type Condition = ConditionView['condition'];
export type ConditionGroup = ConditionView['group'];
export type ShownAttribution = Schemas['ShownAttribution'];
export type AttributionReadout = Schemas['AttributionReadout'];
export type LocationTitle = Schemas['LocationTitle'];
export type ArtworkCard = Schemas['ArtworkCard'];
export type HistoryEventType = Schemas['EventEntry']['type'];
export type Medium = Schemas['DocumentationSummary']['medium'];
export type EvidenceLevel = Schemas['ShownAttribution']['evidence_level'];
export type Certainty = Schemas['ShownAttribution']['certainty'];

type Options = { locale: Locale };
type Message = (inputs: Record<string, never>, options: Options) => string;

/** The route of each kind, de-localized (see `$lib/i18n/url-patterns`). */
export const ROUTES: Record<Kind, string> = {
	artwork: '/artworks',
	artist: '/artists',
	location: '/locations',
	site: '/sites',
	area: '/areas',
	series: '/series',
	source: '/sources',
	documentation_item: '/documents'
};

/** The API segment of each kind. */
export const API_SEGMENTS: Record<Kind, string> = {
	artwork: 'artworks',
	artist: 'artists',
	location: 'locations',
	site: 'sites',
	area: 'areas',
	series: 'series',
	source: 'sources',
	documentation_item: 'documents'
};

/** The page of a record at its canonical `{id}-{slug}` path, in the UI language. */
export function recordHref(kind: Kind, path: string, locale?: Locale): string {
	return localizeHref(`${ROUTES[kind]}/${path}`, locale ? { locale } : undefined);
}

export function revisionsHref(kind: Kind, path: string, anchor?: number): string {
	return localizeHref(`${ROUTES[kind]}/${path}/revisions`) + (anchor ? `#revision-${anchor}` : '');
}

/** The report form (Rights and legal actions), naming what is reported. */
const REPORT_PARAMETER: Record<string, string> = { it: 'oggetto', en: 'object' };

export function reportHref(locale: Locale, kind: Kind, id: number, revision?: number): string {
	const object = `${kind}:${id}` + (revision ? `#revision-${revision}` : '');
	const name = REPORT_PARAMETER[locale] ?? 'object';
	return `${localizeHref('/report', { locale })}?${name}=${encodeURIComponent(object)}`;
}

const conditions: Record<Condition, Message> = {
	intact: m.archive_condition_intact,
	deteriorated: m.archive_condition_deteriorated,
	damaged: m.archive_condition_damaged,
	modified: m.archive_condition_modified,
	covered: m.archive_condition_covered,
	removed: m.archive_condition_removed,
	destroyed: m.archive_condition_destroyed,
	missing: m.archive_condition_missing,
	unknown: m.archive_condition_unknown
};

export function conditionWord(condition: Condition, locale: Locale): string {
	return conditions[condition]({}, { locale });
}

const certainties: Record<Certainty, Message> = {
	confirmed: m.archive_certainty_confirmed,
	probable: m.archive_certainty_probable,
	disputed: m.archive_certainty_disputed
};

export function certaintyWord(certainty: Certainty, locale: Locale): string {
	return certainties[certainty]({}, { locale });
}

const events: Record<Exclude<HistoryEventType, 'condition_recorded'>, Message> = {
	created: m.archive_event_created,
	deteriorated: m.archive_event_deteriorated,
	damaged: m.archive_event_damaged,
	modified: m.archive_event_modified,
	covered: m.archive_event_covered,
	removed: m.archive_event_removed,
	destroyed: m.archive_event_destroyed,
	attribution_changed: m.archive_event_attribution_changed
};

/** A History event's type in words; a Condition record names the Condition it states. */
export function eventWord(
	type: HistoryEventType,
	condition: Condition | null | undefined,
	locale: Locale
): string {
	if (type === 'condition_recorded') {
		const stated = conditionWord(condition ?? 'unknown', locale);
		return m.archive_event_condition_recorded({ condition: stated }, { locale });
	}
	return events[type]({}, { locale });
}

const media: Record<Medium, Message> = {
	image: m.archive_medium_image,
	pdf: m.archive_medium_pdf,
	text: m.archive_medium_text,
	link: m.archive_medium_link
};

export function mediumWord(medium: Medium, locale: Locale): string {
	return media[medium]({}, { locale });
}

const kinds: Record<Kind, Message> = {
	artwork: m.archive_kind_artwork,
	artist: m.archive_kind_artist,
	location: m.archive_kind_location,
	site: m.archive_kind_site,
	area: m.archive_kind_area,
	series: m.archive_kind_series,
	source: m.archive_kind_source,
	documentation_item: m.archive_kind_documentation_item
};

export function kindWord(kind: Kind, locale: Locale): string {
	return kinds[kind]({}, { locale });
}

/** "documented · N sources", or "reported · no sources cited". */
export function evidenceWords(level: EvidenceLevel, sources: number, locale: Locale): string {
	if (level === 'reported') return m.archive_evidence_reported({}, { locale });
	const plural = new Intl.PluralRules(locale).select(sources);
	const message =
		plural === 'one' ? m.archive_evidence_documented_one : m.archive_evidence_documented_other;
	return message({ count: new Intl.NumberFormat(locale).format(sources) }, { locale });
}

/** A Location's title: its Place description, else "Surface type · place", else "Location {id}". */
export function locationTitleText(
	id: number,
	title: LocationTitle | null | undefined,
	surfaceLabel: (key: string) => string,
	locale: Locale
): string {
	if (title?.place_description) return title.place_description;
	if (title?.surface_type && title.place) {
		const surface = surfaceLabel(title.surface_type);
		return m.archive_location_composed({ surface, place: title.place }, { locale });
	}
	return m.archive_location_fallback({ id: String(id) }, { locale });
}

/** A record's name for a link or a heading; an untitled Artwork reads "Untitled". */
export function linkText(
	link: RecordLink,
	surfaceLabel: (key: string) => string,
	locale: Locale
): string {
	if (link.kind === 'location') {
		return locationTitleText(link.id, link.location_title, surfaceLabel, locale);
	}
	if (link.name) return link.name;
	if (link.kind === 'artwork') return m.archive_untitled({}, { locale });
	if (link.kind === 'documentation_item') {
		return `${kindWord('documentation_item', locale)} ${link.id}`;
	}
	return m.archive_content_redacted({}, { locale });
}

/**
 * Who an Artwork is by, in one line: "Unknown artist"; the attributed Artists, each
 * "— probable attribution" when probable; or "Disputed attribution: A or B".
 */
export function attributionSummary(readout: AttributionReadout, locale: Locale): string {
	const name = (shown: ShownAttribution): string =>
		shown.artist.name ?? m.archive_content_redacted({}, { locale });
	if (readout.attributed.length === 0 && readout.disputed.length === 0) {
		return m.archive_unknown_artist({}, { locale });
	}
	const parts: string[] = [];
	if (readout.attributed.length > 0) {
		const names = readout.attributed.map((shown) =>
			shown.certainty === 'probable'
				? m.archive_attribution_probable({ name: name(shown) }, { locale })
				: name(shown)
		);
		parts.push(new Intl.ListFormat(locale, { type: 'conjunction' }).format(names));
	}
	if (readout.disputed.length > 0) {
		const names = new Intl.ListFormat(locale, { type: 'disjunction' }).format(
			readout.disputed.map(name)
		);
		parts.push(m.archive_attribution_disputed({ names }, { locale }));
	}
	return parts.join(' · ');
}

/** The label of a vocabulary key in the UI language, falling back to the key. */
export function vocabularyLabels(
	entries: { key: string; label: Record<string, string> }[],
	locale: Locale
): (key: string) => string {
	const labels = new Map(entries.map((entry) => [entry.key, entry.label[locale] ?? entry.key]));
	return (key) => labels.get(key) ?? key;
}

export type ApiDate = Schemas['UncertainDate'];

/** An Uncertain date from the API in words; the API validates its shape. */
export function archiveDate(date: ApiDate, context: DateFormatContext): string {
	return formatUncertainDate(date as UncertainDate, context);
}

/** A period from the API in words, or `null` without either end. */
export function archivePeriod(
	period: Schemas['Period'],
	context: DateFormatContext
): string | null {
	return formatPeriod(period as Period, context);
}

export type ArtworkView = Schemas['ArtworkView'];
export type ArtistView = Schemas['ArtistView'];
export type LocationView = Schemas['LocationView'];
export type PlaceView = Schemas['PlaceView'];
export type SourceView = Schemas['SourceView'];
export type DocumentationItemView = Schemas['DocumentationItemView'];
export type DocumentationSummary = Schemas['DocumentationSummary'];
export type RevisionsView = Schemas['RevisionsView'];
export type IndexPage = Schemas['IndexPage'];
export type EventEntry = Schemas['EventEntry'];
export type ItemEntry = Schemas['ItemEntry'];
