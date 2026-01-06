import { userResource } from '@/data/user';
import { createResource } from 'frappe-ui';
import { computed, ref } from 'vue';

const currentBatch = ref(null);
const isLoadingBatch = ref(false);

export function isWikiManager() {
	const user = userResource.data;
	if (!user || !user.roles) return false;

	return user.roles.some(
		(role) => role.role === 'Wiki Manager' || role.role === 'System Manager',
	);
}

export function canAccessWiki() {
	const user = userResource.data;
	if (!user || !user.roles) return false;

	return user.roles.some(
		(role) =>
			role.role === 'Wiki User' ||
			role.role === 'Wiki Manager' ||
			role.role === 'System Manager',
	);
}

export function shouldUseContributionMode() {
	const user = userResource.data;
	if (!user || !user.is_logged_in) return false;

	return !isWikiManager();
}

export function useContributionMode(spaceId) {
	const isContributionMode = computed(() => shouldUseContributionMode());
	const hasActiveBatch = computed(() => !!currentBatch.value);

	const batchResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch.get_or_create_draft_batch',
		onSuccess(data) {
			currentBatch.value = data;
			isLoadingBatch.value = false;
		},
		onError(error) {
			console.error('Failed to get/create batch:', error);
			isLoadingBatch.value = false;
		},
	});

	const contributionsResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_contribution.wiki_contribution.get_batch_contributions',
	});

	const submitBatchResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch.submit_batch',
		onSuccess(data) {
			currentBatch.value = data;
		},
	});

	const withdrawBatchResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch.withdraw_batch',
		onSuccess(data) {
			currentBatch.value = data;
		},
	});

	async function initBatch() {
		if (!isContributionMode.value || !spaceId.value) return null;

		isLoadingBatch.value = true;
		await batchResource.submit({ wiki_space: spaceId.value });
		return currentBatch.value;
	}

	async function loadContributions() {
		if (!currentBatch.value) return [];

		await contributionsResource.submit({ batch: currentBatch.value.name });
		return contributionsResource.data || [];
	}

	async function submitForReview() {
		if (!currentBatch.value) return null;

		await submitBatchResource.submit({ batch_name: currentBatch.value.name });
		return currentBatch.value;
	}

	async function withdrawBatch() {
		if (!currentBatch.value) return null;

		await withdrawBatchResource.submit({ batch_name: currentBatch.value.name });
		return currentBatch.value;
	}

	const contributionCount = computed(() => {
		return contributionsResource.data?.length || 0;
	});

	const canSubmit = computed(() => {
		return (
			currentBatch.value?.status === 'Draft' && contributionCount.value > 0
		);
	});

	const canWithdraw = computed(() => {
		return ['Submitted', 'Under Review'].includes(currentBatch.value?.status);
	});

	return {
		isContributionMode,
		currentBatch,
		hasActiveBatch,
		isLoadingBatch,
		contributionCount,
		canSubmit,
		canWithdraw,
		batchResource,
		contributionsResource,
		submitBatchResource,
		withdrawBatchResource,
		initBatch,
		loadContributions,
		submitForReview,
		withdrawBatch,
	};
}

export function useContribution() {
	const createContributionResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_contribution.wiki_contribution.create_contribution',
	});

	const updateContributionResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_contribution.wiki_contribution.update_contribution',
	});

	const deleteContributionResource = createResource({
		url: 'wiki.frappe_wiki.doctype.wiki_contribution.wiki_contribution.delete_contribution',
	});

	async function createEditContribution(
		batchName,
		targetDocument,
		proposedTitle,
		proposedContent,
	) {
		return await createContributionResource.submit({
			batch: batchName,
			operation: 'edit',
			target_document: targetDocument,
			proposed_title: proposedTitle,
			proposed_content: proposedContent,
		});
	}

	async function createPageContribution(
		batchName,
		parentRef,
		title,
		content,
		isGroup = false,
	) {
		return await createContributionResource.submit({
			batch: batchName,
			operation: 'create',
			parent_ref: parentRef,
			proposed_title: title,
			proposed_content: content,
			proposed_is_group: isGroup,
			proposed_is_published: true,
		});
	}

	async function updateContribution(
		contributionName,
		proposedTitle,
		proposedContent,
	) {
		return await updateContributionResource.submit({
			name: contributionName,
			proposed_title: proposedTitle,
			proposed_content: proposedContent,
		});
	}

	function findContributionForDocument(contributions, documentName) {
		return contributions?.find(
			(c) => c.target_document === documentName || c.temp_id === documentName,
		);
	}

	return {
		createContributionResource,
		updateContributionResource,
		deleteContributionResource,
		createEditContribution,
		createPageContribution,
		updateContribution,
		findContributionForDocument,
	};
}

export { currentBatch };
