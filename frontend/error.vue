<template>
  <NuxtLayout>
    <div class="py-24 text-center">
      <p class="title-script text-9xl">{{ error?.statusCode === 404 ? '404' : 'Увы' }}</p>
      <h1 class="mt-4 text-4xl italic">{{ error?.statusCode === 404 ? 'Здесь тишина' : 'Что-то сфальшивило' }}</h1>
      <p class="mt-4 font-elegant text-xl italic text-parchment-muted">
        {{ error?.statusCode === 404 ? 'Такой страницы нет — возможно, её ещё не сочинили.' : error?.statusMessage || 'Попробуйте обновить страницу.' }}
      </p>
      <div class="mt-10 flex flex-wrap justify-center gap-3">
        <button v-if="error?.statusCode !== 404" class="btn-primary" @click="reload">Обновить страницу</button>
        <button class="btn-secondary" @click="clearError({ redirect: '/' })">На главную</button>
      </div>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
import type { NuxtError } from '#app'

defineProps<{ error: NuxtError }>()
const reload = () => location.reload()
</script>
