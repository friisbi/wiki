<template>
    <div class="flex h-[calc(100vh-4rem)]">
        <!-- Left Sidebar -->
        <aside
            class="border-r border-outline-gray-2 flex flex-col bg-surface-gray-1 relative flex-shrink-0"
            :style="{ width: `${sidebarWidth}px` }"
        >
            <!-- Header -->
            <div class="p-4 border-b border-outline-gray-2">
                <div class="flex items-center justify-between mb-3">
                    <Button
                        variant="ghost"
                        icon-left="arrow-left"
                        :route="{ name: 'SpaceList' }"
                    >
                        {{ __('Back to Spaces') }}
                    </Button>
                    <Button
                        variant="ghost"
                        icon="settings"
                        :title="__('Settings')"
                        @click="showSettingsDialog = true"
                    />
                </div>
                <h1 class="text-lg font-semibold text-ink-gray-9">
                    {{ space.doc?.space_name || spaceId }}
                </h1>
                <p class="text-sm text-ink-gray-5 mt-0.5">{{ space.doc?.route }}</p>
            </div>

            <!-- Document Tree -->
            <div v-if="space.doc && wikiTree.data" class="flex-1 overflow-auto p-2">
                <WikiDocumentList
                    :tree-data="wikiTree.data"
                    :space-id="spaceId"
                    :root-node="space.doc.root_group"
                    :selected-page-id="currentPageId"
                    @refresh="wikiTree.reload()"
                />
            </div>

            <!-- Resize Handle -->
            <div
                class="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-ink-blue-3 transition-colors z-10"
                :class="{ 'bg-ink-blue-3': isResizing }"
                @mousedown="startResize"
            />
        </aside>

        <!-- Right Content Panel -->
        <main class="flex-1 overflow-auto bg-surface-white min-w-0">
            <router-view
                :space-id="spaceId"
                @refresh="wikiTree.reload()"
            />
        </main>

        <!-- Settings Dialog -->
        <Dialog v-model="showSettingsDialog">
            <template #body-title>
                <h3 class="text-xl font-semibold text-ink-gray-9">
                    {{ __('Space Settings') }}
                </h3>
            </template>
            <template #body-content>
                <div class="flex flex-col items-center justify-center py-8">
                    <LucideSettings class="size-12 text-ink-gray-4 mb-4" />
                    <p class="text-sm text-ink-gray-5">{{ __('Space settings coming soon') }}</p>
                </div>
            </template>
            <template #actions="{ close }">
                <div class="flex justify-end">
                    <Button variant="outline" @click="close">{{ __('Close') }}</Button>
                </div>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { useStorage } from '@vueuse/core';
import { createDocumentResource, createResource, Button, Dialog } from 'frappe-ui';
import WikiDocumentList from '../components/WikiDocumentList.vue';
import LucideSettings from '~icons/lucide/settings';

const props = defineProps({
    spaceId: {
        type: String,
        required: true,
    },
});

const route = useRoute();

// Settings dialog state
const showSettingsDialog = ref(false);

// Sidebar resize state
const MIN_WIDTH = 200;
const MAX_WIDTH = 600;
const DEFAULT_WIDTH = 280;

const sidebarWidth = useStorage('wiki-sidebar-width', DEFAULT_WIDTH);
const isResizing = ref(false);

function startResize() {
    isResizing.value = true;
    document.addEventListener('mousemove', handleResize);
    document.addEventListener('mouseup', stopResize);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
}

function handleResize(e) {
    if (!isResizing.value) return;
    const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, e.clientX));
    sidebarWidth.value = newWidth;
}

function stopResize() {
    isResizing.value = false;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
}

onUnmounted(() => {
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
});

// Compute current page from route params
const currentPageId = computed(() => route.params.pageId || null);

const space = createDocumentResource({
    doctype: 'Wiki Space',
    name: props.spaceId,
    auto: true
});

const wikiTree = createResource({
    url: '/api/method/wiki.api.get_wiki_tree',
    params: { space_id: props.spaceId },
    auto: true,
});
</script>
