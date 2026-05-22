import { describe, expect, test, vi } from 'vitest';

import {
	PersephoneApiClient,
	type ExplanationResponse,
	type FrameListResponse,
	type PluginSemantics
} from './index';

describe('PersephoneApiClient frame contracts', () => {
	test('loads replay frames through typed client methods', async () => {
		const fixture: FrameListResponse = {
			metadata: {
				run_id: 'run-a',
				frame_count: 1,
				available_kinds: ['field'],
				t_min: 0.1,
				t_max: 0.1
			},
			frames: [
				{
					frame_id: 'solver:field:1',
					kind: 'field',
					t: 0.1,
					tick: 1,
					solver_id: 'solver',
					source: 'live',
					payload_ref: { uri: 'frames/frames.jsonl', format: 'jsonl' }
				}
			]
		};
		const fetcher = vi.fn(async () => new Response(JSON.stringify(fixture)));
		const api = new PersephoneApiClient('http://api.local', fetcher);

		const frames = await api.listFrames('run-a', { kind: 'field', maxCount: 10 });

		expect(fetcher).toHaveBeenCalledWith(
			'http://api.local/runs/run-a/frames?kind=field&max_count=10',
			{ headers: { accept: 'application/json' } }
		);
		expect(frames.frames[0]?.kind).toBe('field');
		expect(api.frameStreamUrl('run-a')).toBe('http://api.local/runs/run-a/frames/stream');
		expect(api.exportRunUrl('run-a', 'parquet')).toBe(
			'http://api.local/runs/run-a/export?format=parquet'
		);
		expect(api.frameUrl('run-a', 'frame-a')).toBe('http://api.local/runs/run-a/frames/frame-a');
	});

	test('loads plugin semantics and explanation summaries through typed client methods', async () => {
		const fetcher = vi
			.fn()
			.mockImplementationOnce(
				async () =>
					new Response(
						JSON.stringify({
							name: 'demo',
							version: '0.1.0',
							semantics: {
								view_capabilities: [{ kind: 'table', default: true }],
								preferred_view: 'table'
							}
						} satisfies PluginSemantics)
					)
			)
			.mockImplementationOnce(
				async () =>
					new Response(
						JSON.stringify({
							run_id: 'run-a',
							scope: 'run',
							available: true,
							interpretation: {
								run_id: 'run-a',
								scope: 'run',
								t: 1,
								tick: 1,
								mode_requested: 'rules_only',
								mode_applied: 'rules_only',
								label: 'Deterministic interpretation',
								cached: false,
								facts: [],
								summary: {
									title: 'Population is rising',
									summary: 'Population increased above baseline.',
									severity: 'warning',
									evidence: [],
									fact_count: 1
								}
							}
						} satisfies ExplanationResponse)
					)
			);
		const api = new PersephoneApiClient('http://api.local', fetcher);

		const semantics = await api.getPluginSemantics('demo');
		const explanation = await api.getRunExplanation('run-a');

		expect(fetcher).toHaveBeenNthCalledWith(1, 'http://api.local/plugins/demo/semantics', {
			headers: { accept: 'application/json' }
		});
		expect(fetcher).toHaveBeenNthCalledWith(2, 'http://api.local/runs/run-a/explanations/run', {
			headers: { accept: 'application/json' }
		});
		expect(semantics.semantics.preferred_view).toBe('table');
		expect(explanation.interpretation?.mode_applied).toBe('rules_only');
	});
});
