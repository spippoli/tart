import { expect, it } from 'vitest';
import { renderMarkdown } from './markdown';

it('renders Operator Markdown without passing raw HTML or unsafe links through', () => {
	expect(renderMarkdown('# Chi siamo\n\nUn *archivio*.')).toBe(
		'<h1>Chi siamo</h1>\n<p>Un <em>archivio</em>.</p>'
	);
	expect(renderMarkdown('<script>alert(1)</script>')).not.toContain('<script>');
	expect(renderMarkdown('[x](javascript:alert(1))')).not.toContain('javascript:');
});
