type BadgeVariant = 'default' | 'info' | 'success' | 'warning' | 'danger';

const STATUS_MAP: Record<string, { variant: BadgeVariant; label: string }> = {
	active: { variant: 'success', label: 'Active' },
	suspended: { variant: 'danger', label: 'Suspended' },
	pending: { variant: 'warning', label: 'Pending' },
	deactivated: { variant: 'default', label: 'Deactivated' }
};

const FALLBACK = { variant: 'default' as BadgeVariant, label: 'Unknown' };

export function accountStatusVariant(status: string): BadgeVariant {
	return (STATUS_MAP[status] ?? FALLBACK).variant;
}

export function accountStatusLabel(status: string): string {
	return (STATUS_MAP[status] ?? FALLBACK).label;
}
