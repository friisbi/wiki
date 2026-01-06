<template>
	<div class="flex flex-col gap-4 p-4">
		<div class="flex items-center justify-between">
			<h2 class="text-xl font-semibold text-ink-gray-9">{{ __('Contributions') }}</h2>
		</div>

		<Tabs v-model="activeTabIndex" :tabs="tabs">
			<template #tab-panel="{ tab }">
				<div v-if="tab.key === 'my'" class="pt-4">
					<ListView
						class="h-[calc(100vh-280px)]"
						:columns="myContributionsColumns"
						:rows="myBatches.data || []"
						:options="myContributionsOptions"
						row-key="name"
					>
						<template #cell="{ column, row }">
							<div v-if="column.key === 'status'">
								<Badge :variant="'subtle'" :theme="getStatusTheme(row.status)" size="sm">
									{{ row.status }}
								</Badge>
							</div>
							<div v-else-if="column.key === 'contribution_count'" class="text-ink-gray-6">
								{{ row.contribution_count }} {{ row.contribution_count === 1 ? __('change') : __('changes') }}
							</div>
							<div v-else-if="column.key === 'modified'" class="text-ink-gray-5 text-sm">
								{{ formatDate(row.modified) }}
							</div>
							<div v-else>
								{{ row[column.key] }}
							</div>
						</template>
					</ListView>
				</div>

				<div v-else-if="tab.key === 'reviews'" class="pt-4">
					<ListView
						class="h-[calc(100vh-280px)]"
						:columns="reviewsColumns"
						:rows="pendingReviews.data || []"
						:options="reviewsOptions"
						row-key="name"
					>
						<template #cell="{ column, row }">
							<div v-if="column.key === 'status'">
								<Badge :variant="'subtle'" :theme="getStatusTheme(row.status)" size="sm">
									{{ row.status }}
								</Badge>
							</div>
							<div v-else-if="column.key === 'contributor_name'" class="flex items-center gap-2">
								<Avatar :image="row.contributor_image" :label="row.contributor_name" size="sm" />
								<span>{{ row.contributor_name }}</span>
							</div>
							<div v-else-if="column.key === 'contribution_count'" class="text-ink-gray-6">
								{{ row.contribution_count }} {{ row.contribution_count === 1 ? __('change') : __('changes') }}
							</div>
							<div v-else-if="column.key === 'submitted_at'" class="text-ink-gray-5 text-sm">
								{{ formatDate(row.submitted_at) }}
							</div>
							<div v-else>
								{{ row[column.key] }}
							</div>
						</template>
					</ListView>
				</div>
			</template>
		</Tabs>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { ListView, Badge, Avatar, Tabs, createResource } from 'frappe-ui';
import { isWikiManager } from '@/composables/useContributionMode';

const isManager = computed(() => isWikiManager());
const activeTabIndex = ref(0);

const tabs = computed(() => {
	const items = [
		{ key: 'my', label: __('My Contributions') },
	];
	if (isManager.value) {
		items.push({ key: 'reviews', label: __('Pending Reviews') });
	}
	return items;
});

const myBatches = createResource({
	url: 'wiki.api.contributions.get_my_contribution_batches',
	auto: true,
});

const pendingReviews = createResource({
	url: 'wiki.api.contributions.get_pending_reviews',
	auto: computed(() => isManager.value),
});

const myContributionsColumns = [
	{ label: __('Title'), key: 'title', width: 2 },
	{ label: __('Space'), key: 'wiki_space_name', width: 1.5 },
	{ label: __('Changes'), key: 'contribution_count', width: 1 },
	{ label: __('Status'), key: 'status', width: 1 },
	{ label: __('Last Modified'), key: 'modified', width: 1.5 },
];

const reviewsColumns = [
	{ label: __('Title'), key: 'title', width: 2 },
	{ label: __('Contributor'), key: 'contributor_name', width: 1.5 },
	{ label: __('Space'), key: 'wiki_space_name', width: 1.5 },
	{ label: __('Changes'), key: 'contribution_count', width: 1 },
	{ label: __('Status'), key: 'status', width: 1 },
	{ label: __('Submitted'), key: 'submitted_at', width: 1.5 },
];

function getStatusTheme(status) {
	switch (status) {
		case 'Draft': return 'blue';
		case 'Submitted': return 'orange';
		case 'Under Review': return 'orange';
		case 'Approved': return 'green';
		case 'Rejected': return 'red';
		case 'Merged': return 'green';
		default: return 'gray';
	}
}

function getRowRoute(row) {
	if (row.status === 'Draft') {
		return { name: 'SpaceDetails', params: { spaceId: row.wiki_space } };
	}
	return { name: 'ContributionReview', params: { batchId: row.name } };
}

function formatDate(dateStr) {
	if (!dateStr) return '';
	const date = new Date(dateStr);
	return date.toLocaleDateString(undefined, {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	});
}

const myContributionsOptions = {
	selectable: false,
	showTooltip: true,
	resizeColumn: false,
	getRowRoute: getRowRoute,
	emptyState: {
		title: __('No Contributions'),
		description: __('You have not made any contributions yet. Edit a wiki page to get started.'),
	},
};

const reviewsOptions = {
	selectable: false,
	showTooltip: true,
	resizeColumn: false,
	getRowRoute: (row) => ({ name: 'ContributionReview', params: { batchId: row.name } }),
	emptyState: {
		title: __('No Pending Reviews'),
		description: __('There are no contributions waiting for review.'),
	},
};
</script>
