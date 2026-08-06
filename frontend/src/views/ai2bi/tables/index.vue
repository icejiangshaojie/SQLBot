<template>
  <div class="ai2bi-tables">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">表管理</h1>
        <p class="page-subtitle">管理 Agent 可访问的数据表白名单，包括字段同步和分层管理</p>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索表名..."
          clearable
          size="default"
          style="width: 280px"
        />
      </div>
    </div>

    <!-- Stats bar -->
    <div class="stats-row">
      <div class="stat-item">
        <div class="stat-icon"><el-icon :size="22"><Grid /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ tables.length }}</div>
          <div class="stat-label">白名单表</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon fields"><el-icon :size="22"><List /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ totalFields }}</div>
          <div class="stat-label">总字段数</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon synced"><el-icon :size="22"><CircleCheck /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ syncedCount }}</div>
          <div class="stat-label">已同步字段</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon unsynced"><el-icon :size="22"><Warning /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ unsyncedCount }}</div>
          <div class="stat-label">未同步</div>
        </div>
      </div>
    </div>

    <!-- Layer filter -->
    <div class="filter-bar">
      <div class="filter-label">分层筛选：</div>
      <el-radio-group v-model="layerFilter" size="default">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button v-for="layer in layers" :key="layer" :label="layer">
          {{ layer }}
        </el-radio-button>
      </el-radio-group>
      <div class="filter-right">
        <el-tag size="small" type="info">数据源: zabank_dw (ODPS)</el-tag>
      </div>
    </div>

    <!-- Table list -->
    <div class="table-list-container" v-loading="loading">
      <div v-if="filteredTables.length > 0" class="table-grid">
        <div
          v-for="t in filteredTables"
          :key="t.id"
          class="table-item"
          @click="selectTable(t)"
        >
          <div class="table-item-header">
            <el-tag size="small" :type="layerTagType(t.layer)" effect="light">{{ t.layer }}</el-tag>
            <span class="table-name">{{ t.table_name }}</span>
            <el-tag
              size="small"
              :type="t.fields > 0 ? 'success' : 'warning'"
              effect="light"
            >
              {{ t.fields > 0 ? `${t.fields} 字段` : '未同步' }}
            </el-tag>
          </div>
          <div class="table-item-body">
            <span class="table-datasource">zabank_dw</span>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无表" />
    </div>

    <!-- Detail drawer -->
    <el-drawer
      v-model="drawerVisible"
      :title="currentTable?.table_name || '表详情'"
      size="55%"
    >
      <div v-if="currentTable" class="table-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="表名">
            <code class="table-name-code">{{ currentTable.table_name }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="分层">
            <el-tag :type="layerTagType(currentTable.layer)" effect="light" size="small">
              {{ currentTable.layer }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="数据源">ODPS zabank_dw</el-descriptions-item>
          <el-descriptions-item label="字段数">{{ currentTable.fields || 0 }}</el-descriptions-item>
        </el-descriptions>

        <div class="field-section">
          <div class="section-header">
            <h4>
              <el-icon><List /></el-icon>
              字段列表
            </h4>
            <el-tag size="small" type="info">{{ fields.length }} 个字段</el-tag>
          </div>
          <el-table
            :data="fields"
            stripe
            size="small"
            max-height="500"
            v-loading="fieldsLoading"
            class="field-table"
          >
            <el-table-column prop="field_name" label="字段名" min-width="220">
              <template #default="{ row }">
                <code class="field-name">{{ row.field_name }}</code>
              </template>
            </el-table-column>
            <el-table-column prop="field_type" label="类型" width="120">
              <template #default="{ row }">
                <el-tag size="small" type="info" effect="plain">{{ row.field_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="field_comment" label="注释" min-width="300">
              <template #default="{ row }">
                <span :class="row.field_comment ? '' : 'no-comment'">
                  {{ row.field_comment || '无注释' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import { Grid, List, CircleCheck, Warning } from '@element-plus/icons-vue'
import { request } from '@/utils/request'

const loading = ref(false)
const fieldsLoading = ref(false)
const tables = ref<any[]>([])
const currentTable = ref<any>(null)
const fields = ref<any[]>([])
const drawerVisible = ref(false)
const searchQuery = ref('')
const layerFilter = ref('')

const totalFields = computed(() =>
  tables.value.reduce((sum: number, t: any) => sum + (t.fields || 0), 0)
)
const syncedCount = computed(() => tables.value.filter(t => t.fields > 0).length)
const unsyncedCount = computed(() => tables.value.filter(t => !t.fields || t.fields === 0).length)
const layers = computed(() => {
  const set = new Set(tables.value.map(t => t.layer).filter(Boolean))
  return Array.from(set).sort()
})

const filteredTables = computed(() => {
  let list = tables.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(t => t.table_name?.toLowerCase().includes(q))
  }
  if (layerFilter.value) {
    list = list.filter(t => t.layer === layerFilter.value)
  }
  return list
})

const layerTagType = (layer: string) => {
  const map: Record<string, string> = {
    dim: 'success', dwd: 'warning', dws: 'primary',
    dm: 'danger', odm: 'info', ads: 'info'
  }
  return map[layer?.toLowerCase()] || 'info'
}

const loadTables = async () => {
  loading.value = true
  try {
    tables.value = await request.get('/ai2bi/tables/list') || []
  } catch (e) {
    console.error('Failed to load tables', e)
  } finally {
    loading.value = false
  }
}

const selectTable = async (t: any) => {
  currentTable.value = t
  fields.value = []
  drawerVisible.value = true
  if (t.id) {
    fieldsLoading.value = true
    try {
      fields.value = await request.get(`/ai2bi/tables/${t.id}/fields`) || []
    } catch {
      fields.value = []
    } finally {
      fieldsLoading.value = false
    }
  }
}

onMounted(() => loadTables())
</script>

<style scoped>
.ai2bi-tables {
  height: 100%;
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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

/* Stats */
.stats-row {
  display: flex;
  gap: 16px;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #e8e9eb;
  flex-shrink: 0;
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #fafbfc;
  border: 1px solid #e8e9eb;
  border-radius: 8px;
  flex: 1;
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  color: #606266;
}
.stat-icon.fields { background: #e6f0ff; color: #409eff; }
.stat-icon.synced { background: #e6f7ef; color: #1cba90; }
.stat-icon.unsynced { background: #fff0f0; color: #f56c6c; }
.stat-info { display: flex; flex-direction: column; }
.stat-num { font-size: 22px; font-weight: 700; color: #1f2329; line-height: 1; }
.stat-label { font-size: 12px; color: #8f959e; margin-top: 4px; }

/* Filter */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #e8e9eb;
  flex-shrink: 0;
}
.filter-label { font-size: 13px; color: #606266; font-weight: 500; }
.filter-right { margin-left: auto; }

/* Table list */
.table-list-container {
  flex: 1;
  padding: 16px 24px;
  overflow-y: auto;
}
.table-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}
.table-item {
  background: #fff;
  border: 1px solid #e8e9eb;
  border-radius: 8px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.table-item:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  border-color: #1cba90;
  transform: translateY(-2px);
}
.table-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.table-name {
  font-weight: 500;
  font-size: 13px;
  font-family: 'SF Mono', 'Consolas', monospace;
  color: #1f2329;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.table-item-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.table-datasource {
  font-size: 11px;
  color: #8f959e;
}

/* Detail */
.table-detail { padding: 0; }
.table-name-code {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 13px;
  color: #1f2329;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}
.field-section { margin-top: 20px; }
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.section-header h4 {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
  margin: 0;
}
.section-header h4 .el-icon { color: #1cba90; }
.field-table {
  border: 1px solid #e8e9eb;
  border-radius: 8px;
  overflow: hidden;
}
.field-name {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 12px;
  color: #1f2329;
}
.no-comment { color: #c0c4cc; font-style: italic; }
</style>
