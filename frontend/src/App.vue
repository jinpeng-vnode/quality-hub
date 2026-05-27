<template>
  <a-config-provider :theme="theme" :locale="zhCN">
    <MainLayout />
  </a-config-provider>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import MainLayout from './layouts/MainLayout.vue'

const theme = {
  token: {
    colorPrimary: '#1677ff',
    borderRadius: 6,
    fontSize: 14,
  },
  components: {
    Table: {
      headerBg: '#fafafa',
      headerColor: 'rgba(0,0,0,0.88)',
      rowHoverBg: '#f5f5f5',
    },
    Card: {
      paddingLG: 20,
    },
  },
}

export default defineComponent({
  name: 'App',
  components: { MainLayout },
  setup() {
    return { theme, zhCN }
  },
})
</script>
