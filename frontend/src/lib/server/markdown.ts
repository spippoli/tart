/**
 * Operator texts are Markdown (ADR 0009). micromark is CommonMark-compliant and
 * safe by default: raw HTML is escaped and only safe link protocols are kept.
 */
import { micromark } from 'micromark';

export function renderMarkdown(source: string): string {
	return micromark(source);
}
