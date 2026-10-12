import { describe, expect, it } from 'vitest';
import { logLine, REDACTED } from './log';

// Operations and portability criterion 19: structured JSON, no email addresses.
describe('a frontend log line', () => {
	it('is one JSON object with time, level, logger, and message', () => {
		const line = logLine(
			'error',
			'Internal Error',
			{ status: 500, path: '/it/mappa' },
			new Date(0)
		);

		expect(line).not.toContain('\n');
		expect(JSON.parse(line)).toEqual({
			time: '1970-01-01T00:00:00.000Z',
			level: 'error',
			logger: 'frontend',
			message: 'Internal Error',
			status: 500,
			path: '/it/mappa'
		});
	});

	it('never carries an email address', () => {
		const line = logLine('error', 'refused for person@example.org');

		expect(line).not.toContain('person@example.org');
		expect(JSON.parse(line).message).toBe(`refused for ${REDACTED}`);
	});
});
