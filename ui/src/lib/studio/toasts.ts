import { writable } from 'svelte/store';

export type StudioToast = {
	id: string;
	title: string;
	description?: string;
	tone?: 'default' | 'success' | 'error';
};

export const studioToasts = writable<StudioToast[]>([]);

export function pushToast(toast: Omit<StudioToast, 'id'>): string {
	const id = crypto.randomUUID();
	studioToasts.update((current) => [...current, { ...toast, id }].slice(-4));
	setTimeout(() => dismissToast(id), 4200);
	return id;
}

export function dismissToast(id: string) {
	studioToasts.update((current) => current.filter((toast) => toast.id !== id));
}
