<template>
  <!-- A page of the site («О нас», «Ссылки»): Markdown written by administrators right here -->
  <div class="mx-auto max-w-prose">
    <template v-if="!editing">
      <MarkdownContent v-if="page?.content_md" :text="page.content_md" />
      <EmptyState v-else>{{ emptyText }}</EmptyState>
      <div v-if="isAdmin" class="mt-8 flex justify-end">
        <button type="button" class="btn-secondary px-4 py-1.5 text-sm" @click="startEdit">Редактировать</button>
      </div>
    </template>
    <form v-else class="space-y-4" @submit.prevent="save">
      <textarea v-model="draft" rows="16" class="field resize-y" :placeholder="placeholder" />
      <div class="flex gap-3">
        <button type="button" class="btn-ghost" @click="editing = false">Отмена</button>
        <button type="submit" class="btn-primary ml-auto" :disabled="busy">Сохранить</button>
      </div>
      <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
    </form>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{ slug: 'about' | 'links'; emptyText?: string; placeholder?: string }>(), {
  emptyText: 'Здесь пока пусто',
  placeholder: 'Markdown: ## Заголовок, **жирный**, [ссылка](https://…)',
})

const api = useApi()
const { isAdmin } = useAuth()
const { data: page } = await useAsyncData(`site-page-${props.slug}`, () =>
  api<{ slug: string; content_md: string }>(`/api/site/pages/${props.slug}`),
)
const editing = ref(false)
const draft = ref('')
const busy = ref(false)
const error = ref('')

function startEdit() {
  draft.value = page.value?.content_md || ''
  editing.value = true
}

async function save() {
  busy.value = true
  error.value = ''
  try {
    page.value = await api(`/api/site/pages/${props.slug}`, { method: 'PUT', body: { content_md: draft.value } })
    editing.value = false
  } catch (e) {
    error.value = apiError(e)
  } finally {
    busy.value = false
  }
}
</script>
