export const DEFAULT_NEAR_BOTTOM_THRESHOLD_PX = 24;

// scrollTop can be fractional while scrollHeight / clientHeight are rounded,
// so bottom detection uses a threshold instead of exact equality.
// https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollHeight
export function isNearBottom(
	el: HTMLElement | null | undefined,
	thresholdPx: number = DEFAULT_NEAR_BOTTOM_THRESHOLD_PX
): boolean {
	if (!el) return true;
	const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
	return distanceFromBottom <= thresholdPx;
}
