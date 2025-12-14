<template>
    <div class="h-full flex flex-col">
        <div v-if="wikiDoc.doc" class="h-full flex flex-col">
            <!-- Page Header (Sticky) -->
            <div class="flex items-center justify-between p-6 pb-4 bg-surface-white shrink-0 border-b-2 border-b-gray-500/20">
                <!-- Title with Badge -->
                <div class="flex items-center gap-2">
                    <h1 class="text-2xl font-semibold text-ink-gray-9">{{ wikiDoc.doc.title }}</h1>
                    <Badge v-if="wikiDoc.doc.is_published" variant="subtle" theme="green" size="sm">
                        {{ __('Published') }}
                    </Badge>
                    <Badge v-else variant="subtle" theme="orange" size="sm">
                        {{ __('Not Published') }}
                    </Badge>
                </div>

                <!-- Actions -->
                <div class="flex items-center gap-2">
                    <Button
                        variant="solid"
                        :loading="wikiDoc.setValue.loading"
                        @click="saveFromHeader"
                    >
                        <template #prefix>
                            <LucideSave class="size-4" />
                        </template>
                        {{ __('Save') }}
                    </Button>
                    <Dropdown :options="menuOptions">
                        <Button variant="outline">
                            <LucideMoreVertical class="size-4" />
                        </Button>
                    </Dropdown>
                </div>
            </div>

            <!-- Editor Content (Scrollable) -->
            <div class="flex-1 overflow-auto px-6 pb-6">
                <MilkdownProvider v-if="editorKey" :key="editorKey">
                    <WikiEditor ref="editorRef" :content="wikiDoc.doc.content" :saving="wikiDoc.setValue.loading" @save="saveContent" />
                </MilkdownProvider>
            </div>
        </div>

        <!-- Settings Dialog -->
        <WikiDocumentSettings
            v-model="showSettingsDialog"
            :pageId="props.pageId"
            :doc="wikiDoc.doc"
            @saved="onSettingsSaved"
        />
    </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { MilkdownProvider } from "@milkdown/vue";
import { createDocumentResource, Badge, Button, Dropdown, toast } from "frappe-ui";
import WikiEditor from './WikiEditor.vue';
import WikiDocumentSettings from './WikiDocumentSettings.vue';
import LucideSave from '~icons/lucide/save';
import LucideMoreVertical from '~icons/lucide/more-vertical';

const props = defineProps({
    pageId: {
        type: String,
        required: true
    },
    spaceId: {
        type: String,
        required: false
    }
});

const emit = defineEmits(['refresh']);
const editorRef = ref(null);
const showSettingsDialog = ref(false);

const wikiDoc = createDocumentResource({
    doctype: "Wiki Document",
    name: props.pageId,
    auto: true,
});

// Watch for pageId changes and reload document
watch(() => props.pageId, (newPageId) => {
    if (newPageId) {
        wikiDoc.name = newPageId;
        wikiDoc.reload();
    }
});

// Key that changes only when the document for the current page is loaded
// This prevents the editor from rendering with stale content
const editorKey = computed(() => {
    if (wikiDoc.doc?.name === props.pageId) {
        return `${props.pageId}-${wikiDoc.doc.modified || 'new'}`;
    }
    return null;
});

// Dropdown menu options
const menuOptions = computed(() => {
    const options = [];

    if (wikiDoc.doc?.is_published) {
        options.push({
            label: __('View Page'),
            icon: 'external-link',
            onClick: () => window.open(`http://wiki.localhost:8000/${wikiDoc.doc.route}`, '_blank'),
        });
    }

    options.push(
        {
            label: wikiDoc.doc?.is_published ? __('Unpublish') : __('Publish'),
            icon: 'upload-cloud',
            onClick: togglePublish,
        },
        {
            label: __('Settings'),
            icon: 'settings',
            onClick: openSettingsDialog,
        },
    );

    return options;
});

async function togglePublish() {
    const newStatus = wikiDoc.doc?.is_published ? 0 : 1;
    const action = newStatus ? __('published') : __('unpublished');

    try {
        await wikiDoc.setValue.submit({
            is_published: newStatus,
        });
        toast.success(__('Page {0}', [action]));
        emit('refresh');
    } catch (error) {
        toast.error(error.messages?.[0] || __('Error updating publish status'));
    }
}

function openSettingsDialog() {
    showSettingsDialog.value = true;
}

function onSettingsSaved() {
    wikiDoc.reload();
    emit('refresh');
}

function saveFromHeader() {
    editorRef.value?.saveToDB();
}

function saveContent(content) {
    wikiDoc.setValue.submit({
        content
    });
}
</script>
