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
	},
	{
		run_id: 'run-graph',
		name: 'SIR graph replay',
		status: 'completed',
		started_at: '2026-05-19T00:00:00Z',
		final_time: 2,
		plugins: ['sir_epidemic'],
		config_hash: 'def456',
		artifact_path: 'runs/run-graph',
		error_message: null
	},
	{
		run_id: 'run-market',
		name: 'Market stress replay',
		status: 'completed',
		started_at: '2026-05-19T00:00:00Z',
		final_time: 4,
		plugins: ['market_stress'],
		config_hash: 'market123',
		artifact_path: 'runs/run-market',
		error_message: null,
		plugin_semantics: [
			{
				name: 'market_stress',
				version: '0.1.0',
				semantics: {
					default_entity_type: 'sector',
					entity_schemas: {
						sector: [
							{ name: 'label', label: 'Sector', type: 'string' },
							{ name: 'mandate', label: 'Mandate', type: 'string' },
							{ name: 'liquidity_bucket', label: 'Liquidity bucket', type: 'categorical' }
						]
					},
					state_schema: {
						stable: { name: 'stable', label: 'Stable', kind: 'categorical' },
						watch: { name: 'watch', label: 'Watch', kind: 'categorical' },
						stressed: { name: 'stressed', label: 'Stressed', kind: 'categorical' }
					},
					metric_schema: {
						portfolio_stress_index: {
							name: 'portfolio_stress_index',
							label: 'Portfolio stress index',
							headline: true
						},
						correlation_pressure: {
							name: 'correlation_pressure',
							label: 'Correlation pressure',
							headline: true
						},
						cross_market_liquidity_pressure_estimate: {
							name: 'cross_market_liquidity_pressure_estimate',
							label: 'Cross-market liquidity pressure estimate',
							headline: true,
							unit: 'bps'
						},
						stress: { name: 'stress', label: 'Stress score' },
						beta: { name: 'beta', label: 'Beta' }
					},
					view_capabilities: [
						{ kind: 'matrix', default: true },
						{ kind: 'table' },
						{ kind: 'timeline' }
					],
					explanation_capabilities: [{ scope: 'run' }],
					preferred_view: 'matrix'
				}
			}
		]
	},
	{
		run_id: 'run-workflow',
		name: 'Dependency workflow replay',
		status: 'completed',
		started_at: '2026-05-19T00:00:00Z',
		final_time: 4,
		plugins: ['dependency_workflow'],
		config_hash: 'workflow123',
		artifact_path: 'runs/run-workflow',
		error_message: null,
		plugin_semantics: [
			{
				name: 'dependency_workflow',
				version: '0.1.0',
				semantics: {
					default_entity_type: 'service',
					entity_schemas: {
						service: [
							{ name: 'label', label: 'Service', type: 'string' },
							{ name: 'owner', label: 'Owner', type: 'string' },
							{ name: 'tier', label: 'Tier', type: 'categorical' }
						]
					},
					state_schema: {
						healthy: { name: 'healthy', label: 'Healthy', kind: 'categorical' },
						watch: { name: 'watch', label: 'Watch', kind: 'categorical' },
						blocked: { name: 'blocked', label: 'Blocked', kind: 'categorical' }
					},
					metric_schema: {
						delivery_risk_index: {
							name: 'delivery_risk_index',
							label: 'Delivery risk index',
							headline: true
						},
						blocked_items: { name: 'blocked_items', label: 'Blocked items', headline: true },
						cross_team_review_backlog_pressure: {
							name: 'cross_team_review_backlog_pressure',
							label: 'Cross-team review backlog pressure',
							headline: true
						},
						service_risk: { name: 'service_risk', label: 'Service risk' },
						review_backlog: { name: 'review_backlog', label: 'Review backlog' }
					},
					view_capabilities: [
						{ kind: 'hierarchy', default: true },
						{ kind: 'table' },
						{ kind: 'timeline' }
					],
					explanation_capabilities: [{ scope: 'run' }],
					preferred_view: 'hierarchy'
				}
			}
		]
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

// These two mocked runs are the smallest reliable set for run-page visual coverage:
// - run-market exercises dense numeric cards and alternate analysis surfaces.
// - run-workflow exercises hierarchy, narrative-heavy explanation, and inspector-heavy layouts.
const runPageVisualCoverage = ['run-market', 'run-workflow'] as const;

test.beforeEach(async ({ page }) => {
	await page.route('http://127.0.0.1:8787/health', async (route) => {
		await route.fulfill({ json: { status: 'ok', version: '0.1.0' } });
	});
	await page.route('http://127.0.0.1:8787/plugins', async (route) => {
		await route.fulfill({
			json: [
				{ name: 'sir_epidemic', version: '0.1.0', paradigm: 'graph' },
				{ name: 'heat_diffusion', version: '0.1.0', paradigm: 'pde' },
				{ name: 'market_stress', version: '0.1.0', paradigm: 'graph' },
				{ name: 'dependency_workflow', version: '0.1.0', paradigm: 'graph' }
			]
		});
	});
	await page.route('http://127.0.0.1:8787/examples', async (route) => {
		await route.fulfill({
			json: [
				{
					id: 'sir_epidemic',
					name: 'SIR baseline',
					description: 'Synthetic graph example'
				},
				{
					id: 'heat_diffusion',
					name: 'Heat baseline',
					description: '2D field example'
				},
				{
					id: 'heat_diffusion_large',
					name: 'Heat large demo',
					description: 'Large 2D field example'
				},
				{
					id: 'market_stress',
					name: 'Market stress demo',
					description: 'Synthetic sector-correlation example'
				},
				{
					id: 'dependency_workflow',
					name: 'Dependency workflow demo',
					description: 'Synthetic codebase dependency example'
				}
			]
		});
	});
	await page.route('http://127.0.0.1:8787/examples/sir_epidemic', async (route) => {
		await route.fulfill({
			json: {
				id: 'sir_epidemic',
				name: 'SIR baseline',
				description: 'Synthetic graph example',
				config: {
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
			}
		});
	});
	await page.route('http://127.0.0.1:8787/examples/heat_diffusion_large', async (route) => {
		await route.fulfill({
			json: {
				id: 'heat_diffusion_large',
				name: 'Heat large demo',
				description: 'Large 2D field example',
				config: {
					name: 'heat_diffusion_large_demo',
					seed: 42,
					scheduler: { t_end: 20, sync_interval: 0.05, demo_delay_ms_per_tick: 25 },
					solvers: [
						{
							type: 'pde',
							plugin: 'heat_diffusion',
							version: '>=0.1.0',
							params: {
								width: 96,
								height: 96,
								alpha: 0.2,
								dx: 1,
								dy: 1,
								initial_condition: 'gaussian',
								hotspot_temperature: 100,
								ambient_temperature: 0
							}
						}
					],
					observer: {
						metrics: ['temperature_min', 'temperature_max', 'temperature_mean'],
						emit_every: 0.25
					},
					storage: { artifacts_dir: 'runs', metrics: true, events: true },
					visualization: { emit_every: 0.25, inline_frame_max_values: 16384 }
				}
			}
		});
	});
	await page.route('http://127.0.0.1:8787/examples/heat_diffusion', async (route) => {
		await route.fulfill({
			json: {
				id: 'heat_diffusion',
				name: 'Heat baseline',
				description: '2D field example',
				config: {
					name: 'heat_diffusion_baseline',
					seed: 7,
					scheduler: { t_end: 1, sync_interval: 'auto' },
					solvers: [
						{
							type: 'field',
							plugin: 'heat_diffusion',
							version: '>=0.1.0',
							params: {
								grid_size: 12,
								diffusivity: 0.15,
								dt: 0.1
							}
						}
					],
					observer: { metrics: [], emit_every: 0.2 },
					storage: { artifacts_dir: 'runs', metrics: true, events: true },
					visualization: { emit_every: 0.2 }
				}
			}
		});
	});
	await page.route('http://127.0.0.1:8787/runs/run-a/events', async (route) => {
		await route.fulfill({ json: [{ t: 1, event_type: 'infection', node: 4 }] });
	});
	await page.route('http://127.0.0.1:8787/runs/created-run/events', async (route) => {
		await route.fulfill({ json: [] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-graph/events', async (route) => {
		await route.fulfill({ json: [{ t: 2, event_type: 'infection', node: 1 }] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-market/events', async (route) => {
		await route.fulfill({ json: [] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-workflow/events', async (route) => {
		await route.fulfill({ json: [] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-a/metrics', async (route) => {
		await route.fulfill({ json: metrics });
	});
	await page.route('http://127.0.0.1:8787/runs/created-run/metrics', async (route) => {
		await route.fulfill({ json: [] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-graph/metrics', async (route) => {
		await route.fulfill({ json: metrics });
	});
	await page.route('http://127.0.0.1:8787/runs/run-market/metrics', async (route) => {
		await route.fulfill({
			json: [
				{ t: 1, metric: 'portfolio_stress_index', value: 48 },
				{ t: 1, metric: 'correlation_pressure', value: 61 },
				{ t: 1, metric: 'cross_market_liquidity_pressure_estimate', value: 982450 },
				{ t: 2, metric: 'portfolio_stress_index', value: 56 },
				{ t: 2, metric: 'correlation_pressure', value: 67 },
				{ t: 2, metric: 'cross_market_liquidity_pressure_estimate', value: 1284500 }
			]
		});
	});
	await page.route('http://127.0.0.1:8787/runs/run-workflow/metrics', async (route) => {
		await route.fulfill({
			json: [
				{ t: 1, metric: 'delivery_risk_index', value: 42 },
				{ t: 1, metric: 'blocked_items', value: 1 },
				{ t: 1, metric: 'cross_team_review_backlog_pressure', value: 12 },
				{ t: 2, metric: 'delivery_risk_index', value: 58 },
				{ t: 2, metric: 'blocked_items', value: 2 },
				{ t: 2, metric: 'cross_team_review_backlog_pressure', value: 38 }
			]
		});
	});
	await page.route('http://127.0.0.1:8787/runs/run-a/fields', async (route) => {
		await route.fulfill({
			json: [{ field_id: 'temperature', name: 'temperature', shape: [1, 1], dtype: 'float64' }]
		});
	});
	await page.route('http://127.0.0.1:8787/runs/created-run/fields', async (route) => {
		await route.fulfill({ json: [] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-market/fields', async (route) => {
		await route.fulfill({ json: [] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-workflow/fields', async (route) => {
		await route.fulfill({ json: [] });
	});
	await page.route(/http:\/\/127\.0\.0\.1:8787\/runs\/run-a\/frames(\?.*)?$/, async (route) => {
		await route.fulfill({
			json: {
				metadata: {
					run_id: 'run-a',
					frame_count: 2,
					available_kinds: ['field'],
					t_min: 1,
					t_max: 2
				},
				frames: [
					{
						frame_id: 'frame-a',
						kind: 'field',
						t: 1,
						tick: 1,
						solver_id: 'heat#0',
						source: 'replay',
						payload_ref: { uri: 'frames/frames.jsonl', format: 'jsonl' }
					},
					{
						frame_id: 'frame-b',
						kind: 'field',
						t: 2,
						tick: 2,
						solver_id: 'heat#0',
						source: 'replay',
						payload_ref: { uri: 'frames/frames.jsonl', format: 'jsonl' }
					}
				]
			}
		});
	});
	await page.route('http://127.0.0.1:8787/runs/run-a/frames/frame-a', async (route) => {
		await route.fulfill({
			json: {
				kind: 'field',
				frame_id: 'frame-a',
				t: 1,
				tick: 1,
				solver_id: 'heat#0',
				source: 'replay',
				field: 'temperature',
				shape: [1, 1],
				dtype: 'float64',
				bounds: { min: 0, max: 1 },
				units: 'temperature',
				visualization: {},
				values: [0.4]
			}
		});
	});
	await page.route('http://127.0.0.1:8787/runs/run-a/frames/frame-b', async (route) => {
		await route.fulfill({
			json: {
				kind: 'field',
				frame_id: 'frame-b',
				t: 2,
				tick: 2,
				solver_id: 'heat#0',
				source: 'replay',
				field: 'temperature',
				shape: [1, 1],
				dtype: 'float64',
				bounds: { min: 0, max: 1 },
				units: 'temperature',
				visualization: {},
				values: [0.8]
			}
		});
	});
	await page.route(/http:\/\/127\.0\.0\.1:8787\/runs\/run-graph\/frames(\?.*)?$/, async (route) => {
		await route.fulfill({
			json: {
				metadata: {
					run_id: 'run-graph',
					frame_count: 1,
					available_kinds: ['graph'],
					t_min: 2,
					t_max: 2
				},
				frames: [
					{
						frame_id: 'sir-frame-a',
						kind: 'graph',
						t: 2,
						tick: 2,
						solver_id: 'sir#0',
						source: 'replay',
						payload_ref: { uri: 'frames/graph.jsonl', format: 'jsonl' }
					}
				]
			}
		});
	});
	await page.route(
		/http:\/\/127\.0\.0\.1:8787\/runs\/run-market\/frames(\?.*)?$/,
		async (route) => {
			await route.fulfill({
				json: {
					metadata: {
						run_id: 'run-market',
						frame_count: 1,
						available_kinds: ['graph'],
						t_min: 2,
						t_max: 2
					},
					frames: [
						{
							frame_id: 'market-frame-a',
							kind: 'graph',
							t: 2,
							tick: 2,
							solver_id: 'market#0',
							source: 'replay',
							payload_ref: { uri: 'frames/market.jsonl', format: 'jsonl' }
						}
					]
				}
			});
		}
	);
	await page.route('http://127.0.0.1:8787/runs/run-market/frames/market-frame-a', async (route) => {
		await route.fulfill({
			json: {
				kind: 'graph',
				frame_id: 'market-frame-a',
				t: 2,
				tick: 2,
				solver_id: 'market#0',
				source: 'replay',
				nodes: [
					{
						id: 'technology',
						label: 'Technology',
						group: 'growth',
						state: 'stressed',
						metrics: { stress: 0.81, beta: 1.24 },
						attrs: {
							mandate: 'Platform and software leaders',
							liquidity_bucket: 'mega_cap'
						}
					},
					{
						id: 'financials',
						label: 'Financials',
						group: 'core',
						state: 'watch',
						metrics: { stress: 0.58, beta: 0.97 },
						attrs: {
							mandate: 'Banks, exchanges, and lenders',
							liquidity_bucket: 'large_cap'
						}
					},
					{
						id: 'energy',
						label: 'Energy',
						group: 'cyclical',
						state: 'watch',
						metrics: { stress: 0.61, beta: 1.11 },
						attrs: {
							mandate: 'Producers exposed to commodity shocks',
							liquidity_bucket: 'large_cap'
						}
					},
					{
						id: 'industrials',
						label: 'Industrials',
						group: 'cyclical',
						state: 'stable',
						metrics: { stress: 0.38, beta: 0.89 },
						attrs: {
							mandate: 'Logistics and capital goods operators',
							liquidity_bucket: 'mid_cap'
						}
					}
				],
				edges: [
					{ source: 'technology', target: 'financials', weight: 0.82, kind: 'correlation' },
					{ source: 'technology', target: 'energy', weight: 0.74, kind: 'correlation' },
					{ source: 'technology', target: 'industrials', weight: 0.58, kind: 'correlation' },
					{ source: 'financials', target: 'energy', weight: 0.69, kind: 'correlation' },
					{ source: 'financials', target: 'industrials', weight: 0.63, kind: 'correlation' },
					{ source: 'energy', target: 'industrials', weight: 0.57, kind: 'correlation' }
				],
				visualization: {
					preferred_view: 'matrix',
					density_hint: 'dense',
					selection_schema: { type: 'node', entity_type: 'sector' }
				}
			}
		});
	});
	await page.route(
		/http:\/\/127\.0\.0\.1:8787\/runs\/run-workflow\/frames(\?.*)?$/,
		async (route) => {
			await route.fulfill({
				json: {
					metadata: {
						run_id: 'run-workflow',
						frame_count: 1,
						available_kinds: ['graph'],
						t_min: 2,
						t_max: 2
					},
					frames: [
						{
							frame_id: 'workflow-frame-a',
							kind: 'graph',
							t: 2,
							tick: 2,
							solver_id: 'workflow#0',
							source: 'replay',
							payload_ref: { uri: 'frames/workflow.jsonl', format: 'jsonl' }
						}
					]
				}
			});
		}
	);
	await page.route(
		'http://127.0.0.1:8787/runs/run-workflow/frames/workflow-frame-a',
		async (route) => {
			await route.fulfill({
				json: {
					kind: 'graph',
					frame_id: 'workflow-frame-a',
					t: 2,
					tick: 2,
					solver_id: 'workflow#0',
					source: 'replay',
					nodes: [
						{
							id: 'ingest',
							label: 'Ingest gateway',
							group: 'foundation',
							state: 'healthy',
							metrics: { service_risk: 0.24, review_backlog: 3 },
							attrs: { owner: 'Platform intake', tier: 'tier_0' }
						},
						{
							id: 'rules',
							label: 'Rules engine',
							group: 'decisioning',
							state: 'blocked',
							metrics: { service_risk: 0.81, review_backlog: 8 },
							attrs: { owner: 'Risk automation', tier: 'tier_1' }
						},
						{
							id: 'pricing',
							label: 'Pricing service',
							group: 'decisioning',
							state: 'watch',
							metrics: { service_risk: 0.58, review_backlog: 6 },
							attrs: { owner: 'Revenue systems', tier: 'tier_1' }
						}
					],
					edges: [
						{ source: 'ingest', target: 'rules', weight: 0.95, kind: 'depends_on', directed: true },
						{
							source: 'ingest',
							target: 'pricing',
							weight: 0.82,
							kind: 'depends_on',
							directed: true
						}
					],
					visualization: {
						preferred_view: 'hierarchy',
						selection_schema: { type: 'node', entity_type: 'service' }
					}
				}
			});
		}
	);
	await page.route('http://127.0.0.1:8787/runs/run-graph/frames/sir-frame-a', async (route) => {
		await route.fulfill({
			json: {
				kind: 'graph',
				frame_id: 'sir-frame-a',
				t: 2,
				tick: 2,
				solver_id: 'sir#0',
				source: 'replay',
				nodes: [
					{ id: '0', state: 'susceptible', x: 0, y: 0 },
					{ id: '1', state: 'infected', x: 1, y: 0 },
					{ id: '2', state: 'recovered', x: 0.5, y: 1 }
				],
				edges: [
					{ source: '0', target: '1', weight: 0.25 },
					{ source: '1', target: '2', weight: 1 }
				],
				visualization: {}
			}
		});
	});
	await page.route('http://127.0.0.1:8787/runs/run-a/frames/stream', async (route) => {
		await route.fulfill({
			contentType: 'text/event-stream',
			body: [
				'id: 1',
				'event: frame',
				'data: {"kind":"field","frame_id":"frame-c","t":3,"tick":3,"solver_id":"heat#0","source":"live","field":"temperature","shape":[1,1],"dtype":"float64","bounds":{"min":0,"max":1},"units":"temperature","visualization":{},"values":[0.9]}',
				'',
				'event: status',
				'data: {"run_id":"run-a","status":"completed"}',
				'',
				''
			].join('\n')
		});
	});
	await page.route('http://127.0.0.1:8787/runs/run-a/stream', async (route) => {
		await route.fulfill({
			contentType: 'text/event-stream',
			body: [
				'event: metric',
				'data: {"t":3,"metric":"infected_count","value":8}',
				'',
				'event: metric',
				'data: {"t":3,"metric":"recovered_count","value":2}',
				'',
				''
			].join('\n')
		});
	});
	await page.route('http://127.0.0.1:8787/runs/run-graph/stream', async (route) => {
		await route.fulfill({ contentType: 'text/event-stream', body: '\n\n' });
	});
	await page.route('http://127.0.0.1:8787/runs/run-market/frames/stream', async (route) => {
		await route.fulfill({ contentType: 'text/event-stream', body: '\n\n' });
	});
	await page.route('http://127.0.0.1:8787/runs/run-market/stream', async (route) => {
		await route.fulfill({ contentType: 'text/event-stream', body: '\n\n' });
	});
	await page.route('http://127.0.0.1:8787/runs/run-workflow/frames/stream', async (route) => {
		await route.fulfill({ contentType: 'text/event-stream', body: '\n\n' });
	});
	await page.route('http://127.0.0.1:8787/runs/run-workflow/stream', async (route) => {
		await route.fulfill({ contentType: 'text/event-stream', body: '\n\n' });
	});
	await page.route('http://127.0.0.1:8787/runs/created-run/frames/stream', async (route) => {
		await route.fulfill({ contentType: 'text/event-stream', body: '\n\n' });
	});
	await page.route('http://127.0.0.1:8787/runs/created-run/stream', async (route) => {
		await route.fulfill({ contentType: 'text/event-stream', body: '\n\n' });
	});
	await page.route('http://127.0.0.1:8787/runs/run-a', async (route) => {
		await route.fulfill({ json: runs[0] });
	});
	await page.route('http://127.0.0.1:8787/runs/created-run', async (route) => {
		await route.fulfill({ json: { ...runs[0], run_id: 'created-run', status: 'running' } });
	});
	await page.route('http://127.0.0.1:8787/runs/run-graph', async (route) => {
		await route.fulfill({ json: runs[1] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-market', async (route) => {
		await route.fulfill({ json: runs[2] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-workflow', async (route) => {
		await route.fulfill({ json: runs[3] });
	});
	await page.route('http://127.0.0.1:8787/runs/run-market/explanations/run', async (route) => {
		await route.fulfill({
			json: {
				run_id: 'run-market',
				scope: 'run',
				available: true,
				interpretation: {
					run_id: 'run-market',
					scope: 'run',
					t: 2,
					tick: 2,
					mode_requested: 'rules_only',
					mode_applied: 'rules_only',
					label: 'Market stress summary',
					cached: false,
					facts: [
						{
							kind: 'trend',
							title: 'Market stress remains clustered',
							summary:
								'Technology is leading the tape while cross-sector pressure remains elevated.',
							severity: 'warning',
							related_ids: ['technology'],
							t: 2,
							evidence: [{ label: 'portfolio_stress_index', value: 56, unit: 'idx' }]
						}
					],
					summary: {
						title: 'Market stress remains clustered',
						summary: 'Technology is leading the tape while cross-sector pressure remains elevated.',
						severity: 'warning',
						fact_count: 1,
						evidence: [{ label: 'portfolio_stress_index', value: 56, unit: 'idx' }]
					}
				}
			}
		});
	});
	await page.route('http://127.0.0.1:8787/runs/run-workflow/explanations/run', async (route) => {
		await route.fulfill({
			json: {
				run_id: 'run-workflow',
				scope: 'run',
				available: true,
				interpretation: {
					run_id: 'run-workflow',
					scope: 'run',
					t: 2,
					tick: 2,
					mode_requested: 'rules_only',
					mode_applied: 'rules_only',
					label: 'Workflow risk summary',
					cached: false,
					facts: [
						{
							kind: 'trend',
							title: 'Delivery risk is clustering on the critical path',
							summary:
								'Rules engine and downstream services are carrying the most blocker pressure.',
							severity: 'warning',
							related_ids: ['rules'],
							t: 2,
							evidence: [{ label: 'delivery_risk_index', value: 58, unit: 'idx' }]
						}
					],
					summary: {
						title: 'Delivery risk is clustering on the critical path',
						summary: 'Rules engine and downstream services are carrying the most blocker pressure.',
						severity: 'warning',
						fact_count: 1,
						evidence: [{ label: 'delivery_risk_index', value: 58, unit: 'idx' }]
					}
				}
			}
		});
	});
	await page.route('http://127.0.0.1:8787/sweeps', async (route) => {
		await route.fulfill({
			status: 201,
			json: {
				sweep_id: 'ui-sweep',
				name: 'UI sweep',
				parameter: 'solvers[0].params.p_infect',
				values: [0.2, 0.4],
				child_runs: [
					{ run_id: 'ui-sweep-001', value: 0.2, status: 'completed', artifact_path: 'runs/1' },
					{ run_id: 'ui-sweep-002', value: 0.4, status: 'completed', artifact_path: 'runs/2' }
				]
			}
		});
	});
	await page.route('http://127.0.0.1:8787/compare?**', async (route) => {
		await route.fulfill({
			json: {
				run_a: 'run-a',
				run_b: 'run-b',
				metric: 'infected_count',
				aligned: [
					{ t: 1, run_a: 3, run_b: 2 },
					{ t: 2, run_a: 4, run_b: 5 }
				],
				summaries: {
					'run-a': { peak: 4, final: 4, auc: 3.5 },
					'run-b': { peak: 5, final: 5, auc: 3.5 }
				}
			}
		});
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

async function pausePlaybackIfNeeded(page: import('@playwright/test').Page) {
	const pauseButton = page.getByRole('button', { name: 'Pause playback' });
	if (await pauseButton.isVisible().catch(() => false)) {
		await pauseButton.click();
	}
}

async function ensureTheme(page: import('@playwright/test').Page, theme: 'light' | 'dark') {
	const isDark = (await page.locator('html').getAttribute('class'))?.includes('dark') ?? false;
	if (theme === 'dark' && !isDark) {
		await page.getByRole('button', { name: 'Switch to dark mode' }).click();
	}
	if (theme === 'light' && isDark) {
		await page.getByRole('button', { name: 'Switch to light mode' }).click();
	}
}

test('renders the run dashboard with catalog rows', async ({ page }) => {
	await page.goto('/runs');

	await expect(page.getByRole('heading', { name: 'Runs' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'run-a' })).toBeVisible();
	await expect(page.getByRole('cell', { name: 'sir_epidemic' }).first()).toBeVisible();
});

test('opens on the Simulation Studio workbench', async ({ page }) => {
	await page.goto('/');

	await expect(page.getByRole('heading', { name: 'Simulation Studio' })).toBeVisible();
	await expect(page.getByRole('region', { name: 'Simulation playback viewport' })).toBeVisible();
	await expect(page.getByText('No run selected')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Create experiment' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Open run catalog' })).toBeVisible();
});

test('captures the Studio shell smoke state', async ({ page }) => {
	await page.goto('/runs');

	await expect(page.getByLabel('Primary navigation')).toBeVisible();
	await expect(page.getByLabel('Studio workspace')).toBeVisible();
	const screenshot = await page.screenshot();
	expect(screenshot.length).toBeGreaterThan(10_000);
});

test('renders run detail metrics and events', async ({ page }) => {
	await page.goto('/runs/run-a');

	await expect(page.getByRole('heading', { name: 'run-a' })).toBeVisible();
	await expect(page.getByLabel('Rendered simulation frame')).toBeVisible();
	await expect(page.getByRole('button', { name: 'Pause playback' })).toBeVisible();
	await expect(page.getByText(/Frame buffer \d+/)).toBeVisible();
	await expect
		.poll(async () =>
			page.getByLabel('Rendered simulation frame').evaluate((canvas) => ({
				width: (canvas as HTMLCanvasElement).width,
				height: (canvas as HTMLCanvasElement).height
			}))
		)
		.toMatchObject({ width: expect.any(Number), height: expect.any(Number) });
	const canvasSize = await page.getByLabel('Rendered simulation frame').evaluate((canvas) => ({
		width: (canvas as HTMLCanvasElement).width,
		height: (canvas as HTMLCanvasElement).height
	}));
	expect(canvasSize.width).toBeGreaterThan(100);
	expect(canvasSize.height).toBeGreaterThan(100);
	await expect(page.getByLabel('Key metric cards').getByText('Infected count')).toBeVisible();
	await expect(page.getByText('Peak value')).toBeVisible();
	await expect(page.getByText('Final value')).toBeVisible();
	await expect(page.getByLabel('Metric timeline').first()).toBeVisible();
	await page.getByRole('tab', { name: 'Artifacts' }).click();
	await expect(page.getByRole('link', { name: 'CSV export' }).first()).toHaveAttribute(
		'href',
		/http:\/\/127\.0\.0\.1:8787\/runs\/run-a\/export\?format=csv/
	);
	await expect(page.getByRole('link', { name: 'Parquet export' }).first()).toBeVisible();
	await expect(page.getByRole('link', { name: 'Compare this run' }).first()).toBeVisible();
	await page.getByRole('tab', { name: 'Events' }).click();
	await expect(page.getByRole('cell', { name: 'infection', exact: true })).toBeVisible();
	await page.getByRole('tab', { name: 'Logs' }).click();
	await expect(page.getByRole('cell', { name: 'metric stream' })).toBeVisible();
});

test('renders SIR graph replay frames and supports node inspection', async ({ page }) => {
	await page.goto('/runs/run-graph');

	const canvas = page.getByLabel('Rendered simulation frame');
	await expect(canvas).toBeVisible();
	const canvasBox = await canvas.boundingBox();
	expect(canvasBox).not.toBeNull();
	await page.mouse.click(
		canvasBox!.x + canvasBox!.width / 2,
		canvasBox!.y + canvasBox!.height - 36
	);
	const screenshot = await page.screenshot();
	expect(screenshot.length).toBeGreaterThan(10_000);
});

test('adapts the shared run page across market and workflow semantic domains', async ({ page }) => {
	await page.goto('/runs/run-market');

	await expect(page.getByText('What is happening now')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'View guide' })).toBeVisible();
	await expect(page.locator('option[value="matrix"]')).toHaveText('Matrix');
	await expect(page.getByText('Market stress remains clustered').first()).toBeVisible();
	await page.getByRole('combobox').selectOption('table');
	await expect(page.getByRole('button', { name: 'Technology Stressed' })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Financials Watch' })).toBeVisible();

	await page.goto('/runs/run-workflow');

	await expect(page.locator('option[value="hierarchy"]')).toHaveText('Hierarchy');
	await expect(
		page.getByText('Delivery risk is clustering on the critical path').first()
	).toBeVisible();
	await page.getByRole('combobox').selectOption('hierarchy');
	await expect(page.getByRole('button', { name: 'Rules engine Blocked' })).toBeVisible();
	await expect(page.getByRole('button', { name: 'Ingest gateway Healthy' })).toBeVisible();
	await expect(page.getByText('Best when').first()).toBeVisible();
	await expect(page.getByText('Fallback').first()).toBeVisible();
});

test('prioritizes the run story, key metrics, and next step before technical detail', async ({
	page
}) => {
	await page.goto('/runs/run-workflow');
	await pausePlaybackIfNeeded(page);

	await expect(page.getByText('What is happening now')).toBeVisible();
	await expect(page.getByText('Why it matters')).toBeVisible();
	await expect(page.getByText('What to inspect next')).toBeVisible();
	await expect(page.getByText('Key metrics')).toBeVisible();
	await expect(page.getByText('Technical details')).toBeVisible();
});

test('keeps metric cards readable with long labels and large values at tablet widths', async ({
	page
}) => {
	await page.setViewportSize({ width: 1024, height: 1366 });
	await page.goto('/runs/run-market');
	await pausePlaybackIfNeeded(page);

	await expect(
		page
			.getByLabel('Key metric cards')
			.getByText('Cross-market liquidity pressure estimate')
			.first()
	).toBeVisible();
	await expect(page.getByText(/1\.28M|1,284,500/).first()).toBeVisible();
	await expect(page.getByLabel('Key metric cards')).toHaveScreenshot(
		'run-market-metric-cards-tablet.png'
	);
});

test('keeps the analysis workspace free of horizontal overflow across supported widths', async ({
	page
}) => {
	for (const viewport of [
		{ name: 'desktop', width: 1536, height: 960 },
		{ name: 'laptop', width: 1280, height: 900 },
		{ name: 'tablet', width: 1024, height: 1366 }
	]) {
		await page.setViewportSize({ width: viewport.width, height: viewport.height });
		await page.goto('/runs/run-workflow');
		await pausePlaybackIfNeeded(page);
		await ensureTheme(page, 'light');
		await expect
			.poll(
				() =>
					page.evaluate(() => ({
						scrollWidth: document.documentElement.scrollWidth,
						clientWidth: document.documentElement.clientWidth
					})),
				{ message: `${viewport.name} viewport should not overflow horizontally` }
			)
			.toEqual({ scrollWidth: viewport.width, clientWidth: viewport.width });
	}
});

test('supports theme switching for the analysis workspace', async ({ page }) => {
	await page.goto('/runs/run-workflow');
	await pausePlaybackIfNeeded(page);
	await ensureTheme(page, 'light');

	await expect(page.locator('html')).not.toHaveClass(/dark/);
	await page.getByRole('button', { name: 'Switch to dark mode' }).click();
	await expect(page.locator('html')).toHaveClass(/dark/);
	await page.getByRole('button', { name: 'Switch to light mode' }).click();
	await expect(page.locator('html')).not.toHaveClass(/dark/);
});

test('captures representative run-page visual baselines in light and dark themes', async ({
	page
}) => {
	await page.setViewportSize({ width: 1280, height: 900 });

	for (const runId of runPageVisualCoverage) {
		await page.goto(`/runs/${runId}`);
		await pausePlaybackIfNeeded(page);
		await ensureTheme(page, 'light');
		await expect(page.getByLabel('Studio workspace')).toHaveScreenshot(`${runId}-light.png`);

		await ensureTheme(page, 'dark');
		await expect(page.getByLabel('Studio workspace')).toHaveScreenshot(`${runId}-dark.png`);
	}
});

test('submits an example experiment config', async ({ page }) => {
	await page.goto('/experiments');
	await expect(page.getByText('Plugin selection')).toBeVisible();
	await expect(page.getByRole('tab', { name: /Parameters/ })).toBeVisible();
	await expect(page.getByLabel('Experiment name')).toBeVisible();
	await page.getByRole('button', { name: 'Run experiment' }).click();

	await expect(page).toHaveURL(/\/runs\/created-run$/);
	await expect(page.getByRole('heading', { name: 'created-run' })).toBeVisible();
	await expect(page.getByText('Run started')).toBeVisible();
});

test('selects installed plugins from the experiment builder', async ({ page }) => {
	await page.goto('/experiments');

	await page.getByRole('button', { name: /heat_diffusion.*pde/ }).click();

	await expect(page.getByLabel('Experiment name')).toHaveValue('heat_diffusion_baseline');
	await expect(page.getByLabel('Primary plugin')).toHaveValue('heat_diffusion');
	await expect(page.getByText('Diffusivity', { exact: true })).toBeVisible();
});

test('loads the large heat demo preset from the experiment builder', async ({ page }) => {
	await page.goto('/experiments');

	await page.getByRole('button', { name: 'Heat large demo' }).click();

	await expect(page.getByLabel('Experiment name')).toHaveValue('heat_diffusion_large_demo');
	await expect(page.getByLabel('Primary plugin')).toHaveValue('heat_diffusion');
	await expect(page.getByText('Demo delay per tick', { exact: true })).toBeVisible();
	await expect(page.getByText('solvers[0].params.width')).toBeVisible();
});

test('shows validation for invalid experiment payloads', async ({ page }) => {
	await page.goto('/experiments');
	await page.getByRole('tab', { name: /Advanced JSON/ }).click();
	await page.getByLabel('Run payload').fill('{}');

	await expect(page.getByText('Experiment name is required.')).toBeVisible();
	await expect(page.getByRole('button', { name: 'Run experiment' })).toBeDisabled();
});

test('creates a scalar parameter sweep', async ({ page }) => {
	await page.goto('/sweeps');
	await page.getByLabel('Parameter path').fill('solvers[0].params.p_infect');
	await page.getByLabel('Sweep values').fill('0.2, 0.4');
	await page.getByRole('button', { name: 'Run sweep' }).click();

	await expect(page.getByText('ui-sweep', { exact: true })).toBeVisible();
	await expect(page.getByRole('link', { name: 'ui-sweep-001' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Compare to baseline' })).toBeVisible();
	await expect(page.getByText('Frame comparison workspace')).toBeVisible();
});

test('compares two runs with an overlay chart', async ({ page }) => {
	await page.goto('/compare');
	await page.getByLabel('Run A').fill('run-a');
	await page.getByLabel('Run B').fill('run-b');
	await page.getByLabel('Metric').fill('infected_count');
	await page.getByRole('button', { name: 'Compare runs' }).click();

	await expect(page.getByText('infected_count')).toBeVisible();
	await expect(page.getByRole('cell', { name: 'run-a' })).toBeVisible();
	await expect(page.getByText('AUC')).toBeVisible();
	await expect(page.getByText('Frame comparison placeholder')).toBeVisible();
});

test('opens command palette from the Studio shell', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('button', { name: 'Command' }).click();

	await expect(page.getByRole('heading', { name: 'Command palette' })).toBeVisible();
	await expect(
		page.getByLabel('Command palette').getByRole('link', { name: 'Runs' })
	).toBeVisible();
});
