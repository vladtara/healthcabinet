import { createLogger, defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';

const defaultLogger = createLogger();

const isTanstackSvelteQueryWarning = (message: string) =>
	message.includes('"notifyManager" and "replaceEqualDeep"') &&
	message.includes('@tanstack/query-core') &&
	message.includes('createMutation.svelte.js') &&
	message.includes('useMutationState.svelte.js');

export default defineConfig({
	server: {
		port: parseInt(process.env.PORT ?? '5173'),
		host: process.env.HOST ?? 'localhost'
	},
	customLogger: {
		...defaultLogger,
		warn(msg, options) {
			if (isTanstackSvelteQueryWarning(msg)) {
				return;
			}

			defaultLogger.warn(msg, options);
		}
	},
	plugins: [tailwindcss(), sveltekit()],
	build: {
		rollupOptions: {
			onwarn(warning, defaultHandler) {
				const warningMessage = typeof warning.message === 'string' ? warning.message : '';
				const isTanstackUnusedExternalImport =
					warning.code === 'UNUSED_EXTERNAL_IMPORT' ||
					isTanstackSvelteQueryWarning(warningMessage);

				if (isTanstackUnusedExternalImport) {
					return;
				}

				defaultHandler(warning);
			}
		}
	},
	resolve: {
		conditions: ['browser']
	}
});
