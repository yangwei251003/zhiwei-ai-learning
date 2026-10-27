<script setup lang="ts">defineProps<{ label?: string }>()</script>
<template><div class="ai-creating" role="status"><div class="creation-orbit"><img src="/assets/mascot-thinking.png" alt="" /><i /><i /><i /></div><div><strong>{{ label || 'AI 正在创造' }}</strong><p>画像分析 → 知识检索 → 内容编排</p><span class="thinking-dots"><b /><b /><b /></span></div></div></template>
