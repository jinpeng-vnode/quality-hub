<template>
  <div class="login-page">
    <a-card class="login-card" title="登录 Quality Hub">
      <p class="hint">使用项目管理的账号和密码登录</p>
      <a-form layout="vertical" @submit.prevent="submit">
        <a-form-item label="账号" required>
          <a-input v-model:value="form.username" autocomplete="username" placeholder="项目管理账号" />
        </a-form-item>
        <a-form-item label="密码" required>
          <a-input-password v-model:value="form.password" autocomplete="current-password" @pressEnter="submit" />
        </a-form-item>
        <a-button type="primary" block :loading="loading" @click="submit">登录</a-button>
      </a-form>
    </a-card>
  </div>
</template>

<script lang="ts">
import { defineComponent, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../stores/auth'

export default defineComponent({
  name: 'LoginView',
  setup() {
    const route = useRoute()
    const router = useRouter()
    const auth = useAuthStore()
    const form = reactive({ username: '', password: '' })
    const loading = ref(false)

    async function submit() {
      if (!form.username.trim() || !form.password) {
        message.warning('请填写账号和密码')
        return
      }
      loading.value = true
      try {
        await auth.login(form.username.trim(), form.password)
        form.password = ''
        const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
          ? route.query.redirect : '/projects'
        router.replace(redirect)
      } catch { /* 拦截器已提示 */ }
      finally { loading.value = false }
    }

    return { form, loading, submit }
  },
})
</script>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #f5f5f5; }
.login-card { width: 360px; }
.hint { color: rgba(0, 0, 0, 0.45); margin-bottom: 16px; }
</style>
