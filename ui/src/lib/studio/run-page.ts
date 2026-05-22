export type RunPageModel = {
	summary: {
		title: string;
		summary: string;
		significance: string;
		nextStep: string;
		status: string;
		viewLabel: string;
		currentFrame: string | null;
	};
	primarySections: Array<'summary' | 'view' | 'metric'>;
	secondaryTabs: Array<'explain' | 'inspect' | 'timeline' | 'artifacts' | 'debug'>;
	showExplainTab: boolean;
	showInspectorPreview: boolean;
	showRecentChanges: boolean;
	showDebugTab: boolean;
};

export function buildRunPageModel(input: {
	runStatus: string;
	currentView: { label: string; kind: string; surface: string; purpose: string };
	narrativeLead: {
		eyebrow?: string;
		title: string;
		summary: string;
		significance: string;
		nextStep: string;
	};
	focusedMetric: { metric: string; label: string; headline?: boolean; unit?: string | null; current: { t: number; value: number } } | null;
	explanationCards: Array<{ sourceLabel: string; primaryStatement: string; supportingDetail: string }>;
	recentChanges: Array<{ label: string; summary: string }>;
	inspectorKind: 'empty' | 'field-cell' | 'graph-node' | 'graph-edge';
	hasSelection: boolean;
	pluginSupportsExplanation: boolean;
	currentFrameId?: string | null;
}): RunPageModel {
	const meaningfulExplain =
		input.pluginSupportsExplanation &&
		input.explanationCards.some(
			(card) =>
				card.sourceLabel !== 'Unavailable' && card.primaryStatement !== 'No interpretation yet'
		);
	const meaningfulRecentChanges = input.recentChanges.some(
		(item) => !item.label.toLowerCase().startsWith('scheduler ')
	);

	const secondaryTabs: RunPageModel['secondaryTabs'] = [];
	if (meaningfulExplain) secondaryTabs.push('explain');
	secondaryTabs.push('inspect');
	if (meaningfulRecentChanges || input.currentView.surface === 'metrics') secondaryTabs.push('timeline');
	secondaryTabs.push('artifacts', 'debug');

	return {
		summary: {
			title: input.narrativeLead.title,
			summary: input.narrativeLead.summary,
			significance: input.narrativeLead.significance,
			nextStep: input.narrativeLead.nextStep,
			status: input.runStatus,
			viewLabel: input.currentView.label,
			currentFrame: input.currentFrameId ?? null
		},
		primarySections: ['summary', 'view', 'metric'],
		secondaryTabs,
		showExplainTab: meaningfulExplain,
		showInspectorPreview: true,
		showRecentChanges: meaningfulRecentChanges,
		showDebugTab: true
	};
}
