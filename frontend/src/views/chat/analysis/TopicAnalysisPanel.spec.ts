import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TopicAnalysisPanel from '@/views/chat/analysis/TopicAnalysisPanel.vue'
import type { BpOutput } from '@/types/analysis'

function makeBp(): BpOutput {
  return {
    executive_summary: [{ category: 'summary', text: '7月消费金额上升', fact_ids: ['trend_direction'], query_ids: [] }],
    findings: [
      { category: 'trend', text: '峰值在7月18日', fact_ids: ['trend_peak'], query_ids: [] },
      { category: 'structure', text: '线上渠道占比最高', fact_ids: ['structure_share'], query_ids: [] },
    ],
    limitations: ['当前结果未包含活动前基准'],
    next_questions: ['是否补充活动前30天数据？'],
    markdown: '## 摘要\n- 7月消费金额上升',
  }
}

describe('TopicAnalysisPanel 专题分析', () => {
  it('无 BP 输出时不渲染', () => {
    const wrapper = mount(TopicAnalysisPanel, { props: { bp: null } })
    expect(wrapper.find('.topic-analysis').exists()).toBe(false)
  })

  it('渲染摘要与关键发现', () => {
    const wrapper = mount(TopicAnalysisPanel, { props: { bp: makeBp() } })
    const text = wrapper.text()
    expect(text).toContain('摘要')
    expect(text).toContain('7月消费金额上升')
    expect(text).toContain('关键发现')
    expect(text).toContain('峰值在7月18日')
  })

  it('渲染数据限制与下一步', () => {
    const wrapper = mount(TopicAnalysisPanel, { props: { bp: makeBp() } })
    const text = wrapper.text()
    expect(text).toContain('数据限制')
    expect(text).toContain('未包含活动前基准')
    expect(text).toContain('下一步')
    expect(text).toContain('是否补充活动前30天数据')
  })
})