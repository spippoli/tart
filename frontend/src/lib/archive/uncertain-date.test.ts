import { describe, expect, it } from 'vitest';
import { locales, type Locale } from '#lib/paraglide/runtime.js';
import {
	formatPeriod,
	formatUncertainDate,
	precisionLabel,
	precisions,
	qualifierLabel,
	qualifiers,
	type KnownPrecision,
	type Qualifier,
	type UncertainDate
} from './uncertain-date';

const rome = { timeZone: 'Europe/Rome' };

// Fictional values; one per precision, each the first day of its unit.
const values: Record<KnownPrecision, string> = {
	day: '2016-03-12',
	month: '2016-03-01',
	year: '2016-01-01',
	decade: '1990-01-01'
};
const secondValues: Record<KnownPrecision, string> = {
	day: '2016-03-20',
	month: '2016-05-01',
	year: '2017-01-01',
	decade: '2000-01-01'
};

const knownPrecisions = precisions.filter((p): p is KnownPrecision => p !== 'unknown');

function format(date: UncertainDate, locale: Locale, timeZone = rome.timeZone): string {
	return formatUncertainDate(date, { locale, timeZone });
}

/** Every form a date can take: each precision x qualifier, the exact "from-to" form, unknown. */
function everyForm(): UncertainDate[] {
	const forms: UncertainDate[] = [{ precision: 'unknown' }];
	for (const precision of knownPrecisions) {
		for (const qualifier of qualifiers) {
			forms.push({ precision, qualifier, first: values[precision] });
		}
		forms.push({
			precision,
			qualifier: 'exact',
			first: values[precision],
			second: secondValues[precision]
		});
	}
	return forms;
}

const expected: Record<Locale, Record<KnownPrecision, Record<Qualifier | 'range', string>>> = {
	it: {
		day: {
			exact: '12 mar 2016',
			circa: '12 mar 2016 circa',
			before: 'prima del 12 mar 2016',
			after: 'dopo il 12 mar 2016',
			range: '12–20 mar 2016'
		},
		month: {
			exact: 'marzo 2016',
			circa: 'marzo 2016 circa',
			before: 'prima di marzo 2016',
			after: 'dopo marzo 2016',
			range: 'marzo–maggio 2016'
		},
		year: {
			exact: '2016',
			circa: '2016 circa',
			before: 'prima del 2016',
			after: 'dopo il 2016',
			range: '2016–2017'
		},
		decade: {
			exact: 'anni 1990',
			circa: 'anni 1990 circa',
			before: 'prima degli anni 1990',
			after: 'dopo gli anni 1990',
			range: 'anni 1990–2000'
		}
	},
	en: {
		day: {
			exact: 'Mar 12, 2016',
			circa: 'c. Mar 12, 2016',
			before: 'before Mar 12, 2016',
			after: 'after Mar 12, 2016',
			range: 'Mar 12 – 20, 2016'
		},
		month: {
			exact: 'March 2016',
			circa: 'c. March 2016',
			before: 'before March 2016',
			after: 'after March 2016',
			range: 'March – May 2016'
		},
		year: {
			exact: '2016',
			circa: 'c. 2016',
			before: 'before 2016',
			after: 'after 2016',
			range: '2016 – 2017'
		},
		decade: {
			exact: '1990s',
			circa: 'c. 1990s',
			before: 'before the 1990s',
			after: 'after the 1990s',
			range: '1990s–2000s'
		}
	}
};

// Intl puts thin and narrow no-break spaces around range dashes; compare them as plain spaces.
const plainSpaces = (text: string) => text.replace(/[\u2009\u202f\u00a0]/g, ' ');

describe('criterion 13: Uncertain date display', () => {
	describe.each(locales)('in %s', (locale) => {
		it.each(knownPrecisions.flatMap((p) => qualifiers.map((q) => [p, q] as const)))(
			'renders %s x %s through its own message',
			(precision, qualifier) => {
				const date: UncertainDate = { precision, qualifier, first: values[precision] };

				expect(plainSpaces(format(date, locale))).toBe(expected[locale][precision][qualifier]);
			}
		);

		it.each(knownPrecisions)('renders the exact %s "from-to" form', (precision) => {
			const date: UncertainDate = {
				precision,
				qualifier: 'exact',
				first: values[precision],
				second: secondValues[precision]
			};

			expect(plainSpaces(format(date, locale))).toBe(expected[locale][precision].range);
		});

		it('renders the unknown date', () => {
			expect(format({ precision: 'unknown' }, locale)).toBe(
				{ it: 'data sconosciuta', en: 'unknown date' }[locale]
			);
		});

		it('gives every form a distinct text', () => {
			const texts = everyForm().map((date) => format(date, locale));

			expect(new Set(texts).size).toBe(texts.length);
		});

		it('has a label for every precision and qualifier', () => {
			const labels = [
				...precisions.map((p) => precisionLabel(p, locale)),
				...qualifiers.map((q) => qualifierLabel(q, locale))
			];

			expect(labels.every((label) => label.length > 0)).toBe(true);
			expect(new Set(labels).size).toBe(labels.length);
		});
	});

	it.each(['Pacific/Kiritimati', 'Pacific/Pago_Pago', 'America/Los_Angeles', 'Asia/Tokyo'])(
		'formats a calendar day as that day in the Instance time zone %s',
		(timeZone) => {
			const date: UncertainDate = { precision: 'day', qualifier: 'exact', first: '2016-01-01' };

			expect(format(date, 'en', timeZone)).toBe('Jan 1, 2016');
		}
	);
});

describe('criterion 46: period display', () => {
	const start: UncertainDate = { precision: 'year', qualifier: 'circa', first: '2010-01-01' };
	const end: UncertainDate = { precision: 'year', qualifier: 'exact', first: '2015-01-01' };
	const context = { locale: 'en', ...rome } as const;

	it('shows a period with only a start as "from …"', () => {
		expect(formatPeriod({ start }, context)).toBe('from c. 2010');
		expect(formatPeriod({ start }, { ...context, locale: 'it' })).toBe('inizio: 2010 circa');
	});

	it('shows a period with only an end as "until …"', () => {
		expect(formatPeriod({ end }, context)).toBe('until 2015');
		expect(formatPeriod({ start: null, end }, { ...context, locale: 'it' })).toBe('fine: 2015');
	});

	it('shows both ends of a period', () => {
		expect(formatPeriod({ start, end }, context)).toBe('c. 2010 – 2015');
	});

	it('shows no period without a start and an end', () => {
		expect(formatPeriod({ start: null, end: null }, context)).toBeNull();
	});
});
