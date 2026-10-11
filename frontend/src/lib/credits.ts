import manifest from '../../third-party-assets.json';
import type { Asset } from '../../scripts/assets';

/**
 * The courtesy credits of the About TART page, one per entry of the third-party
 * asset manifest, bundled at build time (ADR 0016).
 */
export const courtesyCredits: Pick<Asset, 'path' | 'credit' | 'licence' | 'source'>[] = (
	manifest.assets as Asset[]
).map(({ path, credit, licence, source }) => ({ path, credit, licence, source }));
