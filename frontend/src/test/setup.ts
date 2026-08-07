import { config } from '@vue/test-utils'

// Element Plus 组件在单测环境不做真实注册，用轻量 stub 替代，避免大量 [Vue warn]。
config.global.stubs = {
  'el-tag': { template: '<span class="el-tag-stub"><slot /></span>' },
  'el-tabs': { template: '<div class="el-tabs-stub"><slot /></div>' },
  'el-tab-pane': { template: '<div class="el-tab-pane-stub"><slot /></div>' },
  'el-descriptions': { template: '<div class="el-descriptions-stub"><slot /></div>' },
  'el-descriptions-item': { template: '<div class="el-descriptions-item-stub"><slot /></div>' },
  'el-table': { template: '<div class="el-table-stub"><slot /></div>' },
  'el-table-column': {
    template: '<div class="el-table-column-stub"><slot :row="row" /></div>',
    setup(props, { slots }) {
      return () => slots.default?.({ row: { source_type: 'sql', label: '', display: '', value: '', formula: '', reason: '', status: '' } })
    },
  },
  'el-alert': { template: '<div class="el-alert-stub"><slot /></div>' },
}