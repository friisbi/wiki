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
        <Dialog v-model="showSettingsDialog">
            <template #body-title>
                <h3 class="text-xl font-semibold text-ink-gray-9">
                    {{ __('Page Settings') }}
                </h3>
            </template>
            <template #body-content>
                <div class="space-y-4">
                    <FormControl
                        type="text"
                        :label="__('Route')"
                        v-model="settingsForm.route"
                        :placeholder="__('e.g., docs/getting-started')"
                    />
                </div>
            </template>
            <template #actions="{ close }">
                <div class="flex justify-end gap-2">
                    <Button variant="outline" @click="close">
                        {{ __('Cancel') }}
                    </Button>
                    <Button
                        variant="solid"
                        :loading="settingsResource.loading"
                        @click="saveSettings"
                    >
                        {{ __('Save') }}
                    </Button>
                </div>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import { MilkdownProvider } from "@milkdown/vue";
import { createDocumentResource, createResource, Badge, Button, Dialog, Dropdown, FormControl, toast } from "frappe-ui";
import WikiEditor from './WikiEditor.vue';
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
const settingsForm = reactive({
    route: '',
});

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

// Publish/Unpublish Resource
const publishResource = createResource({
    url: 'frappe.client.set_value',
    makeParams() {
        return {
            doctype: 'Wiki Document',
            name: props.pageId,
            fieldname: {
                is_published: wikiDoc.doc?.is_published ? 0 : 1,
            },
        };
    },
    onSuccess() {
        const action = wikiDoc.doc?.is_published ? __('unpublished') : __('published');
        toast.success(__('Page {0}', [action]));
        wikiDoc.reload();
        emit('refresh'); // Refresh sidebar tree
    },
    onError(error) {
        toast.error(error.messages?.[0] || __('Error updating publish status'));
    },
});

async function togglePublish() {
    await publishResource.submit();
}

// Settings Resource
const settingsResource = createResource({
    url: 'frappe.client.set_value',
    onSuccess() {
        toast.success(__('Settings saved'));
        showSettingsDialog.value = false;
        wikiDoc.reload();
        emit('refresh');
    },
    onError(error) {
        toast.error(error.messages?.[0] || __('Error saving settings'));
    },
});

function openSettingsDialog() {
    settingsForm.route = wikiDoc.doc?.route || '';
    showSettingsDialog.value = true;
}

function saveSettings() {
    settingsResource.submit({
        doctype: 'Wiki Document',
        name: props.pageId,
        fieldname: {
            route: settingsForm.route,
        },
    });
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
