import { config } from '@vue/test-utils'

// Element Plus 组件在单测环境不做真实注册，用轻量 stub 替代，避免大量 [Vue warn]。
config.global.stubs = {
  'el-tag': { template: '<span class="el-tag-stub"><slot /></span>' },
}