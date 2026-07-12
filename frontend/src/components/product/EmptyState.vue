<script setup lang="ts">
withDefaults(defineProps<{ title: string; description: string; action?: string; image?: string }>(), { image: '/assets/mascot-empty.png' })
defineEmits<{ action: [] }>()
</script>
<template><div class="empty-state"><img :src="image" alt="小智析析正在引导" loading="lazy" /><h2>{{ title }}</h2><p>{{ description }}</p><button v-if="action" class="primary-button" @click="$emit('action')">{{ action }}</button></div></template>
