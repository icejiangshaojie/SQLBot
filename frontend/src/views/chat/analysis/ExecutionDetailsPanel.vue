<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ai2biApi } from '@/api/ai2bi'
import type { EvidenceDetail, AnalysisFact } from '@/types/analysis'
import ChartBlock from '@/views/chat/chat-block/ChartBlock.vue'

const props = withDefaults(
  defineProps<{
    recordId?: number
    message?: any
    loadingData?: boolean
    showLabel?: boolean
    thousandsSeparatorList?: Array<string>
  }>(),
  {
    recordId: undefined,
    message: null,
    loadingData: false,
    showLabel: false,
    thousandsSeparatorList: () => [],
  }
)

const emit = defineEmits(['update:showLabel', 'update:thousandsSeparatorList'])

const loading = ref(false)
const error = ref('')
const evidence = ref<EvidenceDetail | null>(null)
const activeTab = ref('evidence')

watch(
  () => props.recordId,
  () => {
    if (props.recordId) load()
  },
  { immediate: true }
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

function factTag(fact: AnalysisFact): string {
  return fact.source_type === 'sql' ? 'SQL' : fact.source_type === 'backend_calc' ? '计算' : '模型'
}

function factType(fact: AnalysisFact): string {
  if (fact.source_type === 'sql') return 'success'
  if (fact.source_type === 'backend_calc') return 'primary'
  return 'warning'
}

function qaType(status?: string): any {
  if (status === 'passed') return 'success'
  if (status === 'warning') return 'warning'
  return 'danger'
}

// ChartBlock 需要可写 v-model；用 computed 桥接到父级 prop
const showLabelModel = computed({
  get: () => props.showLabel,
  set: (v: boolean) => emit('update:showLabel', v),
})
const thousandsModel = computed({
  get: () => props.thousandsSeparatorList,
  set: (v: Array<string>) => emit('update:thousandsSeparatorList', v),
})
</script>

<template>
  <div class="execution-details">
    <el-tabs v-model="activeTab">
      <!-- 数据：复用 ChartBlock（SQL/表格/图表） -->
      <el-tab-pane label="数据" name="data">
        <div v-if="!message" class="center">暂无数据</div>
        <ChartBlock
          v-else
          v-model:show-label="showLabelModel"
          v-model:thousands-separator-list="thousandsModel"
          :message="message"
          :record-id="recordId"
          :loading-data="loadingData"
        />
      </el-tab-pane>

      <!-- SQL -->
      <el-tab-pane label="SQL" name="sql">
        <div v-if="loading" class="center">加载中...</div>
        <div v-else-if="error" class="center err">{{ error }}</div>
        <div v-else-if="!evidence?.found" class="center">未找到证据记录</div>
        <div v-else class="pane">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="行数">{{ evidence.sql_row_count }}</el-descriptions-item>
            <el-descriptions-item label="结果 hash">
              <code class="hash">{{ evidence.result_hash || '-' }}</code>
            </el-descriptions-item>
          </el-descriptions>
          <pre v-if="evidence.sql_text" class="sql">{{ evidence.sql_text }}</pre>
        </div>
      </el-tab-pane>

      <!-- 证据链 -->
      <el-tab-pane label="证据链" name="evidence">
        <div v-if="loading" class="center">加载中...</div>
        <div v-else-if="error" class="center err">{{ error }}</div>
        <div v-else-if="!evidence?.found" class="center">未找到证据记录</div>
        <div v-else class="pane">
          <!-- 意图快照 -->
          <section v-if="evidence.analysis_intent" class="sec">
            <h4>分析意图</h4>
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="类型">{{ evidence.analysis_intent.intent_type }}</el-descriptions-item>
              <el-descriptions-item label="是否触发分析">
                {{ evidence.analysis_intent.analysis_required ? '是' : '否' }}
              </el-descriptions-item>
              <el-descriptions-item label="判断原因">{{ evidence.analysis_intent.reason }}</el-descriptions-item>
            </el-descriptions>
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

          <!-- 指标口径 -->
          <section v-if="evidence.metric_context?.length" class="sec">
            <h4>指标口径</h4>
            <div v-for="m in evidence.metric_context" :key="m.id" class="metric">
              <b>{{ m.cn_name }}</b>
              <div v-if="m.calculation" class="dim">{{ m.calculation }}</div>
            </div>
          </section>
        </div>
      </el-tab-pane>

      <!-- QA -->
      <el-tab-pane label="QA" name="qa">
        <div v-if="loading" class="center">加载中...</div>
        <div v-else-if="error" class="center err">{{ error }}</div>
        <div v-else-if="!evidence?.qa_result" class="center">暂无质检结果</div>
        <div v-else class="pane">
          <div class="qa-status">
            <el-tag :type="qaType(evidence.qa_result.status)" size="small">
              {{ evidence.qa_result.status }}
            </el-tag>
            <template v-if="evidence.qa_result.summary">
              <span class="qa-metric">[SQL] {{ evidence.qa_result.summary.sql_facts }}</span>
              <span class="qa-metric">[计算] {{ evidence.qa_result.summary.backend_facts }}</span>
              <span class="qa-metric">[数据不足] {{ evidence.qa_result.summary.data_insufficient }}</span>
            </template>
          </div>
          <div v-if="evidence.qa_result.findings?.length" class="qa-findings">
            <div v-for="f in evidence.qa_result.findings" :key="f.code" class="qa-finding">
              <span class="lv" :class="f.severity">{{ f.severity }}</span>
              {{ f.message }}
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 专题分析 -->
      <el-tab-pane label="专题" name="topic">
        <div v-if="loading" class="center">加载中...</div>
        <div v-else-if="error" class="center err">{{ error }}</div>
        <div v-else-if="!evidence?.topic_plan && !evidence?.topic_bp_output" class="center">非专题分析，无专题数据</div>
        <div v-else class="pane">
          <div v-if="evidence.topic_contract" class="sec">
            <h4>专题口径</h4>
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="模板">{{ evidence.topic_contract.topic_template || '-' }}</el-descriptions-item>
              <el-descriptions-item label="指标">{{ (evidence.topic_contract.metrics || []).join(', ') }}</el-descriptions-item>
              <el-descriptions-item label="维度">{{ (evidence.topic_contract.dimensions || []).join(', ') }}</el-descriptions-item>
              <el-descriptions-item label="强制过滤">{{ (evidence.topic_contract.mandatory_filters || []).join(', ') }}</el-descriptions-item>
            </el-descriptions>
          </div>
          <div v-if="evidence.topic_plan?.queries?.length" class="sec">
            <h4>计划查询</h4>
            <el-table :data="evidence.topic_plan.queries" size="small" max-height="220">
              <el-table-column label="查询" prop="query_id" width="120" />
              <el-table-column label="用途" prop="purpose" min-width="160" />
              <el-table-column label="必需" width="70">
                <template #default="scope">
                  {{ scope.row.required ? '是' : '否' }}
                </template>
              </el-table-column>
              <el-table-column label="状态" width="110">
                <template #default="scope">
                  <el-tag :type="scope.row.status === 'completed' ? 'success' : scope.row.status === 'failed' ? 'danger' : 'info'" size="small">
                    {{ scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="行数" width="70">
                <template #default="scope">{{ scope.row.row_count ?? 0 }}</template>
              </el-table-column>
            </el-table>
          </div>
          <div v-if="evidence.topic_bp_output" class="sec">
            <h4>分析发现</h4>
            <div v-if="evidence.topic_bp_output.executive_summary?.length" class="bp-block">
              <b>摘要</b>
              <div v-for="(s, i) in evidence.topic_bp_output.executive_summary" :key="i">- {{ s.text }}</div>
            </div>
            <div v-if="evidence.topic_bp_output.findings?.length" class="bp-block">
              <b>关键发现</b>
              <div v-for="(f, i) in evidence.topic_bp_output.findings" :key="i">- {{ f.text }}</div>
            </div>
            <div v-if="evidence.topic_bp_output.limitations?.length" class="bp-block dim">
              <b>数据限制</b>
              <div v-for="(l, i) in evidence.topic_bp_output.limitations" :key="i">- {{ l }}</div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 路由与资产 -->
      <el-tab-pane label="路由与资产" name="route">
        <div v-if="loading" class="center">加载中...</div>
        <div v-else-if="error" class="center err">{{ error }}</div>
        <div v-else-if="!evidence?.found" class="center">未找到证据记录</div>
        <div v-else class="pane">
          <section v-if="evidence.route_info" class="sec">
            <h4>路由</h4>
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="Agent">
                {{ evidence.route_info.agent?.name || '通用模式' }}
              </el-descriptions-item>
              <el-descriptions-item label="业务域">{{ evidence.route_info.domain || '-' }}</el-descriptions-item>
              <el-descriptions-item label="子 Skill">{{ evidence.route_info.sub_skill || '-' }}</el-descriptions-item>
              <el-descriptions-item label="置信度">{{ evidence.route_info.confidence ?? 0 }}</el-descriptions-item>
            </el-descriptions>
          </section>
          <section v-if="evidence.model_name" class="sec">
            <h4>运行元数据</h4>
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="模型">{{ evidence.model_name }}</el-descriptions-item>
              <el-descriptions-item label="耗时">{{ evidence.duration_ms }} ms</el-descriptions-item>
              <el-descriptions-item label="Token">{{ evidence.total_tokens }}</el-descriptions-item>
            </el-descriptions>
          </section>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped lang="less">
.execution-details {
  margin-top: 8px;
  padding: 4px 12px 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid rgba(222, 224, 227, 1);
}
.center {
  padding: 24px 0;
  text-align: center;
  color: #798089;
}
.err { color: #d03050; }
.pane { padding-top: 8px; }
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
.metric {
  margin-bottom: 8px;
  font-size: 13px;
}
.bp-block {
  margin-bottom: 8px;
  font-size: 13px;
  color: #1d2129;
  b { display: block; margin-bottom: 4px; }
  div { line-height: 20px; }
  &.dim { color: #86909c; }
}
.qa-status {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  .qa-metric { color: #4e5969; }
}
.qa-findings { margin-top: 8px; }
.qa-finding {
  padding: 3px 0;
  font-size: 13px;
  .lv { font-weight: 600; }
  .lv.block { color: #d03050; }
  .lv.warning { color: #e6a23c; }
  .lv.info { color: #409eff; }
}
</style>