/**
 * The Data licences an Instance may choose (ADR 0009; the list is validated by the
 * backend) with their short labels, canonical URLs, and translated full names.
 */
import { m } from '#lib/paraglide/messages.js';
import type { Locale } from '#lib/paraglide/runtime.js';

interface Licence {
	/** The licence's own abbreviation, the same in every UI language. */
	label: string;
	url: string;
	name: (inputs: object, options: { locale: Locale }) => string;
}

const licences: Record<string, Licence> = {
	'CC0-1.0': {
		label: 'CC0 1.0',
		url: 'https://creativecommons.org/publicdomain/zero/1.0/',
		name: m.licence_cc0_1_0
	},
	'CC-BY-4.0': {
		label: 'CC BY 4.0',
		url: 'https://creativecommons.org/licenses/by/4.0/',
		name: m.licence_cc_by_4_0
	},
	'CC-BY-SA-4.0': {
		label: 'CC BY-SA 4.0',
		url: 'https://creativecommons.org/licenses/by-sa/4.0/',
		name: m.licence_cc_by_sa_4_0
	},
	'ODbL-1.0': {
		label: 'ODbL 1.0',
		url: 'https://opendatacommons.org/licenses/odbl/1-0/',
		name: m.licence_odbl_1_0
	}
};

export interface LicenceDisplay {
	label: string;
	name: string;
	url: string;
}

/** A licence by SPDX identifier; an unknown one shows its identifier and SPDX page. */
export function licence(spdx: string, locale: Locale): LicenceDisplay {
	const known = licences[spdx];
	if (known === undefined) {
		return { label: spdx, name: spdx, url: `https://spdx.org/licenses/${spdx}.html` };
	}
	return { label: known.label, name: known.name({}, { locale }), url: known.url };
}
