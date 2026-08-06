<template>
  <div class="ai2bi-assets">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">数据资产</h1>
        <p class="page-subtitle">表字典、字段字典、核心指标与业务规则</p>
      </div>
    </div>

    <div class="layout-body">
      <!-- Left: domain nav -->
      <div class="domain-panel">
        <div class="panel-header">
          <el-icon :size="14"><Grid /></el-icon>
          <span>业务域</span>
        </div>
        <div class="domain-list">
          <div
            v-for="d in domains"
            :key="d.code"
            :class="['domain-item', { active: selectedDomain === d.code }]"
            @click="selectedDomain = d.code"
          >
            <div class="domain-name">{{ d.cn_name }}</div>
            <div class="domain-code">{{ d.code }}</div>
          </div>
        </div>
      </div>

      <!-- Right: tabs + content -->
      <div class="right-panel">
        <!-- Tab nav -->
        <div class="tab-bar">
          <div
            v-for="tab in tabs"
            :key="tab.name"
            :class="['tab-item', { active: activeTab === tab.name }]"
            @click="activeTab = tab.name"
          >
            <el-icon :size="14"><component :is="tab.icon" /></el-icon>
            <span>{{ tab.label }}</span>
            <el-tag
              v-if="tab.count !== undefined && tab.count > 0"
              size="small"
              type="info"
              effect="plain"
              class="tab-count"
            >{{ tab.count }}</el-tag>
          </div>
        </div>

        <!-- Content -->
        <div class="content-area">

          <!-- 1. 表字典 -->
          <div v-if="activeTab === 'tables'" class="tab-content">
            <div class="toolbar">
              <el-input
                v-model="tableSearch"
                placeholder="搜索表名..."
                clearable
                size="default"
                style="width: 320px"
                :prefix-icon="Search"
              />
              <el-radio-group v-model="tableLayerFilter" size="small">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="dim">dim</el-radio-button>
                <el-radio-button label="dwd">dwd</el-radio-button>
                <el-radio-button label="dws">dws</el-radio-button>
                <el-radio-button label="dm">dm</el-radio-button>
                <el-radio-button label="other">其他</el-radio-button>
              </el-radio-group>
            </div>
            <div class="card-grid" v-loading="loading">
              <div
                v-for="t in filteredTables"
                :key="t.id"
                class="asset-card"
                @click="openTableDetail(t)"
              >
                <div class="card-header">
                  <span class="table-name">{{ t.table_name }}</span>
                  <el-tag size="small" :type="layerTagType(t.layer)">{{ t.layer || 'other' }}</el-tag>
                </div>
                <div class="card-body">
                  <p class="table-comment">{{ t.table_comment || '暂无注释' }}</p>
                  <div class="table-stats">
                    <span class="stat-item">
                      <el-icon :size="12"><Tickets /></el-icon>
                      {{ t.field_count || 0 }} 字段
                    </span>
                    <span class="stat-item">
                      <el-icon :size="12"><Histogram /></el-icon>
                      {{ t.metric_count || 0 }} 指标
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <el-empty v-if="!loading && filteredTables.length === 0" description="暂无表" />

            <!-- Table Detail Drawer -->
            <el-drawer
              v-model="tableDetailVisible"
              :title="selectedTable?.table_name"
              size="600px"
            >
              <div v-if="selectedTable" class="detail-body">
                <el-descriptions :column="1" border>
                  <el-descriptions-item label="表名">{{ selectedTable.table_name }}</el-descriptions-item>
                  <el-descriptions-item label="注释">{{ selectedTable.table_comment || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="分层">{{ selectedTable.layer || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="字段数">{{ selectedTable.field_count || 0 }}</el-descriptions-item>
                  <el-descriptions-item label="指标数">{{ selectedTable.metric_count || 0 }}</el-descriptions-item>
                </el-descriptions>
                <h4 class="section-title">字段列表</h4>
                <el-table :data="selectedTableFields" stripe size="small">
                  <el-table-column prop="field_name" label="字段名" width="180" />
                  <el-table-column prop="field_type" label="类型" width="120" />
                  <el-table-column prop="field_comment" label="注释" />
                  <el-table-column prop="category" label="分类" width="100" />
                </el-table>
              </div>
            </el-drawer>
          </div>

          <!-- 2. 字段字典 -->
          <div v-if="activeTab === 'fields'" class="tab-content">
            <div class="toolbar">
              <el-input
                v-model="fieldSearch"
                placeholder="搜索字段名..."
                clearable
                size="default"
                style="width: 320px"
                :prefix-icon="Search"
              />
            </div>
            <el-table :data="filteredFields" stripe v-loading="loading" class="field-table">
              <el-table-column prop="field_name" label="字段名" width="180" sortable>
                <template #default="{ row }">
                  <span class="field-name">{{ row.field_name }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="field_type" label="类型" width="120" />
              <el-table-column prop="field_comment" label="注释" min-width="200" />
              <el-table-column prop="category" label="分类" width="120">
                <template #default="{ row }">
                  <el-tag size="small" :type="categoryTagType(row.category)">
                    {{ row.category || 'other' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="is_partition" label="分区" width="80">
                <template #default="{ row }">
                  <el-tag v-if="row.is_partition" size="small" type="warning">是</el-tag>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="is_primary_key" label="主键" width="80">
                <template #default="{ row }">
                  <el-tag v-if="row.is_primary_key" size="small" type="success">是</el-tag>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="!loading && filteredFields.length === 0" description="暂无字段" />
          </div>

          <!-- 3. 核心指标 -->
          <div v-if="activeTab === 'metrics'" class="tab-content">
            <div class="toolbar">
              <el-input
                v-model="metricSearch"
                placeholder="搜索指标..."
                clearable
                size="default"
                style="width: 320px"
                :prefix-icon="Search"
              />
              <el-radio-group v-model="metricStatusFilter" size="small">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="candidate">候选</el-radio-button>
                <el-radio-button label="confirmed">已确认</el-radio-button>
                <el-radio-button label="deprecated">已废弃</el-radio-button>
              </el-radio-group>
            </div>
            <div class="card-grid" v-loading="loading">
              <div
                v-for="m in filteredMetrics"
                :key="m.id"
                class="asset-card metric-card"
                @click="openMetricDetail(m)"
              >
                <div class="card-header">
                  <span class="metric-name">{{ m.cn_name }}</span>
                  <el-tag size="small" :type="metricStatusType(m.status)">{{ m.status || 'candidate' }}</el-tag>
                </div>
                <div class="card-body">
                  <p class="metric-number" v-if="m.metric_number">#{{ m.metric_number }}</p>
                  <p class="metric-calc" v-if="m.calculation">{{ m.calculation }}</p>
                  <div class="metric-meta">
                    <span v-if="m.grain" class="meta-tag">粒度: {{ m.grain }}</span>
                    <span v-if="m.unit" class="meta-tag">单位: {{ m.unit }}</span>
                  </div>
                </div>
              </div>
            </div>
            <el-empty v-if="!loading && filteredMetrics.length === 0" description="暂无指标" />

            <!-- Metric Detail Drawer -->
            <el-drawer
              v-model="metricDetailVisible"
              :title="selectedMetric?.cn_name"
              size="600px"
            >
              <div v-if="selectedMetric" class="detail-body">
                <el-descriptions :column="1" border>
                  <el-descriptions-item label="指标编号">{{ selectedMetric.metric_number || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="中文名">{{ selectedMetric.cn_name }}</el-descriptions-item>
                  <el-descriptions-item label="英文名">{{ selectedMetric.en_name || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="别名">{{ selectedMetric.alias || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="业务定义">
                    <pre class="pre-text">{{ selectedMetric.business_definition || '-' }}</pre>
                  </el-descriptions-item>
                  <el-descriptions-item label="计算公式">
                    <pre class="pre-text">{{ selectedMetric.calculation || '-' }}</pre>
                  </el-descriptions-item>
                  <el-descriptions-item label="SQL 模板">
                    <pre class="sql-highlight">{{ selectedMetric.sql_template || '-' }}</pre>
                  </el-descriptions-item>
                  <el-descriptions-item label="粒度">{{ selectedMetric.grain || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="单位">{{ selectedMetric.unit || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="状态">
                    <el-tag :type="metricStatusType(selectedMetric.status)">
                      {{ selectedMetric.status || 'candidate' }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
              </div>
            </el-drawer>
          </div>

          <!-- 4. 注意事项 (Business Rules) -->
          <div v-if="activeTab === 'rules'" class="tab-content">
            <div class="toolbar">
              <el-input
                v-model="ruleSearch"
                placeholder="搜索规则..."
                clearable
                size="default"
                style="width: 320px"
                :prefix-icon="Search"
              />
              <el-radio-group v-model="ruleSeverityFilter" size="small">
                <el-radio-button label="">全部</el-radio-button>
                <el-radio-button label="info">提示</el-radio-button>
                <el-radio-button label="warning">警告</el-radio-button>
                <el-radio-button label="critical">严重</el-radio-button>
              </el-radio-group>
            </div>
            <div class="rule-list" v-loading="loading">
              <div
                v-for="r in filteredRules"
                :key="r.id"
                class="rule-card"
              >
                <div class="rule-header">
                  <el-tag size="small" :type="severityType(r.severity)">{{ severityLabel(r.severity) }}</el-tag>
                  <span class="rule-title">{{ r.title }}</span>
                </div>
                <div class="rule-content">{{ r.content }}</div>
                <div class="rule-example" v-if="r.example">
                  <div class="example-label">✓ 正确示例</div>
                  <pre>{{ r.example }}</pre>
                </div>
                <div class="rule-counter" v-if="r.counter_example">
                  <div class="example-label error">✗ 错误示例</div>
                  <pre>{{ r.counter_example }}</pre>
                </div>
              </div>
            </div>
            <el-empty v-if="!loading && filteredRules.length === 0" description="暂无规则" />
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, watch, markRaw } from 'vue'
import {
  Search, Tickets, Histogram, Grid, Warning,
  DataAnalysis, Collection
} from '@element-plus/icons-vue'
import { request } from '@/utils/request'

// ── State ──
const loading = ref(true)
const domains = ref<any[]>([
  { code: 'card', cn_name: '卡域' },
  { code: 'corp_deposit', cn_name: '对公存款' },
  { code: 'corp_fx', cn_name: '对公外汇' },
])
const selectedDomain = ref('card')
const activeTab = ref('tables')

// Search
const tableSearch = ref('')
const fieldSearch = ref('')
const metricSearch = ref('')
const ruleSearch = ref('')

// Filters
const tableLayerFilter = ref('')
const metricStatusFilter = ref('')
const ruleSeverityFilter = ref('')

// Data
const tables = ref<any[]>([])
const fields = ref<any[]>([])
const metrics = ref<any[]>([])
const rules = ref<any[]>([])

// Detail
const tableDetailVisible = ref(false)
const selectedTable = ref<any>(null)
const selectedTableFields = ref<any[]>([])
const metricDetailVisible = ref(false)
const selectedMetric = ref<any>(null)

// ── Tabs ──
const tabIcons: Record<string, any> = {
  tables: markRaw(Tickets),
  fields: markRaw(Collection),
  metrics: markRaw(DataAnalysis),
  rules: markRaw(Warning),
}

const tabs = computed(() => [
  { name: 'tables', label: '表字典', icon: tabIcons.tables, count: tables.value.length },
  { name: 'fields', label: '字段字典', icon: tabIcons.fields, count: fields.value.length },
  { name: 'metrics', label: '核心指标', icon: tabIcons.metrics, count: metrics.value.length },
  { name: 'rules', label: '注意事项', icon: tabIcons.rules, count: rules.value.length },
])

// ── Computed ──
const filteredTables = computed(() => {
  let result = tables.value
  if (tableLayerFilter.value) {
    result = result.filter((t: any) => (t.layer || 'other') === tableLayerFilter.value)
  }
  if (tableSearch.value) {
    const q = tableSearch.value.toLowerCase()
    result = result.filter((t: any) =>
      t.table_name?.toLowerCase().includes(q) ||
      t.table_comment?.toLowerCase().includes(q)
    )
  }
  return result
})

const filteredFields = computed(() => {
  let result = fields.value
  if (fieldSearch.value) {
    const q = fieldSearch.value.toLowerCase()
    result = result.filter((f: any) =>
      f.field_name?.toLowerCase().includes(q) ||
      f.field_comment?.toLowerCase().includes(q)
    )
  }
  return result
})

const filteredMetrics = computed(() => {
  let result = metrics.value
  if (metricStatusFilter.value) {
    result = result.filter((m: any) => (m.status || 'candidate') === metricStatusFilter.value)
  }
  if (metricSearch.value) {
    const q = metricSearch.value.toLowerCase()
    result = result.filter((m: any) =>
      m.cn_name?.toLowerCase().includes(q) ||
      m.metric_number?.toLowerCase().includes(q)
    )
  }
  return result
})

const filteredRules = computed(() => {
  let result = rules.value
  if (ruleSeverityFilter.value) {
    result = result.filter((r: any) => (r.severity || 'warning') === ruleSeverityFilter.value)
  }
  if (ruleSearch.value) {
    const q = ruleSearch.value.toLowerCase()
    result = result.filter((r: any) =>
      r.title?.toLowerCase().includes(q) ||
      r.content?.toLowerCase().includes(q)
    )
  }
  return result
})

// ── Helpers ──
const layerTagType = (layer: string) => {
  const map: Record<string, string> = {
    dim: '', dwd: 'info', dws: 'success', dm: 'warning', odm: 'danger',
  }
  return map[layer] || 'info'
}

const categoryTagType = (cat: string) => {
  const map: Record<string, string> = {
    dimension: '', metric: 'success', filter: 'warning', partition: 'danger',
  }
  return map[cat] || 'info'
}

const metricStatusType = (status: string) => {
  const map: Record<string, string> = {
    candidate: 'info', confirmed: 'success', deprecated: 'danger',
  }
  return map[status] || 'info'
}

const severityType = (sev: string) => {
  const map: Record<string, string> = {
    info: 'info', warning: 'warning', critical: 'danger',
  }
  return map[sev] || 'warning'
}

const severityLabel = (sev: string) => {
  const map: Record<string, string> = {
    info: '提示', warning: '警告', critical: '严重',
  }
  return map[sev] || '警告'
}

// ── Detail ──
const openTableDetail = async (t: any) => {
  selectedTable.value = t
  tableDetailVisible.value = true
  // Load fields for this table
  try {
    const res = await request.get(`/ai2bi/assets/tables/${t.id}/fields`)
    selectedTableFields.value = res || []
  } catch (e) {
    selectedTableFields.value = []
  }
}

const openMetricDetail = (m: any) => {
  selectedMetric.value = m
  metricDetailVisible.value = true
}

// ── Load ──
const loadAssets = async () => {
  loading.value = true
  try {
    const domain = selectedDomain.value
    // Load all in parallel
    const [tablesRes, fieldsRes, metricsRes, rulesRes] = await Promise.all([
      request.get(`/ai2bi/assets/tables?domain=${domain}`).catch(() => ({ items: [] })),
      request.get(`/ai2bi/assets/fields?domain=${domain}`).catch(() => ({ items: [] })),
      request.get(`/ai2bi/assets/metrics?domain=${domain}`).catch(() => ({ items: [] })),
      request.get(`/ai2bi/assets/rules?domain=${domain}`).catch(() => ({ items: [] })),
    ])
    tables.value = tablesRes?.items || []
    fields.value = fieldsRes?.items || []
    metrics.value = metricsRes?.items || []
    rules.value = rulesRes?.items || []
  } catch (e) {
    console.error('Failed to load assets', e)
  } finally {
    loading.value = false
  }
}

watch(selectedDomain, loadAssets, { immediate: true })
onMounted(() => loadAssets())
</script>

<style scoped>
.ai2bi-assets {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f5f7fa;
}

/* Header */
.page-header {
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #e8e9eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.header-left { display: flex; flex-direction: column; gap: 2px; }
.page-title { font-size: 18px; font-weight: 600; color: #1f2329; margin: 0; }
.page-subtitle { font-size: 13px; color: #8f959e; margin: 0; }

/* Layout */
.layout-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* Domain panel */
.domain-panel {
  width: 200px;
  border-right: 1px solid #e8e9eb;
  background: #fff;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}
.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid #e8e9eb;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2329;
}
.domain-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.domain-item {
  padding: 12px 14px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.15s;
  margin-bottom: 4px;
}
.domain-item:hover { background: #f5f7fa; }
.domain-item.active {
  background: #e6f7ef;
}
.domain-name {
  font-size: 14px;
  font-weight: 500;
  color: #1f2329;
  margin-bottom: 2px;
}
.domain-code {
  font-size: 12px;
  color: #8f959e;
  font-family: 'SF Mono', monospace;
}
.domain-item.active .domain-name { color: #1cba90; }
.domain-item.active .domain-code { color: #6ccba8; }

/* Right panel */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Tab bar */
.tab-bar {
  display: flex;
  gap: 4px;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e8e9eb;
  flex-shrink: 0;
}
.tab-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  color: #606266;
  border-radius: 6px;
  transition: all 0.15s;
}
.tab-item:hover { background: #f5f7fa; color: #1f2329; }
.tab-item.active {
  background: #e6f7ef;
  color: #1cba90;
  font-weight: 500;
}
.tab-count { margin-left: 4px; }

/* Content */
.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}
.tab-content { max-width: 1200px; }

/* Toolbar */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

/* Card grid */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.asset-card {
  background: #fff;
  border: 1px solid #e8e9eb;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.15s;
}
.asset-card:hover {
  border-color: #1cba90;
  box-shadow: 0 2px 8px rgba(28, 186, 144, 0.08);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.table-name {
  font-size: 14px;
  font-weight: 500;
  color: #1f2329;
  font-family: 'SF Mono', monospace;
  word-break: break-all;
}
.metric-name {
  font-size: 14px;
  font-weight: 500;
  color: #1f2329;
}
.table-comment, .metric-calc {
  font-size: 13px;
  color: #606266;
  margin: 0 0 8px;
  line-height: 1.5;
}
.metric-number {
  font-size: 12px;
  color: #909399;
  margin: 0 0 4px;
  font-family: 'SF Mono', monospace;
}
.table-stats {
  display: flex;
  gap: 12px;
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #8f959e;
}
.metric-meta {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.meta-tag {
  font-size: 12px;
  color: #8f959e;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}

/* Field table */
.field-table {
  border: 1px solid #e8e9eb;
  border-radius: 8px;
  overflow: hidden;
}
.field-name {
  font-family: 'SF Mono', monospace;
  font-weight: 500;
  color: #1f2329;
}
.text-muted { color: #c0c4cc; }

/* Rule list */
.rule-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rule-card {
  background: #fff;
  border: 1px solid #e8e9eb;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.15s;
}
.rule-card:hover {
  border-color: #e6a23c;
  box-shadow: 0 2px 8px rgba(230, 162, 60, 0.08);
}
.rule-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.rule-title {
  font-size: 14px;
  font-weight: 500;
  color: #1f2329;
}
.rule-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 12px;
}
.rule-example, .rule-counter {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 8px;
}
.rule-counter {
  background: #fff2f0;
  border-color: #ffccc7;
}
.example-label {
  font-size: 12px;
  font-weight: 500;
  color: #52c41a;
  margin-bottom: 4px;
}
.example-label.error { color: #ff4d4f; }
.rule-example pre, .rule-counter pre {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'SF Mono', monospace;
  color: #333;
}

/* Detail body */
.detail-body { padding: 16px; }
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2329;
  margin: 20px 0 12px;
}
.pre-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
  color: #333;
}
.sql-highlight {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'SF Mono', 'Consolas', monospace;
  margin: 0;
}
</style>
