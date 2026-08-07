<script setup lang="ts">
import { ref, watch } from 'vue'
import { ai2biApi } from '@/api/ai2bi'
import type { EvidenceDetail, AnalysisFact } from '@/types/analysis'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    recordId?: number
  }>(),
  {
    modelValue: false,
    recordId: undefined,
  }
)

const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
const loading = ref(false)
const evidence = ref<EvidenceDetail | null>(null)
const error = ref('')

watch(
  () => props.modelValue,
  (v) => {
    visible.value = v
    if (v && props.recordId) {
      load()
    }
  }
)

watch(
  () => props.recordId,
  () => {
    if (visible.value && props.recordId) {
      load()
    }
  }
)

async function load() {
  if (!props.recordId) return
  loading.value = true
  error.value = ''
  evidence.value = null
  try {
    const res = await ai2biApi.getEvidence(props.recordId)
    evidence.value = res as EvidenceDetail
  } catch (e: any) {
    error.value = e?.message || '加载证据失败'
  } finally {
    loading.value = false
  }
}

function close() {
  visible.value = false
  emit('update:modelValue', false)
}

function factTag(fact: AnalysisFact): string {
  return fact.source_type === 'sql' ? 'SQL' : fact.source_type === 'backend_calc' ? '计算' : '模型'
}

function factType(fact: AnalysisFact): string {
  if (fact.source_type === 'sql') return 'success'
  if (fact.source_type === 'backend_calc') return 'primary'
  return 'warning'
}
</script>

<template>
  <el-drawer
    :model-value="visible"
    :title="`证据链 #${props.recordId ?? ''}`"
    size="480px"
    @close="close"
  >
    <div v-if="loading" class="center">加载中...</div>
    <div v-else-if="error" class="center err">{{ error }}</div>
    <div v-else-if="!evidence?.found" class="center">未找到证据记录</div>
    <div v-else class="evidence-body">
      <!-- 状态 -->
      <el-alert
        v-if="evidence.analysis_status"
        :type="evidence.analysis_status === 'blocked' || evidence.analysis_status === 'failed'
          ? 'error'
          : evidence.analysis_status === 'completed' ? 'success' : 'warning'"
        :closable="false"
        :title="`分析状态：${evidence.analysis_status}`"
        class="block"
      >
        <span v-if="evidence.analysis_error">{{ evidence.analysis_error }}</span>
      </el-alert>

      <!-- 意图快照（Q2） -->
      <section v-if="evidence.analysis_intent" class="sec">
        <h4>分析意图</h4>
        <el-descriptions :column="1" size="small">
          <el-descriptions-item label="类型">
            {{ evidence.analysis_intent.intent_type }}
          </el-descriptions-item>
          <el-descriptions-item label="是否触发分析">
            {{ evidence.analysis_intent.analysis_required ? '是' : '否' }}
          </el-descriptions-item>
          <el-descriptions-item label="判断原因">
            {{ evidence.analysis_intent.reason }}
          </el-descriptions-item>
        </el-descriptions>
      </section>

      <!-- 路由 -->
      <section v-if="evidence.route_info" class="sec">
        <h4>路由</h4>
        <el-descriptions :column="1" size="small">
          <el-descriptions-item label="Agent">
            {{ evidence.route_info.agent?.name || '通用模式' }}
          </el-descriptions-item>
          <el-descriptions-item label="业务域">
            {{ evidence.route_info.domain || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="子 Skill">
            {{ evidence.route_info.sub_skill || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            {{ evidence.route_info.confidence ?? 0 }}
          </el-descriptions-item>
        </el-descriptions>
      </section>

      <!-- SQL 与执行 -->
      <section class="sec">
        <h4>SQL 与执行</h4>
        <el-descriptions :column="1" size="small">
          <el-descriptions-item label="行数">
            {{ evidence.sql_row_count }}
          </el-descriptions-item>
          <el-descriptions-item label="结果 hash">
            <code class="hash">{{ evidence.result_hash || '-' }}</code>
          </el-descriptions-item>
        </el-descriptions>
        <pre v-if="evidence.sql_text" class="sql">{{ evidence.sql_text }}</pre>
      </section>

      <!-- 确定性事实 -->
      <section v-if="evidence.analysis_facts?.length" class="sec">
        <h4>确定性分析事实</h4>
        <el-table :data="evidence.analysis_facts" size="small" max-height="260">
          <el-table-column label="标签" prop="label" min-width="140" />
          <el-table-column label="来源" width="70">
            <template #default="{ row }">
              <el-tag :type="factType(row) as any" size="small">{{ factTag(row) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="值" width="110">
            <template #default="{ row }">
              <span :class="{ dim: row.status === 'data_insufficient' }">
                {{ row.display || row.value || '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="公式/原因" min-width="140">
            <template #default="{ row }">
              <span v-if="row.formula" class="formula">{{ row.formula }}</span>
              <span v-else-if="row.reason" class="dim">{{ row.reason }}</span>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <!-- QA -->
      <section v-if="evidence.qa_result" class="sec">
        <h4>质检</h4>
        <el-tag
          :type="evidence.qa_result.status === 'passed' ? 'success'
            : evidence.qa_result.status === 'warning' ? 'warning' : 'danger'"
          size="small"
        >
          {{ evidence.qa_result.status }}
        </el-tag>
        <div v-if="evidence.qa_result.findings?.length" class="qa-findings">
          <div v-for="f in evidence.qa_result.findings" :key="f.code" class="qa-finding">
            <span class="lv" :class="f.severity">{{ f.severity }}</span>
            {{ f.message }}
          </div>
        </div>
      </section>

      <!-- 指标上下文 -->
      <section v-if="evidence.metric_context?.length" class="sec">
        <h4>指标口径</h4>
        <div v-for="m in evidence.metric_context" :key="m.id" class="metric">
          <b>{{ m.cn_name }}</b>
          <div v-if="m.calculation" class="dim">{{ m.calculation }}</div>
        </div>
      </section>
    </div>
  </el-drawer>
</template>

<style scoped lang="less">
.center {
  padding: 40px 0;
  text-align: center;
  color: #798089;
}
.err { color: #d03050; }
.block { margin-bottom: 12px; }
.sec {
  margin-bottom: 16px;

  h4 {
    margin: 0 0 8px;
    font-size: 14px;
    color: #1d2129;
  }
}
.sql {
  margin-top: 8px;
  padding: 8px;
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.hash { font-family: Consolas, monospace; font-size: 12px; }
.dim { color: #86909c; }
.formula { color: #165dff; font-size: 12px; }
.qa-findings { margin-top: 8px; }
.qa-finding {
  padding: 3px 0;
  font-size: 13px;
  .lv { font-weight: 600; }
  .lv.block { color: #d03050; }
  .lv.warning { color: #e6a23c; }
  .lv.info { color: #409eff; }
}
.metric {
  margin-bottom: 8px;
  font-size: 13px;
}
</style>