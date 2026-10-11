import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ locals }) => ({
	operatorName: locals.config.operator_name,
	contacts: locals.config.contacts
});
