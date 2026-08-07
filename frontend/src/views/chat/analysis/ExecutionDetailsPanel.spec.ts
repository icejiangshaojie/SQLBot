import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ExecutionDetailsPanel from '@/views/chat/analysis/ExecutionDetailsPanel.vue'
import type { EvidenceDetail } from '@/types/analysis'

// mock ChartBlock，避免依赖真实图表组件
vi.mock('@/views/chat/chat-block/ChartBlock.vue', () => ({
  default: { template: '<div class="chart-block-stub">图表</div>' },
}))

const { getMock } = vi.hoisted(() => ({ getMock: vi.fn() }))
vi.mock('@/utils/request', () => ({
  request: { get: getMock },
}))

function makeEvidence(overrides: Partial<EvidenceDetail> = {}): EvidenceDetail {
  return {
    found: true,
    record_id: 87,
    analysis_status: 'completed',
    sql_row_count: 120,
    result_hash: 'abc123',
    sql_text: 'SELECT * FROM t',
    route_info: { agent: { name: '卡分析' }, domain: 'card', sub_skill: 'kpi', confidence: 0.9 },
    metric_context: [{ id: 1, cn_name: '消费金额', calculation: 'sum(amt)' }],
    qa_result: {
      status: 'passed', renderable: true, findings: [],
      summary: { sql_facts: 3, backend_facts: 2, model_facts: 0, data_insufficient: 1, sourced_numbers: 5, derived_count: 2, inferred_count: 0, unsourced_count: 0 },
    },
    analysis_facts: [
      { fact_id: 'f1', category: 'summary', label: '消费总额', value: 1234567, source_type: 'sql', input_refs: [], row_refs: [], status: 'verified' },
      { fact_id: 'f2', category: 'trend', label: '趋势方向', value: 100, source_type: 'backend_calc', formula: 'last-first', input_refs: [], row_refs: [], status: 'verified' },
    ],
    ...overrides,
  }
}

async function mountPanel(recordId = 87) {
  getMock.mockResolvedValue(makeEvidence())
  const wrapper = mount(ExecutionDetailsPanel, { props: { recordId } })
  await flushPromises()
  return wrapper
}

describe('ExecutionDetailsPanel 执行详情', () => {
  beforeEach(() => {
    getMock.mockReset()
  })

  it('以 recordId 主动加载证据', async () => {
    await mountPanel(87)
    expect(getMock).toHaveBeenCalledWith('/ai2bi/evidence/87')
  })

  it('证据链 tab 展示确定性事实区块与来源标签', async () => {
    const wrapper = await mountPanel()
    const text = wrapper.text()
    // el-table 内容由真实组件渲染，单测 stub 下断言区块标题与来源标签存在
    expect(text).toContain('确定性分析事实')
    expect(text).toContain('SQL') // 来源标签
  })

  it('QA tab 展示 findings 与 summary', async () => {
    const ev = makeEvidence()
    ev.qa_result!.findings = [
      { code: 'unsourced_numbers', severity: 'block', message: '无来源数字', fact_ids: [], source_refs: [] },
    ]
    getMock.mockResolvedValue(ev)
    const wrapper = mount(ExecutionDetailsPanel, { props: { recordId: 87 } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('无来源数字')
    expect(text).toContain('[SQL] 3')
  })

  it('SQL tab 展示 sql_text 与行数', async () => {
    const wrapper = await mountPanel()
    const text = wrapper.text()
    expect(text).toContain('SELECT * FROM t')
    expect(text).toContain('120')
  })

  it('路由 tab 展示 agent 与指标口径', async () => {
    const wrapper = await mountPanel()
    const text = wrapper.text()
    expect(text).toContain('卡分析')
    expect(text).toContain('消费金额')
  })

  it('未找到证据时显示空态', async () => {
    getMock.mockResolvedValue({ found: false })
    const wrapper = mount(ExecutionDetailsPanel, { props: { recordId: 99 } })
    await flushPromises()
    expect(wrapper.text()).toContain('未找到证据记录')
  })
})