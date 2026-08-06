<template>
  <div class="ai2bi-agents">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">Agent 管理</h1>
        <p class="page-subtitle">管理 AI2BI 智能分析 Agent，包括路由信号、技能绑定、数据权限等</p>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索 Agent 名称或业务线..."
          clearable
          size="default"
          style="width: 280px"
        />
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
          新建 Agent
        </el-button>
      </div>
    </div>

    <!-- Stats bar -->
    <div class="stats-row">
      <div class="stat-item">
        <div class="stat-icon"><el-icon :size="24"><OfficeBuilding /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ agents.length }}</div>
          <div class="stat-label">Agent 总数</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon published"><el-icon :size="24"><CircleCheck /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ agents.filter(a => a.status === 'published').length }}</div>
          <div class="stat-label">已发布</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon dev"><el-icon :size="24"><EditPen /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ agents.filter(a => a.status === 'dev').length }}</div>
          <div class="stat-label">开发中</div>
        </div>
      </div>
      <div class="stat-item">
        <div class="stat-icon"><el-icon :size="24"><DataAnalysis /></el-icon></div>
        <div class="stat-info">
          <div class="stat-num">{{ totalSkills }}</div>
          <div class="stat-label">绑定 Skills</div>
        </div>
      </div>
    </div>

    <!-- Agent grid -->
    <div class="agent-grid-container" v-loading="loading">
      <div v-if="filteredAgents.length > 0" class="agent-grid">
        <el-card
          v-for="a in filteredAgents"
          :key="a.id"
          class="agent-card"
          shadow="hover"
          @click="openDetail(a)"
        >
          <div class="card-header">
            <div class="card-header-left">
              <div class="agent-icon" :class="a.vertical">
                <el-icon :size="20"><component :is="agentIcon(a.vertical)" /></el-icon>
              </div>
              <div class="card-header-info">
                <div class="agent-name">{{ a.name }}</div>
                <div class="agent-meta">
                  <el-tag size="small" :type="statusType(a.status)" effect="plain">{{ statusLabel(a.status) }}</el-tag>
                  <span class="agent-version">v{{ a.version }}</span>
                  <span class="agent-vertical">{{ a.vertical }}</span>
                </div>
              </div>
            </div>
            <el-icon class="card-arrow"><ArrowRight /></el-icon>
          </div>

          <div class="card-body">
            <div class="card-desc" :title="a.description">{{ a.description || '暂无描述' }}</div>
          </div>

          <div class="card-footer">
            <div class="footer-stats">
              <span class="footer-stat">
                <el-icon><Tools /></el-icon>
                {{ a.skill_count || 0 }} Skills
              </span>
              <span class="footer-stat">
                <el-icon><Grid /></el-icon>
                {{ a.table_count || 0 }} 表
              </span>
              <span class="footer-stat">
                <el-icon><User /></el-icon>
                {{ a.grant_count || 0 }} 用户
              </span>
            </div>
            <div class="footer-actions" @click.stop>
              <el-button size="small" text :icon="Edit" @click="editAgent(a)">编辑</el-button>
              <el-button size="small" text type="danger" :icon="Delete" @click="deleteAgent(a)">删除</el-button>
            </div>
          </div>
        </el-card>
      </div>
      <el-empty v-else description="暂无 Agent" />
    </div>

    <!-- Detail drawer -->
    <el-drawer v-model="detailVisible" :title="currentAgent?.name || 'Agent 详情'" size="60%">
      <div v-if="currentAgent" class="agent-detail">
        <el-tabs v-model="detailTab" type="border-card">
          <el-tab-pane label="基本信息" name="basic">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Agent 代码">{{ currentAgent.code }}</el-descriptions-item>
              <el-descriptions-item label="名称">{{ currentAgent.name }}</el-descriptions-item>
              <el-descriptions-item label="业务线">{{ currentAgent.business_line }}</el-descriptions-item>
              <el-descriptions-item label="垂直域">{{ currentAgent.vertical }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="statusType(currentAgent.status)" effect="plain">{{ statusLabel(currentAgent.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="版本">v{{ currentAgent.version }}</el-descriptions-item>
              <el-descriptions-item label="负责人">{{ currentAgent.owner || '-' }}</el-descriptions-item>
              <el-descriptions-item label="隔离规则" :span="2">{{ currentAgent.isolation_rules || '-' }}</el-descriptions-item>
            </el-descriptions>

            <div class="detail-actions" v-if="currentAgent.status === 'dev'">
              <el-button type="success" :icon="Promotion" @click="publishAgent">发布 Agent</el-button>
            </div>
          </el-tab-pane>

          <el-tab-pane label="Skills" name="skills">
            <div v-if="currentAgent.skills?.length" class="detail-section">
              <h4 class="section-title">
                <el-icon><Tools /></el-icon> 包含 Skills ({{ currentAgent.skills.length }})
              </h4>
              <div class="tag-list">
                <el-tag v-for="sk in currentAgent.skills" :key="sk" type="primary" effect="light" size="default">
                  {{ sk }}
                </el-tag>
              </div>
            </div>
            <el-empty v-else description="暂无 Skills" />
          </el-tab-pane>

          <el-tab-pane label="数据表" name="tables">
            <div v-if="currentAgent.exclusive_tables?.length" class="detail-section">
              <h4 class="section-title">
                <el-icon><Grid /></el-icon> 专属表 ({{ currentAgent.exclusive_tables.length }})
              </h4>
              <div class="tag-list">
                <el-tag v-for="t in currentAgent.exclusive_tables" :key="t" type="success" effect="light" size="default">
                  {{ t }}
                </el-tag>
              </div>
            </div>
            <div v-if="currentAgent.shared_tables?.length" class="detail-section">
              <h4 class="section-title">
                <el-icon><Grid /></el-icon> 可引用基座表 ({{ currentAgent.shared_tables.length }})
              </h4>
              <div class="tag-list">
                <el-tag v-for="t in currentAgent.shared_tables" :key="t" type="info" effect="light" size="default">
                  {{ t }}
                </el-tag>
              </div>
            </div>
            <el-empty v-if="!currentAgent.exclusive_tables?.length && !currentAgent.shared_tables?.length" description="暂无数据表" />
          </el-tab-pane>

          <el-tab-pane label="路由信号" name="signals">
            <div v-if="currentAgent.entry_signals?.length" class="detail-section">
              <h4 class="section-title">
                <el-icon><Promotion /></el-icon> 路由信号 ({{ currentAgent.entry_signals.length }})
              </h4>
              <div class="tag-list">
                <el-tag v-for="sig in currentAgent.entry_signals" :key="sig" type="warning" effect="light" size="default">
                  {{ sig }}
                </el-tag>
              </div>
            </div>
            <el-empty v-else description="暂无路由信号" />
          </el-tab-pane>

          <el-tab-pane label="版本历史" name="versions">
            <el-timeline v-if="currentAgent.versions?.length">
              <el-timeline-item
                v-for="v in currentAgent.versions"
                :key="v.version"
                :type="v.version === currentAgent.version ? 'primary' : ''"
                :hollow="v.version !== currentAgent.version"
                placement="top"
              >
                <div class="version-card">
                  <div class="version-header">
                    <span class="version-num">v{{ v.version }}</span>
                    <span class="version-date">{{ v.published_at?.substring(0, 10) }}</span>
                  </div>
                  <div class="version-log">{{ v.changelog || '无变更说明' }}</div>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无版本记录" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>

    <!-- Create/Edit dialog -->
    <el-dialog v-model="showCreateDialog" :title="isEdit ? '编辑 Agent' : '新建 Agent'" width="520px">
      <el-form label-width="100px" :model="form">
        <el-form-item label="代码">
          <el-input v-model="form.code" placeholder="如 card_agent" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如 卡域分析" />
        </el-form-item>
        <el-form-item label="垂直域">
          <el-input v-model="form.vertical" placeholder="如 retail_card" />
        </el-form-item>
        <el-form-item label="业务线">
          <el-select v-model="form.business_line" style="width: 100%">
            <el-option label="零售" value="零售" />
            <el-option label="对公" value="对公" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="路由信号">
          <el-input v-model="signalsInput" placeholder="逗号分隔，如 信用卡,消费,MPAU" />
        </el-form-item>
        <el-form-item label="Skills">
          <el-input v-model="skillsInput" placeholder="逗号分隔，如 card/director/SKILL.md" />
        </el-form-item>
        <el-form-item label="专属表">
          <el-input v-model="tablesInput" placeholder="逗号分隔" />
        </el-form-item>
        <el-form-item label="基座表">
          <el-input v-model="sharedInput" placeholder="逗号分隔" />
        </el-form-item>
        <el-form-item label="隔离规则">
          <el-input v-model="form.isolation_rules" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAgent">{{ isEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import {
  Plus, OfficeBuilding, CircleCheck, EditPen, DataAnalysis,
  ArrowRight, Tools, Grid, User, Delete, Edit, Promotion
} from '@element-plus/icons-vue'
import { request } from '@/utils/request'
import { ElMessage } from 'element-plus-secondary'

const loading = ref(false)
const agents = ref<any[]>([])
const currentAgent = ref<any>(null)
const detailVisible = ref(false)
const showCreateDialog = ref(false)
const searchQuery = ref('')
const detailTab = ref('basic')
const isEdit = ref(false)

const form = ref({
  code: '', name: '', vertical: '', business_line: '零售',
  description: '', isolation_rules: ''
})
const signalsInput = ref('')
const skillsInput = ref('')
const tablesInput = ref('')
const sharedInput = ref('')

const statusType = (s: string) => ({ published: 'success', dev: 'warning', archived: 'info' }[s] || 'info')
const statusLabel = (s: string) => ({ published: '已发布', dev: '开发中', archived: '已归档' }[s] || s)

const agentIcon = (v: string) => {
  const map: Record<string, string> = {
    retail_card: 'CreditCard',
    corp_fx: 'Money',
    corp_deposit: 'BankBuilding',
    corp_income: 'TrendCharts',
    corp_transfer: 'Switch',
  }
  return map[v] || 'Robot'
}

const filteredAgents = computed(() => {
  if (!searchQuery.value) return agents.value
  const q = searchQuery.value.toLowerCase()
  return agents.value.filter(a =>
    a.name?.toLowerCase().includes(q) ||
    a.code?.toLowerCase().includes(q) ||
    a.business_line?.toLowerCase().includes(q) ||
    a.vertical?.toLowerCase().includes(q)
  )
})

const totalSkills = computed(() =>
  agents.value.reduce((sum, a) => sum + (a.skill_count || 0), 0)
)

const loadAgents = async () => {
  loading.value = true
  try { agents.value = await request.get('/ai2bi/agents') || [] }
  finally { loading.value = false }
}

const openDetail = async (a: any) => {
  currentAgent.value = await request.get(`/ai2bi/agents/${a.id}`)
  detailTab.value = 'basic'
  detailVisible.value = true
}

const editAgent = async (a: any) => {
  isEdit.value = true
  currentAgent.value = await request.get(`/ai2bi/agents/${a.id}`)
  const c = currentAgent.value
  form.value = {
    code: c.code, name: c.name, vertical: c.vertical,
    business_line: c.business_line, description: c.description || '', isolation_rules: c.isolation_rules || ''
  }
  signalsInput.value = (c.entry_signals || []).join(', ')
  skillsInput.value = (c.skills || []).join(', ')
  tablesInput.value = (c.exclusive_tables || []).join(', ')
  sharedInput.value = (c.shared_tables || []).join(', ')
  showCreateDialog.value = true
}

const saveAgent = async () => {
  const body = {
    ...form.value,
    entry_signals: signalsInput.value.split(',').map((s: string) => s.trim()).filter(Boolean),
    skills: skillsInput.value.split(',').map((s: string) => s.trim()).filter(Boolean),
    exclusive_tables: tablesInput.value.split(',').map((s: string) => s.trim()).filter(Boolean),
    shared_tables: sharedInput.value.split(',').map((s: string) => s.trim()).filter(Boolean),
  }
  if (isEdit.value && currentAgent.value) {
    await request.put(`/ai2bi/agents/${currentAgent.value.id}`, body)
    ElMessage.success('Agent 已更新')
  } else {
    await request.post('/ai2bi/agents', body)
    ElMessage.success('Agent 已创建')
  }
  showCreateDialog.value = false
  resetForm()
  await loadAgents()
}

const deleteAgent = async (a: any) => {
  if (!confirm(`确认删除 Agent "${a.name}"?`)) return
  await request.delete(`/ai2bi/agents/${a.id}`)
  ElMessage.success('已删除')
  await loadAgents()
}

const resetForm = () => {
  form.value = { code: '', name: '', vertical: '', business_line: '零售', description: '', isolation_rules: '' }
  signalsInput.value = skillsInput.value = tablesInput.value = sharedInput.value = ''
  isEdit.value = false
}

const publishAgent = async () => {
  if (!currentAgent.value) return
  await request.post(`/ai2bi/agents/${currentAgent.value.id}/publish`, { changelog: '发布' })
  ElMessage.success('Agent 已发布')
  detailVisible.value = false
  await loadAgents()
}

onMounted(() => loadAgents())
</script>

<style scoped>
.ai2bi-agents {
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
.stat-icon.published { background: #e6f7ef; color: #1cba90; }
.stat-icon.dev { background: #fff6e6; color: #e6a23c; }
.stat-info { display: flex; flex-direction: column; }
.stat-num { font-size: 22px; font-weight: 700; color: #1f2329; line-height: 1; }
.stat-label { font-size: 12px; color: #8f959e; margin-top: 4px; }

/* Agent grid */
.agent-grid-container {
  flex: 1;
  padding: 16px 24px;
  overflow-y: auto;
}
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.agent-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid #e8e9eb;
}
.agent-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  border-color: #1cba90;
  transform: translateY(-2px);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}
.card-header-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
}
.agent-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
  color: #606266;
  flex-shrink: 0;
}
.agent-icon.retail_card { background: #e6f7ef; color: #1cba90; }
.agent-icon.corp_fx { background: #e6f0ff; color: #409eff; }
.agent-icon.corp_deposit { background: #fff0f0; color: #f56c6c; }
.agent-icon.corp_income { background: #f0f9ff; color: #0ea5e9; }
.card-header-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.agent-name {
  font-size: 15px;
  font-weight: 600;
  color: #1f2329;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agent-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.agent-version {
  font-size: 11px;
  color: #8f959e;
  background: #f5f7fa;
  padding: 1px 6px;
  border-radius: 4px;
}
.agent-vertical {
  font-size: 11px;
  color: #8f959e;
}
.card-arrow {
  color: #c0c4cc;
  transition: color 0.2s;
}
.agent-card:hover .card-arrow { color: #1cba90; }

.card-body {
  margin-bottom: 12px;
  min-height: 36px;
}
.card-desc {
  font-size: 13px;
  color: #8f959e;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
.footer-stats {
  display: flex;
  gap: 16px;
}
.footer-stat {
  font-size: 12px;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 4px;
}
.footer-stat .el-icon { font-size: 14px; color: #8f959e; }

/* Detail */
.agent-detail { padding: 0; }
.detail-actions { margin-top: 24px; text-align: right; }
.detail-section { margin-bottom: 20px; }
.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
  margin: 0 0 12px 0;
}
.section-title .el-icon { color: #1cba90; }
.tag-list { display: flex; flex-wrap: wrap; gap: 8px; }

/* Version timeline */
.version-card {
  background: #fafbfc;
  border: 1px solid #e8e9eb;
  border-radius: 8px;
  padding: 10px 14px;
}
.version-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.version-num { font-weight: 600; color: #1cba90; font-size: 13px; }
.version-date { font-size: 12px; color: #8f959e; }
.version-log { font-size: 13px; color: #606266; line-height: 1.5; }
</style>
