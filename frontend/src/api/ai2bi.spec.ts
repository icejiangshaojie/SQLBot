import { describe, it, expect, vi, beforeEach } from 'vitest'

// vi.hoisted 用于在 vi.mock factory 被提升前创建 mock，避免 "Cannot access before initialization"
const { getMock } = vi.hoisted(() => ({ getMock: vi.fn() }))

vi.mock('@/utils/request', () => ({
  request: { get: getMock },
}))

import { ai2biApi } from '@/api/ai2bi'
import type { EvidenceDetail } from '@/types/analysis'

describe('ai2biApi.getEvidence', () => {
  beforeEach(() => {
    getMock.mockReset()
  })

  it('以 recordId 拼接证据链 URL', async () => {
    const payload: EvidenceDetail = { record_id: 87, analysis_status: 'completed' }
    getMock.mockResolvedValue(payload)

    await ai2biApi.getEvidence(87)

    expect(getMock).toHaveBeenCalledTimes(1)
    expect(getMock.mock.calls[0][0]).toBe('/ai2bi/evidence/87')
  })

  it('返回解析后的 EvidenceDetail', async () => {
    const payload: EvidenceDetail = {
      record_id: 87,
      evidence_id: 8,
      analysis_status: 'blocked',
      qa_result: { status: 'blocked', findings: [], summary: {
        sql_facts: 0, backend_facts: 0, model_facts: 0, data_insufficient: 0,
        sourced_numbers: 0, derived_count: 0, inferred_count: 0, unsourced_count: 0,
      }, renderable: false },
    }
    getMock.mockResolvedValue(payload)

    const res = await ai2biApi.getEvidence(87)
    expect(res).toMatchObject({ evidence_id: 8, analysis_status: 'blocked' })
  })
})