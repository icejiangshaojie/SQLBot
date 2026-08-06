<script setup lang="ts">
import BaseAnswer from './BaseAnswer.vue'
import { Chat, chatApi, ChatInfo, type ChatMessage, ChatRecord, questionApi } from '@/api/chat.ts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import ChartBlock from '@/views/chat/chat-block/ChartBlock.vue'
import JSONBig from 'json-bigint'
import md from '@/utils/markdown'

// AI2BI: 分析结果 Markdown 渲染
const renderMarkdown = (text: string) => {
  if (!text) return ''
  return md.render(text)
}

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
    const decoder = new TextDecoder('utf-8')

    let sql_answer = ''
    let chart_answer = ''

    let tempResult = ''

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

      let chunk = decoder.decode(value, { stream: true })
      tempResult += chunk
      const split = tempResult.match(/data:.*}\n\n/g)
      if (split) {
        chunk = split.join('')
        tempResult = tempResult.replace(chunk, '')
      } else {
        continue
      }
      if (chunk && chunk.startsWith('data:{')) {
        if (split) {
          for (const str of split) {
            let data
            try {
              data = JSONBig.parse(str.replace('data:{', '{'))
            } catch (err) {
              console.error('JSON string:', str)
              throw err
            }

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
                  _currentChat.value.records[index.value].evidence_qa = JSON.parse(data.content)
                } catch { _currentChat.value.records[index.value].evidence_qa = data.content }
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
            }
            await nextTick()
          }
        }
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

onMounted(() => {
  if (props.message?.record?.id && props.message?.record?.finish) {
    getChatData(props.message.record.id)
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
      <div class="knowledge-content" v-html="renderMarkdown(message.record.knowledge_answer)"></div>
    </div>
    <!-- AI2BI: 分析结果 + 证据链 -->
    <div v-if="message?.record?.analysis" class="ai2bi-analysis">
      <div class="analysis-content" v-html="renderMarkdown(message.record.analysis)"></div>
    </div>
    <div v-if="message?.record?.evidence_qa" class="ai2bi-evidence-chain">
      <el-collapse>
        <el-collapse-item>
          <template #title>
            <span class="evidence-title">
              📋 证据链
              <el-tag v-if="message.record.evidence_qa.passed" type="success" size="small" style="margin-left: 8px">✅ 质检通过</el-tag>
              <el-tag v-else type="warning" size="small" style="margin-left: 8px">⚠️ 质检警告</el-tag>
            </span>
          </template>
          <div class="evidence-detail">
            <div v-if="message.record.evidence_qa.evidence_summary" class="evidence-summary">
              <span class="evidence-tag sql">[SQL] {{ message.record.evidence_qa.evidence_summary.sourced_count }} 个</span>
              <span class="evidence-tag calc">[计算] {{ message.record.evidence_qa.evidence_summary.derived_count }} 个</span>
              <span class="evidence-tag inferred">[模型推导] {{ message.record.evidence_qa.evidence_summary.inferred_count }} 个</span>
            </div>
            <div v-if="message.record.evidence_qa.answer_violations?.length" class="evidence-violations">
              <div v-for="v in message.record.evidence_qa.answer_violations" :key="v" class="violation-item">⚠️ {{ v }}</div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
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
