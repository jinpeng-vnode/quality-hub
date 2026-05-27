<template>
  <div class="not-found-view">
    <a-result status="404" title="404" sub-title="页面不存在">
      <template #extra>
        <a-button type="primary" @click="$router.push('/projects')">返回首页</a-button>
      </template>
    </a-result>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({ name: 'NotFoundView' })
</script>
