/**
 * TipTap Video Block Extension
 *
 * Custom node extension for video blocks.
 * Renders video URLs (like GitHub does) as HTML5 video players.
 *
 * Markdown syntax: ![title](video-url.mp4)
 */

import { Node, mergeAttributes } from '@tiptap/core';
import { VueNodeViewRenderer } from '@tiptap/vue-3';
import VideoBlockView from './VideoBlockView.vue';

/**
 * Video extensions that should be rendered as video players
 */
export const VIDEO_EXTENSIONS = [
	'.mp4',
	'.webm',
	'.ogg',
	'.mov',
	'.avi',
	'.mkv',
	'.m4v',
];

/**
 * Check if a URL is a video URL based on file extension
 */
export function isVideoUrl(url) {
	if (!url) return false;
	const lowerUrl = url.toLowerCase();
	return VIDEO_EXTENSIONS.some((ext) => lowerUrl.endsWith(ext));
}

export const VideoBlock = Node.create({
	name: 'videoBlock',

	group: 'block',

	atom: true,

	draggable: true,

	addAttributes() {
		return {
			src: {
				default: '',
			},
			alt: {
				default: '',
			},
		};
	},

	parseHTML() {
		return [
			{
				tag: 'div[data-type="video-block"]',
				getAttrs: (dom) => ({
					src: dom.getAttribute('data-src') || '',
					alt: dom.getAttribute('data-alt') || '',
				}),
			},
			{
				tag: 'video',
				getAttrs: (dom) => ({
					src:
						dom.getAttribute('src') ||
						dom.querySelector('source')?.getAttribute('src') ||
						'',
					alt: dom.getAttribute('title') || '',
				}),
			},
		];
	},

	renderHTML({ node, HTMLAttributes }) {
		const attrs = mergeAttributes(HTMLAttributes, {
			'data-type': 'video-block',
			'data-src': node.attrs.src,
			'data-alt': node.attrs.alt,
		});

		return [
			'div',
			attrs,
			[
				'video',
				{
					src: node.attrs.src,
					controls: true,
					preload: 'metadata',
					style: 'max-width: 100%; border-radius: 8px;',
				},
				['source', { src: node.attrs.src }],
			],
		];
	},

	addNodeView() {
		return VueNodeViewRenderer(VideoBlockView);
	},

	addCommands() {
		return {
			setVideo:
				(attributes) =>
				({ commands }) => {
					return commands.insertContent({
						type: this.name,
						attrs: attributes,
					});
				},
		};
	},

	// TipTap v3 Markdown extension support
	// Custom tokenizer to intercept image syntax with video URLs
	markdownTokenizer: {
		name: 'videoBlock',
		level: 'block',

		start(src) {
			// Look for image-like syntax that could be a video
			return src.indexOf('![');
		},

		tokenize(src) {
			// Match markdown image syntax: ![alt](url)
			const match = /^!\[([^\]]*)\]\(([^)]+)\)/.exec(src);

			if (!match) {
				return undefined;
			}

			const alt = match[1];
			const url = match[2];

			// Only tokenize if it's a video URL
			if (!isVideoUrl(url)) {
				return undefined;
			}

			return {
				type: 'videoBlock',
				raw: match[0],
				alt: alt,
				src: url,
			};
		},
	},

	parseMarkdown(token) {
		return {
			type: 'videoBlock',
			attrs: {
				src: token.src || token.href || '',
				alt: token.alt || token.text || '',
			},
		};
	},

	renderMarkdown(node) {
		const alt = node.attrs.alt || '';
		const src = node.attrs.src || '';
		return `![${alt}](${src})\n\n`;
	},
});

export default VideoBlock;
