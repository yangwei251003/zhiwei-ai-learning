<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'

import AppShell from '@/components/AppShell.vue'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const appStore = useAppStore()
onMounted(() => appStore.initializeTheme())
</script>

<template>
  <RouterView v-if="route.meta.public" />
  <AppShell v-else>
    <RouterView />
  </AppShell>
</template>
