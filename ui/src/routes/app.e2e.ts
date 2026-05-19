import { expect, test } from '@playwright/test';

const runs = [
	{
		run_id: 'run-a',
		name: 'SIR baseline',
		status: 'completed',
		started_at: '2026-05-19T00:00:00Z',
		final_time: 24,
		plugins: ['sir_epidemic'],
		config_hash: 'abc123',
		artifact_path: 'runs/run-a',
		error_message: null
	}
];

const metrics = [
	{ t: 1, metric: 'susceptible_count', value: 17 },
	{ t: 1, metric: 'infected_count', value: 3 },
	{ t: 1, metric: 'recovered_count', value: 0 },
	{ t: 2, metric: 'susceptible_count', value: 16 },
	{ t: 2, metric: 'infected_count', value: 4 },
	{ t: 2, metric: 'recovered_count', value: 0 }
];

test.beforeEach(async ({ page }) => {
	await page.route('http://127.0.0.1:8787/health', async (route) => {
		await route.fulfill({ json: { status: 'ok', version: '0.1.0' } });
	});
	await page.route('http://127.0.0.1:8787/plugins', async (route) => {
		await route.fulfill({ json: [{ name: 'sir_epidemic', version: '0.1.0', paradigm: 'graph' }] });
	});
	await page.route('http://127.0.0.1:8787/examples/sir_epidemic', async (route) => {
		await route.fulfill({
			json: {
				name: 'sir_epidemic_baseline',
				seed: 42,
				scheduler: { t_end: 24, sync_interval: 'auto' },
				solvers: [
					{
						type: 'graph',
						plugin: 'sir_epidemic',
						version: '>=0.1.0',
						params: {
							contact_graph: 'configs/examples/data/sir_contact_edges.csv',
							n_nodes: 20,
							initially_infected: [0, 10],
							p_infect: 0.6,
							p_recover: 0.08
						}
					}
				],
				observer: { metrics: [], emit_every: 1 },
				storage: { artifacts_dir: 'runs', metrics: true, events: true }
			}
		});
	});
	await page.route('http://127.0.0.1:8787/runs/run-a/events', async (route) => {
		await route.fulfill({ json: [{ t: 1, event_type: 'infection', node: 4 }] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-a/metrics', async (route) => {
		await route.fulfill({ json: metrics });
	});
	await page.route('http://127.0.0.1:8787/runs/run-a', async (route) => {
		await route.fulfill({ json: runs[0] });
	});
	await page.route('http://127.0.0.1:8787/runs', async (route) => {
		if (route.request().method() === 'POST') {
			await route.fulfill({
				status: 202,
				json: { ...runs[0], run_id: 'created-run', status: 'running' }
			});
			return;
		}
		await route.fulfill({ json: runs });
	});
});

test('renders the run dashboard with catalog rows', async ({ page }) => {
	await page.goto('/runs');

	await expect(page.getByRole('heading', { name: 'Runs' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'run-a' })).toBeVisible();
	await expect(page.getByText('sir_epidemic')).toBeVisible();
});

test('renders run detail metrics and events', async ({ page }) => {
	await page.goto('/runs/run-a');

	await expect(page.getByRole('heading', { name: 'run-a' })).toBeVisible();
	await expect(page.getByText('infected_count')).toBeVisible();
	await page.getByRole('tab', { name: 'Events' }).click();
	await expect(page.getByText('infection', { exact: true })).toBeVisible();
});

test('submits the bundled SIR experiment config', async ({ page }) => {
	await page.goto('/experiments');
	await page.getByLabel('Seed').fill('77');
	await page.getByLabel('Infection probability').fill('0.45');
	await page.getByRole('button', { name: 'Run experiment' }).click();

	await expect(page.getByText('created-run')).toBeVisible();
});
