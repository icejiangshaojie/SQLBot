<script setup lang="ts">
import { computed } from 'vue'
import type { AnalysisRunStatus, QaResult } from '@/types/analysis'

const props = withDefaults(
  defineProps<{
    status?: string
    message?: string
    qa?: QaResult | null
    agentName?: string
    datasourceName?: string
    rowCount?: number
  }>(),
  {
    status: '',
    message: '',
    qa: null,
    agentName: '',
    datasourceName: '',
    rowCount: undefined,
  }
)

const statusMeta = computed(() => {
  const map: Record<string, { label: string; type: string; icon: string }> = {
    completed: { label: '分析完成', type: 'success', icon: '✅' },
    generating: { label: '分析中', type: 'primary', icon: '⏳' },
    started: { label: '开始分析', type: 'primary', icon: '⏳' },
    data_insufficient: { label: '数据不足', type: 'warning', icon: '⚠️' },
    blocked: { label: '分析已阻断', type: 'danger', icon: '🚫' },
    failed: { label: '分析失败', type: 'danger', icon: '❌' },
    skipped: { label: '分析跳过', type: 'info', icon: '⏭️' },
  }
  return map[props.status] || { label: props.status || '待分析', type: 'info', icon: '➖' }
})

const qaSummary = computed(() => props.qa?.summary)
</script>

<template>
  <div class="analysis-run-panel">
    <div class="row">
      <span class="status">
        <el-tag :type="statusMeta.type as any" size="small" effect="light">
          {{ statusMeta.icon }} {{ statusMeta.label }}
        </el-tag>
      </span>
      <span v-if="agentName" class="meta">Agent: {{ agentName }}</span>
      <span v-if="datasourceName" class="meta">数据源: {{ datasourceName }}</span>
      <span v-if="rowCount !== undefined" class="meta">行数: {{ rowCount }}</span>
    </div>

    <div v-if="message" class="message">{{ message }}</div>

    <div v-if="qa" class="qa-row">
      <el-tag
        v-if="qa.status === 'passed'"
        type="success"
        size="small"
      >质检通过</el-tag>
      <el-tag
        v-else-if="qa.status === 'warning'"
        type="warning"
        size="small"
      >质检警告</el-tag>
      <el-tag
        v-else
        type="danger"
        size="small"
      >质检阻断</el-tag>

      <template v-if="qaSummary">
        <span class="qa-metric">[SQL] {{ qaSummary.sql_facts }}</span>
        <span class="qa-metric">[计算] {{ qaSummary.backend_facts }}</span>
        <span class="qa-metric">[数据不足] {{ qaSummary.data_insufficient }}</span>
      </template>
    </div>

    <div v-if="qa?.findings?.length" class="findings">
      <div
        v-for="f in qa.findings"
        :key="f.code"
        class="finding"
      >
        <span class="level" :class="f.severity">{{ levelText(f.severity) }}</span>
        {{ f.message }}
      </div>
    </div>
  </div>
</template>

<script lang="ts">
function levelText(sev: string): string {
  if (sev === 'block') return '【阻断】'
  if (sev === 'warning') return '【警告】'
  return '【提示】'
}
</script>

<style scoped lang="less">
.analysis-run-panel {
  margin-top: 10px;
  padding: 10px 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid rgba(222, 224, 227, 1);
  font-size: 13px;

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;

    .meta {
      color: #798089;
    }
  }

  .message {
    margin-top: 6px;
    color: #4e5969;
  }

  .qa-row {
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;

    .qa-metric {
      color: #4e5969;
    }
  }

  .findings {
    margin-top: 6px;

    .finding {
      padding: 2px 0;
      color: #4e5969;

      .level {
        font-weight: 600;
        margin-right: 4px;
      }
      .level.block { color: #d03050; }
      .level.warning { color: #e6a23c; }
      .level.info { color: #409eff; }
    }
  }
}
</style>