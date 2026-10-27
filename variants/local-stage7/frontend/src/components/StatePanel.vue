<script setup>
import { PhWarningCircle as WarningCircle } from '@phosphor-icons/vue'

defineProps({
  state: { type: String, required: true },
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
})
defineEmits(['action'])
</script>

<template>
  <div v-if="state === 'loading'" class="skeleton-stack" aria-label="正在加载" aria-live="polite">
    <span v-for="n in 4" :key="n" class="skeleton-line" :style="{ width: `${100 - n * 9}%` }" />
  </div>
  <section v-else class="state-panel" :class="`state-${state}`" :aria-live="state === 'error' ? 'assertive' : 'polite'">
    <WarningCircle v-if="state === 'error'" :size="38" weight="duotone" />
    <img v-else src="/assets/mascot-empty.png" width="132" height="132" alt="" />
    <h2>{{ title }}</h2>
    <p>{{ message }}</p>
    <button v-if="actionLabel" class="secondary-button" type="button" @click="$emit('action')">{{ actionLabel }}</button>
  </section>
</template>
