import { describe, expect, test } from 'vitest';

import {
	buildExplanationPanelCards,
	buildNarrativeLead,
	extractMilestones,
	milestonePlaybackTarget,
	recentChangeCards
} from './narrative';
import type {
	EventRecord,
	ExplanationResponse,
	MetricRecord,
	SimulationFrame
} from '$lib/api-client';

const metrics: MetricRecord[] = [
	{ t: 1, metric: 'infected_count', value: 10, warning_threshold: 15, critical_threshold: 24 },
	{ t: 2, metric: 'infected_count', value: 18, warning_threshold: 15, critical_threshold: 24 },
	{ t: 3, metric: 'infected_count', value: 28, warning_threshold: 15, critical_threshold: 24 },
	{ t: 4, metric: 'infected_count', value: 11, warning_threshold: 15, critical_threshold: 24 },
	{ t: 1, metric: 'recovered_count', value: 2 },
	{ t: 2, metric: 'recovered_count', value: 4 },
	{ t: 3, metric: 'recovered_count', value: 9 },
	{ t: 4, metric: 'recovered_count', value: 16 }
];

const events: EventRecord[] = [
	{ t: 2.1, event_type: 'infection' },
	{ t: 2.2, event_type: 'infection' },
	{ t: 2.3, event_type: 'infection' },
	{ t: 3.2, event_type: 'recovery' }
];

const frames: SimulationFrame[] = [
	{
		kind: 'graph',
		frame_id: 'frame-1',
		t: 1,
		tick: 1,
		solver_id: 'sir#0',
		source: 'replay',
		nodes: [{ id: 'a', state: 'susceptible' }],
		edges: [],
		visualization: {}
	},
	{
		kind: 'graph',
		frame_id: 'frame-3',
		t: 3,
		tick: 3,
		solver_id: 'sir#0',
		source: 'replay',
		nodes: [{ id: 'a', state: 'infected' }],
		edges: [],
		visualization: {}
	},
	{
		kind: 'graph',
		frame_id: 'frame-4',
		t: 4,
		tick: 4,
		solver_id: 'sir#0',
		source: 'replay',
		nodes: [{ id: 'a', state: 'recovered' }],
		edges: [],
		visualization: {}
	}
];

const explanation: ExplanationResponse = {
	run_id: 'run-a',
	scope: 'run',
	available: true,
	interpretation: {
		run_id: 'run-a',
		scope: 'run',
		t: 3,
		tick: 3,
		mode_requested: 'rules_only',
		mode_applied: 'rules_only',
		label: 'Run summary',
		cached: true,
		facts: [
			{
				kind: 'milestone',
				title: 'Containment window opened',
				summary: 'Recovery momentum overtook new infections.',
				severity: 'notice',
				related_ids: ['recovered_count'],
				t: 4
			}
		],
		summary: {
			title: 'Recovery trend strengthening',
			summary: 'Deterministic facts show recoveries accelerating after the infection peak.',
			severity: 'notice',
			fact_count: 1
		}
	}
};

describe('narrative helpers', () => {
	test('extracts milestones for peaks, threshold crossings, anomalies, bursts, and fact markers', () => {
		const milestones = extractMilestones({ metrics, events, frames, explanation });

		expect(milestones.map((milestone) => milestone.kind)).toEqual([
			'event_burst',
			'threshold_crossing',
			'peak',
			'anomaly_end',
			'fact'
		]);
		expect(milestones[0]).toMatchObject({
			kind: 'event_burst',
			t: 2.2
		});
		expect(milestones[2]).toMatchObject({
			kind: 'peak',
			metric: 'infected_count',
			t: 3
		});
	});

	test('summarizes what changed recently around the selected playback time', () => {
		expect(recentChangeCards({ metrics, events, selectedTime: 3.1, explanation })).toEqual([
			{
				label: 'Infected count',
				summary: 'Climbed by 10 to 28 at the selected time.',
				detail: 'The latest sample is above the critical threshold.',
				severity: 'critical'
			},
			{
				label: 'Event burst',
				summary: '3 events landed in the same short activity window.',
				detail: 'The burst centered on t=2.2.',
				severity: 'notice'
			},
			{
				label: 'Interpretation',
				summary: 'Deterministic facts show recoveries accelerating after the infection peak.',
				detail: 'Deterministic summary for the active frame or run.',
				severity: 'notice'
			}
		]);
	});

	test('builds explanation cards with primary statement, source label, evidence, and footer', () => {
		expect(
			buildExplanationPanelCards([
				{
					key: 'run',
					label: "What's happening",
					description: 'Run-level summary from deterministic facts and optional interpretation.',
					response: explanation,
					loading: false
				}
			])
		).toEqual([
			{
				key: 'run',
				label: "What's happening",
				description: 'Run-level summary from deterministic facts and optional interpretation.',
				loading: false,
				sourceLabel: 'Deterministic facts',
				primaryStatement: 'Recovery trend strengthening',
				supportingDetail:
					'Deterministic facts show recoveries accelerating after the infection peak.',
				evidence: [],
				facts: [
					{
						title: 'Containment window opened',
						summary: 'Recovery momentum overtook new infections.',
						severity: 'notice',
						time: 4,
						timeLabel: 't=4'
					}
				],
				footer: '1 supporting fact · Cached response'
			}
		]);
	});

	test('links milestones to the nearest replay frame before scrubbing', () => {
		const milestones = extractMilestones({ metrics, events, frames, explanation });
		const target = milestonePlaybackTarget(milestones[0], frames);

		expect(target).toEqual({ time: 3, frameId: 'frame-3' });
	});

	test('builds a narrative-first run lead with plain language, significance, and next step', () => {
		expect(
			buildNarrativeLead({
				explanation,
				recentChanges: recentChangeCards({ metrics, events, selectedTime: 3.1, explanation }),
				viewLabel: 'Matrix',
				viewPurpose: 'Compare the densest relationships without relying on node positions.'
			})
		).toEqual({
			eyebrow: 'What is happening now',
			title: 'Recovery trend strengthening',
			summary: 'Deterministic facts show recoveries accelerating after the infection peak.',
			significance:
				'The strongest recent shift is Infected count: Climbed by 10 to 28 at the selected time.',
			nextStep: 'Use Matrix to compare the densest relationships without relying on node positions.'
		});
	});
});
