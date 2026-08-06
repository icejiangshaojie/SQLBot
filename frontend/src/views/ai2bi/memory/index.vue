<template>
  <div class="ai2bi-memory">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">我的记忆</h1>
        <p class="page-subtitle">管理 AI 助手的记忆，包括用户偏好和会话摘要</p>
      </div>
      <div class="header-right">
        <el-input
          v-model="newMemory.content"
          placeholder="添加记忆..."
          size="default"
          style="width: 300px"
          @keyup.enter="createMemory"
        />
        <el-button type="primary" :icon="Plus" @click="createMemory">
          添加
        </el-button>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-row">
      <div class="stat-item">
        <div class="stat-icon"><el-icon :size="22"><Collection /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ memories.length }}</div>
          <div class="stat-label">记忆条数</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon pinned"><el-icon :size="22"><Star /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ pinnedCount }}</div>
          <div class="stat-label">已固定</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon"><el-icon :size="22"><Memo /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ summaries.length }}</div>
          <div class="stat-label">会话摘要</div>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tab-bar">
      <div
        v-for="tab in tabs"
        :key="tab.name"
        :class="['tab-item', { active: activeTab === tab.name }]"
        @click="activeTab = tab.name"
      >
        <el-icon :size="14"><component :is="tab.icon" /></el-icon>
        <span>{{ tab.label }}</span>
        <el-tag v-if="tab.count !== undefined" size="small" type="info" effect="plain" class="tab-count">{{ tab.count }}</el-tag>
      </div>
    </div>

    <!-- Content -->
    <div class="content-area">
      <!-- Memories tab -->
      <div v-if="activeTab === 'memories'" class="tab-content" v-loading="loading">
        <div v-if="memories.length > 0" class="memory-list">
          <div v-for="m in memories" :key="m.id" :class="['memory-item', { pinned: m.pinned }]">
            <div class="memory-main">
              <div class="memory-header">
                <el-tag size="small" type="info" effect="light">{{ m.category || '通用' }}</el-tag>
                <span v-if="m.pinned" class="pin-badge">
                  <el-icon :size="12"><StarFilled /></el-icon>
                  已固定
                </span>
              </div>
              <div class="memory-content">{{ m.content }}</div>
            </div>
            <div class="memory-actions">
              <el-button size="small" text :icon="m.pinned ? StarFilled : Star" @click="togglePin(m)">
                {{ m.pinned ? '取消固定' : '固定' }}
              </el-button>
              <el-button size="small" text type="danger" :icon="Delete" @click="deleteMemory(m.id)">
                删除
              </el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无记忆" />
      </div>

      <!-- Summaries tab -->
      <div v-if="activeTab === 'summaries'" class="tab-content" v-loading="summaryLoading">
        <div v-if="summaries.length > 0" class="summary-list">
          <el-card
            v-for="s in summaries"
            :key="s.id"
            class="summary-card"
            shadow="never"
          >
            <template #header>
              <div class="summary-card-header">
                <el-icon :size="14"><ChatLineSquare /></el-icon>
                <span class="summary-title">{{ s.title || '会话摘要' }}</span>
                <el-tag size="small" type="info" effect="light">{{ s.scope }}</el-tag>
              </div>
            </template>
            <p class="summary-text">{{ s.summary }}</p>
          </el-card>
        </div>
        <el-empty v-else description="暂无摘要" />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import {
  Plus, Collection, Star, StarFilled, Memo,
  Delete, ChatLineSquare
} from '@element-plus/icons-vue'
import { request } from '@/utils/request'
import { ElMessage } from 'element-plus-secondary'

const loading = ref(false)
const summaryLoading = ref(false)
const memories = ref<any[]>([])
const summaries = ref<any[]>([])
const activeTab = ref('memories')
const newMemory = ref({ content: '' })

const pinnedCount = computed(() => memories.value.filter(m => m.pinned).length)

const tabs = computed(() => [
  { name: 'memories', label: '记忆', icon: 'Collection', count: memories.value.length },
  { name: 'summaries', label: '摘要', icon: 'ChatLineSquare', count: summaries.value.length },
])

const loadMemories = async () => {
  loading.value = true
  try {
    const res: any = await request.get('/ai2bi/memory')
    memories.value = res || []
  } finally { loading.value = false }
}

const loadSummaries = async () => {
  summaryLoading.value = true
  try {
    const res: any = await request.get('/ai2bi/memory/summaries')
    summaries.value = res || []
  } finally { summaryLoading.value = false }
}

const createMemory = async () => {
  if (!newMemory.value.content) return
  await request.post('/ai2bi/memory', { scope: 'user', content: newMemory.value.content })
  ElMessage.success('记忆已添加')
  newMemory.value.content = ''
  await loadMemories()
}

const togglePin = async (m: any) => {
  await request.put(`/ai2bi/memory/${m.id}`, { pinned: !m.pinned })
  await loadMemories()
}

const deleteMemory = async (id: number) => {
  if (!confirm('确认删除？')) return
  await request.delete(`/ai2bi/memory/${id}`)
  ElMessage.success('已删除')
  await loadMemories()
}

onMounted(() => { loadMemories(); loadSummaries() })
</script>

<style scoped>
.ai2bi-memory {
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
.stat-icon.pinned { background: #fff6e6; color: #e6a23c; }
.stat-info { display: flex; flex-direction: column; }
.stat-num { font-size: 22px; font-weight: 700; color: #1f2329; line-height: 1; }
.stat-label { font-size: 12px; color: #8f959e; margin-top: 4px; }

/* Tabs */
.tab-bar {
  display: flex;
  gap: 4px;
  padding: 12px 24px;
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

/* Content area */
.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}
.tab-content { max-width: 960px; }

/* Memory list */
.memory-list { display: flex; flex-direction: column; gap: 10px; }
.memory-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #e8e9eb;
  border-radius: 8px;
  transition: all 0.2s;
}
.memory-item:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.memory-item.pinned { border-left: 3px solid #e6a23c; }
.memory-main { flex: 1; min-width: 0; }
.memory-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.pin-badge {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  color: #e6a23c;
  background: #fff6e6;
  padding: 1px 6px;
  border-radius: 4px;
}
.memory-content {
  font-size: 14px;
  color: #1f2329;
  line-height: 1.6;
  word-break: break-all;
}
.memory-actions {
  display: flex;
  gap: 4px;
  margin-left: 12px;
  flex-shrink: 0;
}

/* Summary list */
.summary-list { display: flex; flex-direction: column; gap: 12px; }
.summary-card { border-radius: 8px; }
.summary-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.summary-card-header .el-icon { color: #409eff; }
.summary-title { font-weight: 500; font-size: 14px; color: #1f2329; }
.summary-text { font-size: 13px; color: #606266; line-height: 1.6; margin: 0; }
</style>
