<script setup lang="ts">
import BaseAnswer from './BaseAnswer.vue'
import { Chat, chatApi, ChatInfo, type ChatMessage, ChatRecord, questionApi } from '@/api/chat.ts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import ChartBlock from '@/views/chat/chat-block/ChartBlock.vue'
import { createSseDecoder } from '@/utils/sse'
import type { QaResult } from '@/types/analysis'
import AnalysisRunPanel from '@/views/chat/analysis/AnalysisRunPanel.vue'
import EvidenceDrawer from '@/views/chat/analysis/EvidenceDrawer.vue'
import MdComponent from '@/views/chat/component/MdComponent.vue'
import { ai2biApi } from '@/api/ai2bi'

const props = withDefaults(
  defineProps<{
    recordId?: number
    chatList?: Array<ChatInfo>
    currentChatId?: number
    currentChat?: ChatInfo
    message?: ChatMessage
    loading?: boolean
    reasoningName: 'sql_answer' | 'chart_answer' | Array<'sql_answer' | 'chart_answer'>
  }>(),
  {
    recordId: undefined,
    chatList: () => [],
    currentChatId: undefined,
    currentChat: () => new ChatInfo(),
    message: undefined,
    loading: false,
  }
)

const emits = defineEmits([
  'finish',
  'error',
  'stop',
  'scrollBottom',
  'update:loading',
  'update:chatList',
  'update:currentChat',
  'update:currentChatId',
])

const index = computed(() => {
  if (props.message?.index) {
    return props.message.index
  }
  if (props.message?.index === 0) {
    return 0
  }
  return -1
})

const _currentChatId = computed({
  get() {
    return props.currentChatId
  },
  set(v) {
    emits('update:currentChatId', v)
  },
})

const _currentChat = computed({
  get() {
    return props.currentChat
  },
  set(v) {
    emits('update:currentChat', v)
  },
})

const _chatList = computed({
  get() {
    return props.chatList
  },
  set(v) {
    emits('update:chatList', v)
  },
})

const _loading = computed({
  get() {
    return props.loading
  },
  set(v) {
    emits('update:loading', v)
  },
})

const stopFlag = ref(false)

// AI2BI Phase 0: 分析运行状态
const analysisStatus = ref('')
const analysisMessage = ref('')
const analysisQa = ref<QaResult | null>(null)
const evidenceDrawerVisible = ref(false)

const sendMessage = async () => {
  stopFlag.value = false
  _loading.value = true

  if (index.value < 0) {
    _loading.value = false
    return
  }

  const currentRecord: ChatRecord = _currentChat.value.records[index.value]

  let error: boolean = false
  if (_currentChatId.value === undefined) {
    error = true
  }
  if (error) return

  try {
    const controller: AbortController = new AbortController()
    const param = {
      question: currentRecord.question,
      chat_id: _currentChatId.value,
    }
    const response = await questionApi.add(param, controller)
    const reader = response.body.getReader()
    const textDecoder = new TextDecoder('utf-8')
    const sseDecoder = createSseDecoder()

    let sql_answer = ''
    let chart_answer = ''

    while (true) {
      if (stopFlag.value) {
        controller.abort()
        break
      }

      const { done, value } = await reader.read()
      if (done) {
        _loading.value = false
        break
      }

      const chunk = textDecoder.decode(value, { stream: true })
      const events = sseDecoder.push(chunk)
      for (const data of events) {
        if (data.code && data.code !== 200) {
          ElMessage({
            message: data.msg,
            type: 'error',
            showClose: true,
          })
          _loading.value = false
          return
        }

        switch (data.type) {
              case 'id':
                currentRecord.id = data.id
                _currentChat.value.records[index.value].id = data.id
                break
              case 'regenerate_record_id':
                currentRecord.regenerate_record_id = data.regenerate_record_id
                _currentChat.value.records[index.value].regenerate_record_id =
                  data.regenerate_record_id
                break
              case 'question':
                currentRecord.question = data.question
                _currentChat.value.records[index.value].question = data.question
                break
              case 'info':
                console.info(data.msg)
                break
              case 'brief':
                _currentChat.value.brief = data.brief
                _chatList.value.forEach((c: Chat) => {
                  if (c.id === _currentChat.value.id) {
                    c.brief = _currentChat.value.brief
                  }
                })
                break
              case 'error':
                currentRecord.error = data.content
                emits('error', currentRecord.id)
                break
              case 'sql-result':
                sql_answer += data.reasoning_content
                _currentChat.value.records[index.value].sql_answer = sql_answer
                break
              case 'sql':
                _currentChat.value.records[index.value].sql = data.content
                break
              case 'sql-data':
                getChatData(_currentChat.value.records[index.value].id)
                break
              case 'chart-result':
                chart_answer += data.reasoning_content
                _currentChat.value.records[index.value].chart_answer = chart_answer
                break
              case 'chart':
                _currentChat.value.records[index.value].chart = data.content
                break
              case 'analysis':
                // AI2BI: 独立分析阶段流式输出
                if (!_currentChat.value.records[index.value].analysis) {
                  _currentChat.value.records[index.value].analysis = ''
                }
                _currentChat.value.records[index.value].analysis += data.content
                break
              case 'evidence_qa':
                // AI2BI: 质检结果
                try {
                  const parsed = JSON.parse(data.content)
                  _currentChat.value.records[index.value].evidence_qa = parsed
                  analysisQa.value = parsed as QaResult
                } catch {
                  _currentChat.value.records[index.value].evidence_qa = data.content
                }
                break
              case 'knowledge_qa':
                // AI2BI: 知识问答模式（不生成 SQL，直接回答）
                if (!_currentChat.value.records[index.value].knowledge_answer) {
                  _currentChat.value.records[index.value].knowledge_answer = ''
                }
                _currentChat.value.records[index.value].knowledge_answer += data.content
                break
              case 'datasource':
                if (!_currentChat.value.datasource) {
                  _currentChat.value.datasource = data.id
                }
                break
              case 'finish':
                emits('finish', currentRecord.id)
                break
              case 'analysis_status':
                analysisStatus.value = data.status || ''
                analysisMessage.value = data.message || ''
                if (data.status) {
                  currentRecord.analysis_status = data.status
                }
                break
              case 'evidence_ready':
                analysisStatus.value = data.status || analysisStatus.value
                break
              case 'analysis_error':
                analysisMessage.value = data.message || analysisMessage.value
                analysisStatus.value = 'failed'
                break
            }
            await nextTick()
          }
    }
  } catch (error) {
    if (!currentRecord.error) {
      currentRecord.error = ''
    }
    if (currentRecord.error.trim().length !== 0) {
      currentRecord.error = currentRecord.error + '\n'
    }
    currentRecord.error = currentRecord.error + 'Error:' + error
    console.error('Error:', error)
    emits('error')
  } finally {
    _loading.value = false
  }
}

const loadingData = ref(false)

function getChatData(recordId?: number) {
  loadingData.value = true
  chatApi
    .get_chart_data(recordId)
    .then((response) => {
      _currentChat.value.records.forEach((record) => {
        if (record.id === recordId) {
          record.data = response
        }
      })
    })
    .finally(() => {
      loadingData.value = false
      emits('scrollBottom')
    })
}

function stop() {
  stopFlag.value = true
  _loading.value = false
  emits('stop')
}

const enableThousandsSeparatorList = ref<Array<string>>([])
const showLabel = ref<boolean>(false)

onBeforeUnmount(() => {
  stop()
})

function restoreAnalysisState() {
  // 历史刷新时，ChatRecord 不持久化 evidence_qa/analysis_status，
  // 从 Evidence 接口懒加载补全状态与 QA。
  const rec = props.message?.record
  if (!rec?.id || !rec.analysis || rec.evidence_qa) return
  ai2biApi
    .getEvidence(rec.id)
    .then((res: any) => {
      const d = res?.data ?? res
      if (!d?.found) return
      if (d.analysis_status) {
        analysisStatus.value = d.analysis_status
        rec.analysis_status = d.analysis_status
      }
      if (d.qa_result) {
        analysisQa.value = d.qa_result as QaResult
        rec.evidence_qa = d.qa_result
      }
    })
    .catch(() => {})
}

onMounted(() => {
  if (props.message?.record?.id && props.message?.record?.finish) {
    getChatData(props.message.record.id)
    restoreAnalysisState()
  }
})

defineExpose({ sendMessage, index: () => index.value, stop })
</script>

<template>
  <BaseAnswer v-if="message" :message="message" :reasoning-name="reasoningName" :loading="_loading">
    <ChartBlock
      v-model:show-label="showLabel"
      v-model:thousands-separator-list="enableThousandsSeparatorList"
      style="margin-top: 6px"
      :message="message"
      :record-id="recordId"
      :loading-data="loadingData"
    />
    <!-- AI2BI: 知识问答模式回答 -->
    <div v-if="message?.record?.knowledge_answer" class="ai2bi-knowledge-qa">
      <MdComponent :message="message.record.knowledge_answer" />
    </div>
    <!-- AI2BI: 分析运行状态面板 -->
    <AnalysisRunPanel
      v-if="analysisStatus || message?.record?.analysis_status"
      :status="analysisStatus || message?.record?.analysis_status"
      :message="analysisMessage"
      :qa="analysisQa || (message?.record?.evidence_qa as any)"
      :datasource-name="message?.record?.datasource ? String(message.record.datasource) : ''"
      :row-count="message?.record?.data?.fields?.length"
    />
    <!-- AI2BI: 分析结果 -->
    <div v-if="message?.record?.analysis" class="ai2bi-analysis">
      <MdComponent :message="message.record.analysis" />
    </div>
    <!-- AI2BI: 证据链入口 -->
    <div v-if="message?.record?.id" class="ai2bi-evidence-chain">
      <el-button size="small" text type="primary" @click="evidenceDrawerVisible = true">
        📋 查看证据链
      </el-button>
    </div>
    <EvidenceDrawer
      v-model="evidenceDrawerVisible"
      :record-id="message?.record?.id"
    />
    <slot></slot>
    <template #tool>
      <slot name="tool"></slot>
    </template>
    <template #footer>
      <slot name="footer"></slot>
    </template>
  </BaseAnswer>
</template>

<style scoped lang="less">
// AI2BI 统一风格：与 SQLBot 原始 answer-container 一致
// 原始风格: 16px font, 24px line-height, #f8f9fa bg, 12px radius, rgba(222,224,227) border
.ai2bi-knowledge-qa {
  margin-top: 12px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 12px;
  border: 1px solid rgba(222, 224, 227, 1);
  font-size: 16px;
  line-height: 24px;
  color: rgba(31, 35, 41, 1);
  .knowledge-content {
    :deep(h2) { font-size: 18px; margin: 12px 0 6px; color: rgba(31, 35, 41, 1); font-weight: 500; }
    :deep(h3) { font-size: 16px; margin: 10px 0 4px; color: rgba(31, 35, 41, 1); font-weight: 500; }
    :deep(p) { margin: 6px 0; }
    :deep(ul), :deep(ol) { padding-left: 20px; margin: 6px 0; }
    :deep(li) { margin: 2px 0; }
    :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; }
    :deep(th), :deep(td) { border: 1px solid rgba(222, 224, 227, 1); padding: 6px 10px; font-size: 14px; }
    :deep(th) { background: #f0f2f5; font-weight: 500; }
    :deep(pre) { background: #1e1e1e; color: #d4d4d4; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; }
    :deep(code) { font-family: 'Consolas', monospace; }
  }
}
.ai2bi-analysis {
  margin-top: 12px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 12px;
  border: 1px solid rgba(222, 224, 227, 1);
  font-size: 16px;
  line-height: 24px;
  color: rgba(31, 35, 41, 1);
  .analysis-content {
    :deep(h2) { font-size: 18px; margin: 12px 0 6px; color: rgba(31, 35, 41, 1); font-weight: 500; }
    :deep(h3) { font-size: 16px; margin: 10px 0 4px; color: rgba(31, 35, 41, 1); font-weight: 500; }
    :deep(p) { margin: 6px 0; }
    :deep(ul), :deep(ol) { padding-left: 20px; margin: 6px 0; }
    :deep(li) { margin: 2px 0; }
    :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; }
    :deep(th), :deep(td) { border: 1px solid rgba(222, 224, 227, 1); padding: 6px 10px; font-size: 14px; }
    :deep(th) { background: #f0f2f5; font-weight: 500; }
    :deep(pre) { background: #1e1e1e; color: #d4d4d4; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; }
    :deep(code) { font-family: 'Consolas', monospace; }
  }
}
.ai2bi-evidence-chain {
  margin-top: 8px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 12px;
  border: 1px solid rgba(222, 224, 227, 1);
  .evidence-title { font-size: 14px; font-weight: 500; color: rgba(31, 35, 41, 1); }
  .evidence-detail { padding: 4px 0; }
  .evidence-summary { margin-bottom: 8px; }
  .evidence-tag {
    display: inline-block; margin-right: 12px; padding: 2px 8px; border-radius: 4px; font-size: 12px;
    &.sql { background: #e8f5e9; color: #2e7d32; }
    &.calc { background: #e3f2fd; color: #1565c0; }
    &.inferred { background: #fff3e0; color: #e65100; }
  }
  .evidence-violations { margin-top: 6px; }
  .violation-item { font-size: 14px; color: #e6a23c; margin: 4px 0; }
}
</style>
