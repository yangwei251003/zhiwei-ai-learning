<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'

const route = useRoute()
const announcement = computed(() => `已进入${String(route.meta.title ?? route.name ?? '页面')}`)
</script>

<template>
  <RouterView v-slot="{ Component, route: currentRoute }">
    <Transition name="auth-route" appear>
      <component :is="Component" :key="currentRoute.fullPath" />
    </Transition>
  </RouterView>
  <div class="sr-only" aria-live="polite" aria-atomic="true">{{ announcement }}</div>
</template>
