import { error } from '@sveltejs/kit';
import { renderMarkdown } from '#lib/server/markdown.ts';
import type { PageServerLoad } from './$types';

/** An optional Operator text: without it, the page does not exist. */
export const load: PageServerLoad = ({ locals }) => {
	const markdown = locals.config.texts.editorial_guidelines;
	if (markdown === null) error(404);
	return { html: renderMarkdown(markdown) };
};
