<script setup>
/**
 * CalloutBlockView Component
 *
 * Renders a callout/aside block in the TipTap editor.
 * Supports types: note, tip, caution, danger
 */

import { computed, ref, nextTick, watch } from 'vue';
import { NodeViewWrapper } from '@tiptap/vue-3';

const props = defineProps({
    node: {
        type: Object,
        required: true,
    },
    updateAttributes: {
        type: Function,
        required: true,
    },
    selected: {
        type: Boolean,
        default: false,
    },
});

// Normalize warning to caution
const normalizedType = computed(() => {
    const type = props.node.attrs.type || 'note';
    return type === 'warning' ? 'caution' : type;
});

// Default titles for each type
const defaultTitles = {
    note: 'Note',
    tip: 'Tip',
    caution: 'Caution',
    danger: 'Danger',
};

// Display title (custom or default)
const displayTitle = computed(() => {
    return props.node.attrs.title || defaultTitles[normalizedType.value] || 'Note';
});

// SVG icons for each callout type
const icons = {
    note: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`,
    tip: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>`,
    caution: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>`,
    danger: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>`,
};

const icon = computed(() => icons[normalizedType.value] || icons.note);

// Editing state
const isEditingContent = ref(false);
const editableContent = ref(props.node.attrs.content || '');
const textareaRef = ref(null);

// Watch for external changes
watch(
    () => props.node.attrs.content,
    (newContent) => {
        if (!isEditingContent.value) {
            editableContent.value = newContent || '';
        }
    }
);

function startEditing() {
    editableContent.value = props.node.attrs.content || '';
    isEditingContent.value = true;
    nextTick(() => {
        if (textareaRef.value) {
            textareaRef.value.focus();
        }
    });
}

function finishEditing() {
    isEditingContent.value = false;
    if (editableContent.value !== props.node.attrs.content) {
        props.updateAttributes({ content: editableContent.value });
    }
}
</script>

<template>
    <NodeViewWrapper
        class="callout-block-wrapper"
        :class="[`callout-${normalizedType}`, { 'is-selected': selected }]"
        contenteditable="false"
    >
        <div class="callout-title">
            <span class="callout-icon" v-html="icon"></span>
            <span class="callout-title-text">{{ displayTitle }}</span>
        </div>
        <div class="callout-content" @dblclick="startEditing">
            <textarea
                v-if="isEditingContent"
                ref="textareaRef"
                v-model="editableContent"
                class="callout-content-editor"
                @blur="finishEditing"
                @keydown.escape="finishEditing"
            ></textarea>
            <div v-else class="callout-content-text">
                {{ node.attrs.content || 'Double-click to edit...' }}
            </div>
        </div>
    </NodeViewWrapper>
</template>

<style scoped>
.callout-block-wrapper {
    margin: 1rem 0;
    padding: 1rem 1.25rem;
    border-radius: 0.5rem;
    border-left: 4px solid;
    position: relative;
    transition: all 0.2s ease;
}

/* Remove the selected outline - it's distracting when editing */
.callout-block-wrapper.is-selected {
    outline: none;
}

.callout-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
    font-size: 0.9375rem;
    margin-bottom: 0.5rem;
    line-height: 1.4;
}

.callout-icon {
    flex-shrink: 0;
    display: flex;
    align-items: center;
}

.callout-icon :deep(svg) {
    width: 1.25rem;
    height: 1.25rem;
}

.callout-title-text {
    text-transform: uppercase;
    letter-spacing: 0.025em;
    font-size: 0.8125rem;
}

.callout-content {
    font-size: 0.9375rem;
    line-height: 1.625;
}

.callout-content-text {
    white-space: pre-wrap;
}

.callout-content-editor {
    width: 100%;
    min-height: 60px;
    resize: vertical;
    padding: 0.5rem;
    font-family: inherit;
    font-size: inherit;
    line-height: inherit;
    border: 1px solid var(--outline-gray-2, #e5e7eb);
    border-radius: 0.375rem;
    background-color: var(--surface-white, #ffffff);
    color: inherit;
    caret-color: var(--ink-gray-9, #111827);
}

.callout-content-editor:focus {
    outline: none;
    border-color: var(--outline-gray-4, #9ca3af);
    box-shadow: 0 0 0 2px rgba(156, 163, 175, 0.25);
}

/* Note - Blue */
.callout-note {
    background-color: var(--surface-blue-1, #eff6ff);
    border-color: var(--ink-blue-2, #3b82f6);
}

.callout-note .callout-title {
    color: var(--ink-blue-3, #2563eb);
}

/* Tip - Green */
.callout-tip {
    background-color: var(--surface-green-1, #f0fdf4);
    border-color: var(--ink-green-2, #22c55e);
}

.callout-tip .callout-title {
    color: var(--ink-green-3, #16a34a);
}

/* Caution - Amber */
.callout-caution {
    background-color: var(--surface-amber-1, #fffbeb);
    border-color: var(--ink-amber-2, #f59e0b);
}

.callout-caution .callout-title {
    color: var(--ink-amber-3, #d97706);
}

/* Danger - Red */
.callout-danger {
    background-color: var(--surface-red-1, #fef2f2);
    border-color: var(--ink-red-3, #dc2626);
}

.callout-danger .callout-title {
    color: var(--ink-red-4, #b91c1c);
}
</style>
