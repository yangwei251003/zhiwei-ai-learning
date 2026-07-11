<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  focused: boolean
  celebrating?: boolean
}>(), {
  celebrating: false,
})

const mascotSource = computed(() => props.celebrating
  ? '/assets/mascot-celebrate.png'
  : '/assets/mascot-hero.png')
</script>

<template>
  <figure
    class="brand-constellation"
    :class="{ 'is-focused': focused, 'is-celebrating': celebrating }"
    aria-label="知微智学学习星图"
  >
    <div class="constellation-decoration" aria-hidden="true">
      <span class="constellation-grid" />
      <span v-for="orbit in 3" :key="orbit" :class="`constellation-orbit orbit-${orbit}`" />
      <i v-for="star in 18" :key="star" :class="`constellation-star star-${star}`" />
      <i v-for="star in 12" :key="`focus-${star}`" :class="`focus-star focus-star-${star}`" />
    </div>

    <ul class="constellation-nodes" aria-label="智能学习环节">
      <li class="constellation-node node-profile"><span>画像</span></li>
      <li class="constellation-node node-resource"><span>资源</span></li>
      <li class="constellation-node node-path"><span>路径</span></li>
    </ul>

    <img
      class="constellation-mascot"
      :src="mascotSource"
      :alt="celebrating ? '正在庆祝学习成果的小智析析' : '在学习星图中探索的小智析析'"
    />
  </figure>
</template>
