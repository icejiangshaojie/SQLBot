// AI2BI 领域 API — 收敛 AI2BI 接口调用，避免散落在页面中
import { request } from '@/utils/request'
import type { EvidenceDetail } from '@/types/analysis'

export const ai2biApi = {
  // 证据链详情
  getEvidence: (recordId: number) => request.get<EvidenceDetail>(`/ai2bi/evidence/${recordId}`),
}