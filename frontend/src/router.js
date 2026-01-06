import { userResource } from '@/data/user';
import { createRouter, createWebHistory } from 'vue-router';
import { session } from './data/session';

const routes = [
	{
		path: '/',
		name: 'Home',
		redirect: '/spaces',
	},
	{
		path: '/spaces',
		name: 'SpaceList',
		component: () => import('@/pages/Spaces.vue'),
	},
	{
		path: '/contributions',
		name: 'Contributions',
		component: () => import('@/pages/Contributions.vue'),
	},
	{
		path: '/contributions/:batchId',
		name: 'ContributionReview',
		component: () => import('@/pages/ContributionReview.vue'),
		props: true,
	},
	{
		path: '/spaces/:spaceId',
		component: () => import('@/pages/SpaceDetails.vue'),
		props: true,
		children: [
			{
				path: '',
				name: 'SpaceDetails',
				component: () => import('@/components/SpaceWelcome.vue'),
			},
			{
				path: 'page/:pageId',
				name: 'SpacePage',
				component: () => import('@/components/WikiDocumentPanel.vue'),
				props: true,
			},
			{
				path: 'draft/:contributionId',
				name: 'DraftContribution',
				component: () => import('@/components/DraftContributionPanel.vue'),
				props: true,
			},
		],
	},
];

const router = createRouter({
	history: createWebHistory('/wiki'),
	routes,
});

router.beforeEach(async (to, from, next) => {
	let isLoggedIn = session.isLoggedIn;
	try {
		await userResource.fetch();
	} catch (error) {
		isLoggedIn = false;
	}

	if (!isLoggedIn) {
		window.location.href = `/login?redirect-to=${encodeURIComponent(
			to.fullPath,
		)}`;
	} else {
		next();
	}
});

export default router;
