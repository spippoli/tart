import { m } from '#lib/paraglide/messages.js';
import type { Locale } from '#lib/paraglide/runtime.js';
import { artworkCount, type LocationProperties } from './locations';
import type { Group } from './signs';

type Message = (inputs: { count: string }, options: { locale: Locale }) => string;

function counted(count: number, locale: Locale, one: Message, other: Message): string {
	const message = new Intl.PluralRules(locale).select(count) === 'one' ? one : other;
	return message({ count: new Intl.NumberFormat(locale).format(count) }, { locale });
}

const artworks = (count: number, locale: Locale) =>
	counted(count, locale, m.map_artworks_one, m.map_artworks_other);

const GROUP_WORDS: Record<Group, [Message, Message]> = {
	present: [m.map_group_present_one, m.map_group_present_other],
	unknown: [m.map_group_unknown_one, m.map_group_unknown_other],
	disappeared: [m.map_group_disappeared_one, m.map_group_disappeared_other]
};

/**
 * The accessible name of a sign: the counts per Condition group, e.g. "Location,
 * 3 artworks: 1 present, 2 disappeared", and in words when the position is approximate.
 */
export function signName(properties: LocationProperties, locale: Locale): string {
	const groups = (['present', 'unknown', 'disappeared'] as const)
		.filter((group) => properties[group] > 0)
		.map((group) => counted(properties[group], locale, ...GROUP_WORDS[group]))
		.join(', ');
	const name = m.map_sign_name(
		{ artworks: artworks(artworkCount(properties), locale), groups },
		{ locale }
	);
	return properties.approximate ? `${name}, ${m.map_sign_approximate({}, { locale })}` : name;
}

/** The accessible name of a cluster: "Cluster of 24 artworks in 9 Locations; activate to zoom in". */
export function clusterName(artworkTotal: number, locations: number, locale: Locale): string {
	return m.map_cluster_name(
		{
			artworks: artworks(artworkTotal, locale),
			locations: counted(locations, locale, m.map_locations_one, m.map_locations_other)
		},
		{ locale }
	);
}
