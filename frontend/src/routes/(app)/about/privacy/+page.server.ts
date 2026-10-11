import { renderMarkdown } from '#lib/server/markdown.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ locals }) => ({
	html: renderMarkdown(locals.config.texts.privacy)
});
