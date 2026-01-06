<template>
	<div
		v-if="isContributionMode"
		class="contribution-banner px-4 py-3 flex items-center justify-between gap-4"
		:class="bannerClass"
	>
		<div class="flex items-center gap-3">
			<component :is="bannerIcon" class="size-5 shrink-0" />
			<div>
				<p class="text-sm font-medium">{{ bannerTitle }}</p>
				<p class="text-xs opacity-80">{{ bannerDescription }}</p>
			</div>
		</div>

		<div class="flex items-center gap-2">
			<button
				v-if="contributionCount > 0"
				class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer"
				:class="clickableBadgeClass"
				@click="showChangesDialog = true"
			>
				<LucideList class="size-3.5" />
				{{ contributionCount }} {{ contributionCount === 1 ? __('change') : __('changes') }}
			</button>

			<template v-if="batchStatus === 'Draft'">
				<Button
					v-if="contributionCount > 0"
					variant="solid"
					size="sm"
					:loading="submitBatchResource?.loading"
					@click="showSubmitConfirmDialog = true"
				>
					{{ __('Submit for Review') }}
				</Button>
			</template>

			<template v-else-if="batchStatus === 'Submitted' || batchStatus === 'Under Review'">
				<Button
					variant="outline"
					size="sm"
					:loading="withdrawBatchResource?.loading"
					@click="$emit('withdraw')"
				>
					{{ __('Withdraw') }}
				</Button>
			</template>

			<template v-else-if="batchStatus === 'Approved'">
				<span class="text-sm font-medium text-green-700">
					{{ __('Approved! Awaiting merge.') }}
				</span>
			</template>

			<template v-else-if="batchStatus === 'Rejected'">
				<Button
					variant="outline"
					size="sm"
					@click="$emit('revise')"
				>
					{{ __('Revise & Resubmit') }}
				</Button>
			</template>
		</div>

		<Dialog v-model="showChangesDialog" :options="{ size: 'lg' }">
			<template #body-title>
				<div class="flex items-center gap-2">
					<LucideGitBranch class="size-5 text-ink-gray-5" />
					<h3 class="text-xl font-semibold text-ink-gray-9">
						{{ __('Pending Changes') }}
					</h3>
				</div>
			</template>
			<template #body-content>
				<div class="space-y-3 max-h-[60vh] overflow-y-auto">
					<div
						v-for="contrib in contributions"
						:key="contrib.name"
						class="flex items-start gap-3 p-3 rounded-lg border border-outline-gray-2 hover:bg-surface-gray-1"
					>
						<div
							class="flex items-center justify-center size-8 rounded-full shrink-0"
							:class="getOperationIconClass(contrib.operation)"
						>
							<component :is="getOperationIcon(contrib.operation)" class="size-4" />
						</div>

						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<span class="font-medium text-ink-gray-9 truncate">
									{{ getContributionTitle(contrib) }}
								</span>
								<Badge variant="subtle" :theme="getOperationTheme(contrib.operation)" size="sm">
									{{ getOperationLabel(contrib.operation) }}
								</Badge>
							</div>
							<p class="text-sm text-ink-gray-5 mt-0.5">
								{{ getContributionDescription(contrib) }}
							</p>
						</div>

						<div class="flex items-center gap-1 text-ink-gray-4 shrink-0">
							<LucideFolder v-if="contrib.proposed_is_group" class="size-4" />
							<LucideFileText v-else class="size-4" />
						</div>
					</div>

					<div v-if="contributions.length === 0" class="text-center py-8 text-ink-gray-5">
						{{ __('No pending changes') }}
					</div>
				</div>
			</template>
			<template #actions="{ close }">
				<div class="flex justify-end">
					<Button variant="outline" @click="close">{{ __('Close') }}</Button>
				</div>
			</template>
		</Dialog>

		<Dialog v-model="showSubmitConfirmDialog" :options="{ size: 'sm' }">
			<template #body-title>
				<div class="flex items-center gap-2">
					<LucideGitBranch class="size-5 text-ink-gray-5" />
					<h3 class="text-xl font-semibold text-ink-gray-9">
						{{ __('Submit for Review') }}
					</h3>
				</div>
			</template>
			<template #body-content>
				<p class="text-ink-gray-7">
					{{ __('Are you sure you want to submit your changes for review? A reviewer will be notified to review your contribution.') }}
				</p>
				<p class="text-sm text-ink-gray-5 mt-2">
					{{ __('You have {0} pending {1}.', [contributionCount, contributionCount === 1 ? __('change') : __('changes')]) }}
				</p>
			</template>
			<template #actions="{ close }">
				<div class="flex justify-end gap-2">
					<Button variant="outline" @click="close">{{ __('Cancel') }}</Button>
					<Button
						variant="solid"
						:loading="submitBatchResource?.loading"
						@click="confirmSubmit(close)"
					>
						{{ __('Submit') }}
					</Button>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { Badge, Button, Dialog } from 'frappe-ui';
import LucideGitBranch from '~icons/lucide/git-branch';
import LucideClock from '~icons/lucide/clock';
import LucideCheckCircle from '~icons/lucide/check-circle';
import LucideXCircle from '~icons/lucide/x-circle';
import LucideAlertCircle from '~icons/lucide/alert-circle';
import LucideList from '~icons/lucide/list';
import LucidePlus from '~icons/lucide/plus';
import LucidePencil from '~icons/lucide/pencil';
import LucideTrash2 from '~icons/lucide/trash-2';
import LucideMove from '~icons/lucide/move';
import LucideArrowUpDown from '~icons/lucide/arrow-up-down';
import LucideFolder from '~icons/lucide/folder';
import LucideFileText from '~icons/lucide/file-text';

const props = defineProps({
	isContributionMode: {
		type: Boolean,
		default: false,
	},
	batchStatus: {
		type: String,
		default: 'Draft',
	},
	contributionCount: {
		type: Number,
		default: 0,
	},
	contributions: {
		type: Array,
		default: () => [],
	},
	submitBatchResource: {
		type: Object,
		default: null,
	},
	withdrawBatchResource: {
		type: Object,
		default: null,
	},
});

const emit = defineEmits(['submit', 'withdraw', 'revise']);

const showChangesDialog = ref(false);
const showSubmitConfirmDialog = ref(false);

function confirmSubmit(closeDialog) {
	closeDialog();
	emit('submit');
}

const clickableBadgeClass = computed(() => {
	switch (props.batchStatus) {
		case 'Draft':
			return 'bg-blue-100 text-blue-700 hover:bg-blue-200';
		case 'Submitted':
		case 'Under Review':
			return 'bg-amber-100 text-amber-700 hover:bg-amber-200';
		case 'Approved':
			return 'bg-green-100 text-green-700 hover:bg-green-200';
		case 'Rejected':
			return 'bg-red-100 text-red-700 hover:bg-red-200';
		default:
			return 'bg-gray-100 text-gray-700 hover:bg-gray-200';
	}
});

function getOperationIcon(operation) {
	switch (operation) {
		case 'create': return LucidePlus;
		case 'edit': return LucidePencil;
		case 'delete': return LucideTrash2;
		case 'move': return LucideMove;
		case 'reorder': return LucideArrowUpDown;
		default: return LucideFileText;
	}
}

function getOperationIconClass(operation) {
	switch (operation) {
		case 'create': return 'bg-green-100 text-green-600';
		case 'edit': return 'bg-blue-100 text-blue-600';
		case 'delete': return 'bg-red-100 text-red-600';
		case 'move': return 'bg-purple-100 text-purple-600';
		case 'reorder': return 'bg-gray-100 text-gray-600';
		default: return 'bg-gray-100 text-gray-600';
	}
}

function getOperationTheme(operation) {
	switch (operation) {
		case 'create': return 'green';
		case 'edit': return 'blue';
		case 'delete': return 'red';
		case 'move': return 'purple';
		case 'reorder': return 'gray';
		default: return 'gray';
	}
}

function getOperationLabel(operation) {
	switch (operation) {
		case 'create': return __('New');
		case 'edit': return __('Edit');
		case 'delete': return __('Delete');
		case 'move': return __('Move');
		case 'reorder': return __('Reorder');
		default: return operation;
	}
}

function getContributionTitle(contrib) {
	if (contrib.operation === 'create') {
		return contrib.proposed_title || __('Untitled');
	}
	if (contrib.operation === 'edit') {
		return contrib.proposed_title || contrib.original_title || __('Untitled');
	}
	return contrib.original_title || contrib.target_route || __('Unknown');
}

function getContributionDescription(contrib) {
	switch (contrib.operation) {
		case 'create':
			return contrib.proposed_is_group
				? __('New group to be created')
				: __('New page to be created');
		case 'edit':
			const changes = [];
			if (contrib.proposed_title && contrib.proposed_title !== contrib.original_title) {
				changes.push(__('title'));
			}
			if (contrib.proposed_content && contrib.proposed_content !== contrib.original_content) {
				changes.push(__('content'));
			}
			return changes.length > 0
				? __('Changed: {0}', [changes.join(', ')])
				: __('Content modified');
		case 'delete':
			return __('Will be deleted');
		case 'move':
			return __('Will be moved to a new location');
		case 'reorder':
			return __('Position changed');
		default:
			return '';
	}
}

const bannerClass = computed(() => {
	switch (props.batchStatus) {
		case 'Draft':
			return 'bg-blue-50 border-b border-blue-200 text-blue-800';
		case 'Submitted':
		case 'Under Review':
			return 'bg-amber-50 border-b border-amber-200 text-amber-800';
		case 'Approved':
			return 'bg-green-50 border-b border-green-200 text-green-800';
		case 'Rejected':
			return 'bg-red-50 border-b border-red-200 text-red-800';
		default:
			return 'bg-gray-50 border-b border-gray-200 text-gray-800';
	}
});

const bannerIcon = computed(() => {
	switch (props.batchStatus) {
		case 'Draft':
			return LucideGitBranch;
		case 'Submitted':
		case 'Under Review':
			return LucideClock;
		case 'Approved':
			return LucideCheckCircle;
		case 'Rejected':
			return LucideXCircle;
		default:
			return LucideAlertCircle;
	}
});

const bannerTitle = computed(() => {
	switch (props.batchStatus) {
		case 'Draft':
			return __('Contribution Mode');
		case 'Submitted':
			return __('Submitted for Review');
		case 'Under Review':
			return __('Under Review');
		case 'Approved':
			return __('Contribution Approved');
		case 'Rejected':
			return __('Changes Requested');
		default:
			return __('Contribution');
	}
});

const bannerDescription = computed(() => {
	switch (props.batchStatus) {
		case 'Draft':
			return __('Your changes will be saved as a draft and submitted for review');
		case 'Submitted':
			return __('Your contribution is waiting for a reviewer');
		case 'Under Review':
			return __('A reviewer is looking at your contribution');
		case 'Approved':
			return __('Your contribution will be merged soon');
		case 'Rejected':
			return __('Please review the feedback and make changes');
		default:
			return '';
	}
});

</script>
