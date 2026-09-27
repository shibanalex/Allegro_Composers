<template>
  <NuxtLayout>
    <div class="py-24 text-center">
      <p class="title-script text-9xl">{{ error?.statusCode === 404 ? '404' : 'Увы' }}</p>
      <h1 class="mt-4 text-4xl italic">{{ error?.statusCode === 404 ? 'Здесь тишина' : 'Что-то сфальшивило' }}</h1>
      <p class="mt-4 font-elegant text-xl italic text-parchment-muted">
        {{ error?.statusCode === 404 ? 'Такой страницы нет — возможно, её ещё не сочинили.' : error?.statusMessage || 'Попробуйте обновить страницу.' }}
      </p>
      <button class="btn-secondary mt-10" @click="clearError({ redirect: '/' })">На главную</button>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
import type { NuxtError } from '#app'

defineProps<{ error: NuxtError }>()
</script>
