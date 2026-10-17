/**
 * The words of the editor's errors (ADR 0008): every rule the form or the API can refuse
 * has a stable code, and the UI language words it. A code nobody worded reads as a
 * generic refusal that names the code, so that it can be reported.
 */
import { m } from '#lib/paraglide/messages.js';

type Params = Record<string, string | number>;
type Message = (params: Params) => string;

/** The generated messages take their own parameters; here they are all given by name. */
const word = (message: unknown): Message => message as Message;

const messages: Record<string, Message> = {
	'location.required': word(m.editor_error_location_required),
	'location.radius_requires_approximate_point': word(m.editor_error_location_radius),
	'location.surface_type_required': word(m.editor_error_location_surface_type_required),
	'location.surface_type_unknown': word(m.editor_error_location_surface_type_unknown),
	'location.place_description_too_long': word(m.editor_error_location_place_description_too_long),
	'location.place_description_not_one_line': word(
		m.editor_error_location_place_description_one_line
	),
	'location.different_artwork_unconfirmed': word(m.editor_error_location_different_artwork),
	'location.different_surface_unconfirmed': word(m.editor_error_location_different_surface),
	'location.outside_boundary': word(m.editor_error_location_outside_boundary),
	'location.radius_not_positive': word(m.editor_error_location_radius_not_positive),
	'geometry.self_intersecting': word(m.editor_error_geometry_self_intersecting),
	'geometry.invalid': word(m.editor_error_geometry_invalid),
	'geometry.invalid_position': word(m.editor_error_geometry_invalid),
	'documentation.required': word(m.editor_error_documentation_required),
	'documentation.too_many_files': word(m.editor_error_documentation_too_many_files),
	'documentation.observed_required': word(m.editor_error_documentation_observed_required),
	'documentation.url_required': word(m.editor_error_documentation_url_required),
	'documentation.url_invalid': word(m.editor_error_url_invalid),
	'documentation.file_missing': word(m.editor_error_documentation_file_missing),
	'documentation.file_rejected': word(m.editor_error_documentation_file_rejected),
	'documentation.file_processing': word(m.editor_error_documentation_file_processing),
	'documentation.rights_required': word(m.editor_error_documentation_rights_required),
	'documentation.credit_required': word(m.editor_error_documentation_credit_required),
	'documentation.licence_required': word(m.editor_error_documentation_licence_required),
	'documentation.licence_not_allowed': word(m.editor_error_documentation_licence_not_allowed),
	'documentation.origin_required': word(m.editor_error_documentation_origin_required),
	'documentation.origin_invalid': word(m.editor_error_url_invalid),
	'documentation.alt_required': word(m.editor_error_documentation_alt_required),
	'documentation.alt_too_long': word(m.editor_error_documentation_alt_too_long),
	'condition.required': word(m.editor_error_condition_required),
	'artwork.title_required': word(m.editor_error_artwork_title_required),
	'artwork.expression_types_required': word(m.editor_error_artwork_expression_types_required),
	'artwork.expression_type_unknown': word(m.editor_error_artwork_expression_type_unknown),
	'series.name_required': word(m.editor_error_series_name_required),
	'attribution.choice_required': word(m.editor_error_attribution_choice_required),
	'attribution.required': word(m.editor_error_attribution_required),
	'attribution.artist_required': word(m.editor_error_attribution_artist_required),
	'attribution.artist_name_required': word(m.editor_error_attribution_artist_name_required),
	'attribution.artist_duplicated': word(m.editor_error_attribution_artist_duplicated),
	'attribution.certainty_required': word(m.editor_error_attribution_certainty_required),
	'attribution.confirmed_requires_citation': word(m.editor_error_attribution_confirmed_citation),
	'date.invalid': word(m.editor_error_date_invalid),
	'date.second_invalid': word(m.editor_error_date_invalid),
	'date.range_needs_exact': word(m.editor_error_date_range_needs_exact),
	'date.second_not_later': word(m.editor_error_date_second_not_later),
	'date.in_future': word(m.editor_error_date_in_future),
	'source.title_required': word(m.editor_error_source_title_required),
	'source.url_invalid': word(m.editor_error_url_invalid),
	'terms.required': word(m.editor_error_terms_required),
	'moderation.documentation_required': word(m.editor_error_documentation_required),
	'moderation.initial_condition_required': word(m.editor_error_condition_required),
	'moderation.terms_not_accepted': word(m.editor_error_terms_required),
	'moderation.submissions_limited': word(m.editor_error_submissions_limited),
	'moderation.drafts_limited': word(m.editor_error_drafts_limited),
	'moderation.uploads_limited': word(m.editor_error_uploads_limited),
	'moderation.outdated': word(m.editor_error_unavailable),
	'moderation.invalid_transition': word(m.editor_error_not_editable),
	'moderation.unknown_submission': word(m.editor_error_not_editable),
	'artwork.creation_event_duplicated': word(m.merge_error_creation_event_duplicated),
	'attribution.duplicate_artist': word(m.merge_error_attribution_duplicate_artist),
	'attribution.alias_not_of_artist': word(m.merge_error_alias_not_of_artist),
	'artist.alias_in_use': word(m.merge_error_alias_in_use),
	'crew_membership.duplicate': word(m.merge_error_crew_membership_duplicate),
	'crew_membership.cycle': word(m.merge_error_crew_membership_cycle),
	'duplicate_retirement.different_locations': word(m.merge_error_different_locations),
	'documentation_item.image_on_several_locations': word(m.merge_error_images_on_several_locations),
	'history_event.covering_itself': word(m.merge_error_covering_itself),
	'artwork.condition_changing_event_required': word(m.merge_error_condition_required),
	'merge.kind_mismatch': word(m.merge_error_kind_mismatch),
	'moderation.merge_kind_mismatch': word(m.merge_error_kind_mismatch),
	'merge.already_merged': word(m.merge_error_already_merged),
	'moderation.target_merged': word(m.merge_error_already_merged),
	'merge.not_public': word(m.merge_error_not_public),
	'moderation.target_withdrawn': word(m.merge_error_not_public),
	'unmerge.not_merged': word(m.merge_error_not_merged),
	'moderation.not_merged': word(m.merge_error_not_merged),
	'moderation.one_merge_required': word(m.merge_error_one_merge_required),
	file_too_large: word(m.editor_error_file_too_large),
	file_type_unsupported: word(m.editor_error_file_type_unsupported),
	file_unreadable: word(m.editor_error_file_unreadable),
	image_too_large: word(m.editor_error_image_too_large),
	network: word(m.editor_error_network),
	sign_in_required: word(m.editor_error_sign_in)
};

/** The error in words. `wait` is the time to wait of a rate limit, already worded. */
export function errorText(code: string, params: Params = {}): string {
	const message = messages[code];
	return message ? message(params) : m.editor_error_unknown({ code });
}
