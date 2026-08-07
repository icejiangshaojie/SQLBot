import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AnalysisRunPanel from '@/views/chat/analysis/AnalysisRunPanel.vue'
import type { QaResult } from '@/types/analysis'

function qa(status: QaResult['status']): QaResult {
  return {
    status,
    findings: [],
    summary: {
      sql_facts: 3,
      backend_facts: 5,
      model_facts: 0,
      data_insufficient: 0,
      sourced_numbers: 6,
      derived_count: 5,
      inferred_count: 1,
      unsourced_count: 0,
    },
    renderable: status !== 'blocked',
  }
}

describe('AnalysisRunPanel 状态投影', () => {
  it('默认状态显示"待分析"', () => {
    const wrapper = mount(AnalysisRunPanel, { props: {} })
    expect(wrapper.text()).toContain('待分析')
  })

  it('completed 显示"分析完成"', () => {
    const wrapper = mount(AnalysisRunPanel, { props: { status: 'completed' } })
    expect(wrapper.text()).toContain('分析完成')
  })

  it('blocked 显示"分析已阻断"并渲染阻断 tag', () => {
    const wrapper = mount(AnalysisRunPanel, { props: { status: 'blocked', qa: qa('blocked') } })
    expect(wrapper.text()).toContain('分析已阻断')
    expect(wrapper.text()).toContain('质检阻断')
  })

  it('data_insufficient 显示"数据不足"', () => {
    const wrapper = mount(AnalysisRunPanel, { props: { status: 'data_insufficient' } })
    expect(wrapper.text()).toContain('数据不足')
  })

  it('渲染 Agent / 数据源 / 行数 meta', () => {
    const wrapper = mount(AnalysisRunPanel, {
      props: { status: 'completed', agentName: '存款', datasourceName: '测试库', rowCount: 120 },
    })
    const text = wrapper.text()
    expect(text).toContain('Agent: 存款')
    expect(text).toContain('数据源: 测试库')
    expect(text).toContain('行数: 120')
  })

  it('渲染 QA summary 计数（[SQL]/[计算]/[数据不足]）', () => {
    const wrapper = mount(AnalysisRunPanel, { props: { status: 'completed', qa: qa('passed') } })
    const text = wrapper.text()
    expect(text).toContain('[SQL] 3')
    expect(text).toContain('[计算] 5')
    expect(text).toContain('[数据不足] 0')
  })

  it('渲染 QA findings 且 block 等级带【阻断】前缀', () => {
    const q: QaResult = {
      status: 'blocked',
      findings: [
        { code: 'unsourced_numbers', severity: 'block', message: '无来源数字', fact_ids: [], source_refs: [] },
      ],
      summary: qa('blocked').summary,
      renderable: false,
    }
    const wrapper = mount(AnalysisRunPanel, { props: { status: 'blocked', qa: q } })
    expect(wrapper.text()).toContain('【阻断】')
    expect(wrapper.text()).toContain('无来源数字')
  })

  it('message 属性渲染提示文案', () => {
    const wrapper = mount(AnalysisRunPanel, { props: { status: 'failed', message: '分析引擎异常' } })
    expect(wrapper.text()).toContain('分析引擎异常')
  })
})