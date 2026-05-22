import { describe, expect, test } from 'vitest';

import { buildRunPageModel } from './run-page';

describe('buildRunPageModel', () => {
	test('prioritizes completed-run summary, primary visualization, and primary metric', () => {
		const model = buildRunPageModel({
			runStatus: 'completed',
			currentView: {
				label: 'Hierarchy',
				kind: 'hierarchy',
				surface: 'table',
				purpose: 'Organize grouped entities into a readable hierarchy.'
			},
			narrativeLead: {
				eyebrow: 'What is happening now',
				title: 'Pricing service is the current blocker hotspot',
				summary: 'Risk reached 0.37 while backlog climbed to 5.3 review items.',
				significance: 'The strongest recent shift is Pricing service pressure on the critical path.',
				nextStep: 'Use Hierarchy to inspect Pricing service and connected relationships.'
			},
			focusedMetric: {
				metric: 'delivery_risk_index',
				label: 'Delivery risk index',
				headline: true,
				unit: 'idx',
				current: { t: 1, value: 31.53 }
			},
			explanationCards: [],
			recentChanges: [],
			inspectorKind: 'empty',
			hasSelection: false,
			pluginSupportsExplanation: true
		});

		expect(model.primarySections).toEqual(['summary', 'view', 'metric']);
		expect(model.secondaryTabs).toEqual(['artifacts', 'debug']);
		expect(model.summary.title).toBe('Pricing service is the current blocker hotspot');
	});
});
