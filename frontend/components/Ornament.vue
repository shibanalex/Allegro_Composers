<template>
  <svg viewBox="0 0 320 40" fill="none" class="text-gold/70" aria-hidden="true">
    <defs>
      <linearGradient id="orn-fade-l" x1="0" x2="1"><stop offset="0" stop-color="currentColor" stop-opacity="0" /><stop offset="1" stop-color="currentColor" /></linearGradient>
      <linearGradient id="orn-fade-r" x1="1" x2="0"><stop offset="0" stop-color="currentColor" stop-opacity="0" /><stop offset="1" stop-color="currentColor" /></linearGradient>
    </defs>
    <path d="M0 20h112" stroke="url(#orn-fade-l)" stroke-width=".8" />
    <path d="M208 20h112" stroke="url(#orn-fade-r)" stroke-width=".8" />
    <!-- scrolls -->
    <g stroke="currentColor" stroke-width="1" stroke-linecap="round">
      <path d="M112 20c10 0 14-10 24-10 7 0 9 6 5 9-3 2-7 0-6-3" />
      <path d="M112 20c10 0 14 10 24 10 7 0 9-6 5-9-3-2-7 0-6 3" />
      <path d="M208 20c-10 0-14-10-24-10-7 0-9 6-5 9 3 2 7 0 6-3" />
      <path d="M208 20c-10 0-14 10-24 10-7 0-9-6-5-9 3-2 7 0 6 3" />
    </g>
    <!-- central diamond -->
    <path d="M160 11l8 9-8 9-8-9z" stroke="currentColor" stroke-width="1" />
    <path d="M160 15.5l4 4.5-4 4.5-4-4.5z" fill="currentColor" />
    <circle cx="146" cy="20" r="1.4" fill="currentColor" />
    <circle cx="174" cy="20" r="1.4" fill="currentColor" />
  </svg>
</template>
