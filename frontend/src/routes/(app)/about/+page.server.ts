import { renderMarkdown } from '#lib/server/markdown.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ locals }) => {
	const { texts } = locals.config;
	return {
		aboutHtml: texts.about === null ? null : renderMarkdown(texts.about),
		hasGuidelines: texts.editorial_guidelines !== null,
		hasContributionPolicy: texts.contribution_policy !== null
	};
};
