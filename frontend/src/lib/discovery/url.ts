import { goto } from '$app/navigation';
import { page } from '$app/state';

/**
 * The URL the visitor sees. Explore changes the selection and the viewport without a
 * load (shallow routing), and then `page.url` is still the URL of the last load.
 */
export function currentUrl(): { search: string; pathname: string } {
	return page.shallow?.url ?? page.url;
}

/**
 * Changes the URL without loading the page again. `replace` writes over the current
 * history entry; without it the change is one step Back undoes.
 */
export function shallow(url: string, options: { replace: boolean; state?: App.PageState }) {
	// The URL is a path of this app.
	// eslint-disable-next-line svelte/no-navigation-without-resolve
	return goto(url, { shallow: true, replace: options.replace, state: options.state ?? {} });
}
