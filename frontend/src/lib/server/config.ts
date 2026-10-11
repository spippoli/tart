import { api } from './api';
import { createInstanceConfigReader, type PublicConfiguration } from './instance-config';

let reader: (() => Promise<PublicConfiguration>) | undefined;

/** The public Instance configuration of this process, read from the API (`API_URL`) and cached. */
export function readInstanceConfig(): Promise<PublicConfiguration> {
	reader ??= createInstanceConfigReader(api());
	return reader();
}
