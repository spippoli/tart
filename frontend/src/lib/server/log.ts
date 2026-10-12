/**
 * Structured logs (Operations and portability spec, 5. Monitoring): one JSON object
 * per line on stdout, as `api` and `worker` write them. A line never carries an email
 * address, a sign-in code, a token, or Notice content: callers pass no request data
 * but the path, and any email address left in a message is replaced.
 */

export const REDACTED = '[redacted]';
const EMAIL = /[^\s@<>()[\]"',;:]+@[^\s@<>()[\]"',;:]+\.[A-Za-z]{2,}/g;

export type LogFields = Record<string, string | number | boolean | null>;

export function logLine(
	level: 'info' | 'warning' | 'error',
	message: string,
	fields: LogFields = {},
	now: Date = new Date()
): string {
	const entry = { time: now.toISOString(), level, logger: 'frontend', message, ...fields };
	return JSON.stringify(entry).replace(EMAIL, REDACTED);
}

export function log(level: 'info' | 'warning' | 'error', message: string, fields?: LogFields) {
	process.stdout.write(logLine(level, message, fields) + '\n');
}
