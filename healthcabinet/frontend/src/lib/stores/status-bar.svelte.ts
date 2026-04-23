/**
 * Reactive store for the AppShell status bar.
 *
 * Holds the raw status string and supporting fields. Localization of the
 * default `'Ready'` sentinel happens at the consumer (AppShell) so this
 * store stays pure and locale-agnostic — the prior design that stored a
 * pre-localized Ukrainian string would leave Ukrainian text frozen in
 * memory after a locale flip back to English (Review Round 2).
 */

const DEFAULT_STATUS_SENTINEL = 'Ready';

let _status = $state<string>(DEFAULT_STATUS_SENTINEL);
let _fields = $state<string[]>([]);

export const statusBarStore = {
	get status() {
		return _status;
	},
	get fields() {
		return _fields;
	},
	set(status: string, fields: string[]) {
		_status = status;
		_fields = fields;
	},
	reset() {
		_status = DEFAULT_STATUS_SENTINEL;
		_fields = [];
	}
};
