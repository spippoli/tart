/**
 * The Uncertain date input of the editor (Contribution and moderation spec, Common
 * rules): a qualifier, a precision, one value or two (a "from-to" range, with `exact`
 * only), and a separate "Unknown date" choice. The field keeps what the person typed,
 * as the native inputs give it; this module turns it into the archive's Uncertain date
 * and back. The archive (backend) owns the real validation; the checks here only say,
 * in the form, what the server would refuse.
 */
import type { KnownPrecision, Qualifier, UncertainDate } from '#lib/archive/uncertain-date.ts';

export interface DateField {
	/** "Unknown date": precision `unknown`, with no value and no qualifier. */
	unknown: boolean;
	qualifier: Qualifier;
	precision: KnownPrecision;
	/** The value as the input gives it: `2016-03-12`, `2016-03`, or `2016`. */
	first: string;
	second: string;
}

export function emptyDate(): DateField {
	return { unknown: false, qualifier: 'exact', precision: 'day', first: '', second: '' };
}

export type DateProblem =
	'invalid' | 'second_invalid' | 'range_needs_exact' | 'second_not_later' | 'in_future';

export type DateOutcome =
	| { date: UncertainDate | null }
	| { date: null; problem: DateProblem; field: 'first' | 'second' | 'qualifier' };

/** Whether nothing was entered in the field. */
export function isEmptyDate(field: DateField): boolean {
	return !field.unknown && field.first.trim() === '' && field.second.trim() === '';
}

const PATTERNS: Record<KnownPrecision, RegExp> = {
	day: /^(\d{4})-(\d{2})-(\d{2})$/,
	month: /^(\d{4})-(\d{2})$/,
	year: /^(\d{4})$/,
	decade: /^(\d{4})$/
};

/** The ISO date of the first day of the unit a value names, or null if it names none. */
function firstDay(precision: KnownPrecision, text: string): string | null {
	const found = PATTERNS[precision].exec(text.trim());
	if (!found) return null;
	const year = Number(found[1]);
	if (year < 1000) return null;
	const pad = (value: number) => String(value).padStart(2, '0');
	switch (precision) {
		case 'decade':
			return `${Math.floor(year / 10) * 10}-01-01`;
		case 'year':
			return `${year}-01-01`;
		case 'month': {
			const month = Number(found[2]);
			return month >= 1 && month <= 12 ? `${year}-${pad(month)}-01` : null;
		}
		case 'day': {
			const month = Number(found[2]);
			const day = Number(found[3]);
			const date = new Date(Date.UTC(year, month - 1, day));
			const real =
				date.getUTCFullYear() === year &&
				date.getUTCMonth() === month - 1 &&
				date.getUTCDate() === day;
			return real ? `${year}-${pad(month)}-${pad(day)}` : null;
		}
	}
}

/**
 * The Uncertain date of a field. `today` is the date of the Submission (ISO, in the
 * Instance time zone): a value after it is refused, as the archive refuses it.
 */
export function toUncertainDate(field: DateField, today: string): DateOutcome {
	if (field.unknown) return { date: { precision: 'unknown' } };
	if (isEmptyDate(field)) return { date: null };
	const first = firstDay(field.precision, field.first);
	if (first === null) return { date: null, problem: 'invalid', field: 'first' };
	if (first > today) return { date: null, problem: 'in_future', field: 'first' };
	if (field.second.trim() === '') {
		return {
			date: { precision: field.precision, qualifier: field.qualifier, first, second: null }
		};
	}
	if (field.qualifier !== 'exact') {
		return { date: null, problem: 'range_needs_exact', field: 'qualifier' };
	}
	const second = firstDay(field.precision, field.second);
	if (second === null) return { date: null, problem: 'second_invalid', field: 'second' };
	if (second <= first) return { date: null, problem: 'second_not_later', field: 'second' };
	if (second > today) return { date: null, problem: 'in_future', field: 'second' };
	return { date: { precision: field.precision, qualifier: 'exact', first, second } };
}

/** What a native input shows for an ISO first day at a precision. */
function inputValue(precision: KnownPrecision, iso: string): string {
	switch (precision) {
		case 'day':
			return iso;
		case 'month':
			return iso.slice(0, 7);
		default:
			return iso.slice(0, 4);
	}
}

/** The field of an Uncertain date as stored. */
export function fromUncertainDate(date: UncertainDate | null | undefined): DateField {
	if (!date) return emptyDate();
	if (date.precision === 'unknown') return { ...emptyDate(), unknown: true };
	return {
		unknown: false,
		qualifier: date.qualifier,
		precision: date.precision,
		first: inputValue(date.precision, date.first),
		second: date.second ? inputValue(date.precision, date.second) : ''
	};
}

/** The Submission's date: today, in the Instance time zone, as an ISO date. */
export function todayIn(timeZone: string, now: Date = new Date()): string {
	const parts = new Intl.DateTimeFormat('en-CA', {
		timeZone,
		year: 'numeric',
		month: '2-digit',
		day: '2-digit'
	}).format(now);
	return parts;
}
