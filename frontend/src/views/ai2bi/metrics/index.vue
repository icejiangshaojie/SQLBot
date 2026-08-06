<template>
  <div class="ai2bi-metrics">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">指标管理</h1>
        <p class="page-subtitle">管理 AI2BI 业务指标定义，包括业务口径、计算公式和 SQL 模板</p>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索指标名称或定义..."
          clearable
          size="default"
          style="width: 280px"
        />
        <el-button type="primary" :icon="Plus" @click="showDomainDialog = true">
          新建域
        </el-button>
      </div>
    </div>

    <div class="layout-body">
      <!-- Left: domain list -->
      <div class="domain-panel">
        <div class="panel-header">
          <span class="panel-title">业务域</span>
        </div>
        <div class="domain-list" v-loading="loading">
          <div
            v-for="d in domains"
            :key="d.id"
            :class="['domain-item', { active: selectedDomain === d.id }]"
            @click="selectDomain(d.id)"
          >
            <div class="domain-name">{{ d.cn_name }}</div>
            <div class="domain-code">{{ d.code }}</div>
          </div>
          <el-empty v-if="!loading && domains.length === 0" description="暂无业务域" />
        </div>
      </div>

      <!-- Right: metric list + detail -->
      <div class="right-panel">
        <div class="panel-toolbar">
          <el-button size="small" type="primary" :icon="Plus" @click="showMetricDialog = true" :disabled="!selectedDomain">
            新建指标
          </el-button>
          <el-tag v-if="selectedDomainName" size="small" type="info" effect="light">
            {{ selectedDomainName }}
          </el-tag>
          <span v-else class="no-domain-hint">请先选择业务域</span>
        </div>

        <div class="metric-grid" v-loading="loading">
          <div v-if="filteredMetrics.length > 0" class="metric-cards">
            <div
              v-for="m in filteredMetrics"
              :key="m.id"
              :class="['metric-item', { active: currentMetric?.id === m.id }]"
              @click="selectMetric(m)"
            >
              <div class="metric-header">
                <el-tag size="small" :type="tierColor(m.tier)" effect="light">{{ m.tier }}</el-tag>
                <el-tag size="small" :type="statusColor(m.status)" effect="light">{{ statusLabel(m.status) }}</el-tag>
                <span class="metric-name">{{ m.cn_name }}</span>
              </div>
              <p class="metric-def">{{ m.business_definition || '无定义' }}</p>
              <div v-if="m.calculation" class="metric-formula">
                <el-icon><EditPen /></el-icon>
                <code>{{ m.calculation }}</code>
              </div>
            </div>
          </div>
          <el-empty v-else-if="!loading" description="暂无指标" />
        </div>
      </div>
    </div>

    <!-- Detail drawer -->
    <el-drawer
      v-model="detailVisible"
      :title="currentMetric?.cn_name || '指标详情'"
      size="55%"
    >
      <div v-if="currentMetric" class="metric-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="编号">{{ currentMetric.metric_number || '-' }}</el-descriptions-item>
          <el-descriptions-item label="层级">
            <el-tag :type="tierColor(currentMetric.tier)" effect="light" size="small">
              {{ currentMetric.tier }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusColor(currentMetric.status)" effect="light" size="small">
              {{ statusLabel(currentMetric.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="版本">v{{ currentMetric.version }}</el-descriptions-item>
          <el-descriptions-item label="业务定义">{{ currentMetric.business_definition || '-' }}</el-descriptions-item>
          <el-descriptions-item label="计算公式">
            <code class="calc-formula">{{ currentMetric.calculation || '-' }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="SQL模板">
            <pre class="sql-template">{{ currentMetric.sql_template || '-' }}</pre>
          </el-descriptions-item>
          <el-descriptions-item label="必选过滤">{{ currentMetric.mandatory_rules || '-' }}</el-descriptions-item>
          <el-descriptions-item label="粒度">{{ currentMetric.grain || '-' }}</el-descriptions-item>
          <el-descriptions-item label="依赖表">
            <div class="table-tags">
              <el-tag
                v-for="t in parseTables(currentMetric.source_tables)"
                :key="t"
                size="small"
                type="info"
                effect="light"
              >
                {{ t }}
              </el-tag>
            </div>
          </el-descriptions-item>
        </el-descriptions>

        <div class="detail-actions">
          <el-button
            v-if="currentMetric.status === 'candidate'"
            type="success"
            :icon="Check"
            @click="confirmMetric"
          >
            确认指标
          </el-button>
          <el-button type="danger" :icon="Delete" @click="deleteMetric">删除</el-button>
        </div>
      </div>
    </el-drawer>

    <!-- New domain dialog -->
    <el-dialog v-model="showDomainDialog" title="新建业务域" width="420px">
      <el-form label-width="80px" :model="newDomain">
        <el-form-item label="编码">
          <el-input v-model="newDomain.code" placeholder="如 card" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="newDomain.cn_name" placeholder="如 卡域" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newDomain.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDomainDialog = false">取消</el-button>
        <el-button type="primary" @click="createDomain">创建</el-button>
      </template>
    </el-dialog>

    <!-- New metric dialog -->
    <el-dialog v-model="showMetricDialog" title="新建指标" width="560px">
      <el-form label-width="100px" :model="newMetric">
        <el-form-item label="中文名">
          <el-input v-model="newMetric.cn_name" />
        </el-form-item>
        <el-form-item label="英文名">
          <el-input v-model="newMetric.en_name" />
        </el-form-item>
        <el-form-item label="层级">
          <el-select v-model="newMetric.tier" style="width: 100%">
            <el-option label="L1" value="L1" />
            <el-option label="L2" value="L2" />
            <el-option label="L3" value="L3" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务定义">
          <el-input v-model="newMetric.business_definition" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="计算公式">
          <el-input v-model="newMetric.calculation" />
        </el-form-item>
        <el-form-item label="SQL模板">
          <el-input v-model="newMetric.sql_template" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="必选过滤">
          <el-input v-model="newMetric.mandatory_rules" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMetricDialog = false">取消</el-button>
        <el-button type="primary" @click="createMetric">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import { Plus, EditPen, Check, Delete } from '@element-plus/icons-vue'
import { request } from '@/utils/request'
import { ElMessage } from 'element-plus-secondary'

const loading = ref(false)
const domains = ref<any[]>([])
const metrics = ref<any[]>([])
const selectedDomain = ref<number | null>(null)
const currentMetric = ref<any>(null)
const searchQuery = ref('')
const detailVisible = ref(false)
const showDomainDialog = ref(false)
const showMetricDialog = ref(false)
const newDomain = ref({ code: '', cn_name: '', description: '' })
const newMetric = ref({
  cn_name: '', en_name: '', tier: 'L2',
  business_definition: '', calculation: '', sql_template: '', mandatory_rules: ''
})

const selectedDomainName = computed(() => {
  const d = domains.value.find(d => d.id === selectedDomain.value)
  return d?.cn_name || ''
})

const filteredMetrics = computed(() => {
  let list = metrics.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter((m: any) =>
      m.cn_name?.toLowerCase().includes(q) ||
      m.business_definition?.toLowerCase().includes(q)
    )
  }
  return list
})

const tierColor = (t: string) => ({ L1: 'danger', L2: 'warning', L3: 'info' }[t] || 'info')
const statusColor = (s: string) => ({ confirmed: 'success', candidate: 'warning', rejected: 'danger', deleted: 'info' }[s] || 'info')
const statusLabel = (s: string) => ({ confirmed: '已确认', candidate: '候选', rejected: '已拒绝', deleted: '已删除' }[s] || s)
const parseTables = (s: string) => s ? s.split(',').map(t => t.trim()).filter(Boolean) : []

const loadDomains = async () => {
  try {
    const res: any = await request.get('/ai2bi/metrics/domains')
    domains.value = res || []
    if (domains.value.length && !selectedDomain.value) {
      selectDomain(domains.value[0].id)
    }
  } catch { /* ignore */ }
}

const selectDomain = async (id: number) => {
  selectedDomain.value = id
  currentMetric.value = null
  detailVisible.value = false
  loading.value = true
  try {
    const res: any = await request.get(`/ai2bi/metrics/list/${id}`)
    metrics.value = res || []
  } finally {
    loading.value = false
  }
}

const selectMetric = (m: any) => {
  currentMetric.value = m
  detailVisible.value = true
}

const createDomain = async () => {
  await request.post('/ai2bi/metrics/domains', newDomain.value)
  ElMessage.success('业务域已创建')
  showDomainDialog.value = false
  newDomain.value = { code: '', cn_name: '', description: '' }
  await loadDomains()
}

const createMetric = async () => {
  if (!selectedDomain.value) return
  await request.post('/ai2bi/metrics/create', { ...newMetric.value, domain_id: selectedDomain.value })
  ElMessage.success('指标已创建')
  showMetricDialog.value = false
  newMetric.value = { cn_name: '', en_name: '', tier: 'L2', business_definition: '', calculation: '', sql_template: '', mandatory_rules: '' }
  await selectDomain(selectedDomain.value)
}

const confirmMetric = async () => {
  if (!currentMetric.value) return
  await request.post(`/ai2bi/metrics/confirm/${currentMetric.value.id}`)
  ElMessage.success('指标已确认')
  await selectDomain(selectedDomain.value!)
}

const deleteMetric = async () => {
  if (!currentMetric.value) return
  if (!confirm('确认删除该指标?')) return
  await request.delete(`/ai2bi/metrics/delete/${currentMetric.value.id}`)
  ElMessage.success('指标已删除')
  currentMetric.value = null
  detailVisible.value = false
  await selectDomain(selectedDomain.value!)
}

onMounted(() => loadDomains())
</script>

<style scoped>
.ai2bi-metrics {
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
.header-right { display: flex; align-items: center; gap: 12px; }

/* Layout */
.layout-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Domain panel */
.domain-panel {
  width: 240px;
  border-right: 1px solid #e8e9eb;
  display: flex;
  flex-direction: column;
  background: #fff;
  flex-shrink: 0;
}
.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid #e8e9eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-title { font-size: 14px; font-weight: 600; color: #1f2329; }
.domain-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.domain-item {
  padding: 12px 14px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
  margin-bottom: 4px;
}
.domain-item:hover { background: #f5f7fa; }
.domain-item.active { background: #e6f7ef; }
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

/* Right panel */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.panel-toolbar {
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-bottom: 1px solid #e8e9eb;
  flex-shrink: 0;
}
.no-domain-hint { font-size: 13px; color: #c0c4cc; }

/* Metric grid */
.metric-grid {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}
.metric-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}
.metric-item {
  background: #fff;
  border: 1px solid #e8e9eb;
  border-radius: 8px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.metric-item:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  border-color: #1cba90;
}
.metric-item.active {
  border-color: #1cba90;
  background: #fafcfb;
}
.metric-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.metric-name {
  font-weight: 500;
  font-size: 14px;
  color: #1f2329;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.metric-def {
  font-size: 12px;
  color: #8f959e;
  margin: 4px 0;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.metric-formula {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding: 6px 10px;
  background: #fafbfc;
  border: 1px solid #e8e9eb;
  border-radius: 6px;
  font-size: 12px;
}
.metric-formula .el-icon { color: #e6a23c; font-size: 12px; }
.metric-formula code {
  font-family: 'SF Mono', 'Consolas', monospace;
  color: #e6a23c;
  font-size: 12px;
}

/* Detail */
.metric-detail { padding: 0; }
.calc-formula {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 13px;
  color: #1f2329;
  background: #f5f7fa;
  padding: 4px 8px;
  border-radius: 4px;
}
.sql-template {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #d4d4d4;
  background: #1e1e1e;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}
.table-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.detail-actions {
  margin-top: 24px;
  display: flex;
  gap: 8px;
}
</style>
