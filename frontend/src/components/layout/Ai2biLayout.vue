<script lang="ts" setup>
import { ref, computed, onMounted, watch, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { request } from '@/utils/request'
import Person from './Person.vue'
import icon_side_fold_outlined from '@/assets/svg/icon_side-fold_outlined.svg'
import icon_side_expand_outlined from '@/assets/svg/icon_side-expand_outlined.svg'
import icon_more_outlined from '@/assets/svg/icon_more_outlined.svg'
import icon_folder from '@/assets/svg/icon_folder.svg'
import {
  Document, Grid, Collection, ChatDotSquare, Cpu, EditPen,
  Histogram, Notebook, Calendar, ChatRound, Star, FirstAidKit
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const collapse = ref(false)
const viewMode = ref<'active' | 'archived'>('active')
const menuTarget = ref<any>(null)
const menuX = ref(0)
const menuY = ref(0)

// 会话列表
const sessions = ref<any[]>([])

const loadSessions = async () => {
  try {
    const res: any = await request.get('/chat/list', { params: { archived: viewMode.value === 'archived' } })
    sessions.value = (res || []).slice(0, 30)
  } catch {
    sessions.value = []
  }
}

const toggleViewMode = () => {
  viewMode.value = viewMode.value === 'active' ? 'archived' : 'active'
  loadSessions()
}

const archiveSession = async (s: any) => {
  const archived = viewMode.value === 'archived'
  try {
    await request.post('/chat/archive', { id: s.id, is_archived: !archived })
    sessions.value = sessions.value.filter((x) => x.id !== s.id)
  } catch {
    // ignore
  }
}

const openMenu = (e: MouseEvent, s: any) => {
  e.stopPropagation()
  menuTarget.value = s
  menuX.value = Math.min(e.clientX, window.innerWidth - 120)
  menuY.value = e.clientY
}

const startNewChat = () => {
  router.push({ path: '/chat/index', query: { new_chat: String(Date.now()) } })
}

const openSession = (id: number) => {
  router.push({ path: '/chat/index', query: { start_chat: String(id) } })
}

// 图标映射 — 使用 markRaw 避免 Vue 的响应式包装
const iconMap: Record<string, any> = {
  Document: markRaw(Document),
  Grid: markRaw(Grid),
  Collection: markRaw(Collection),
  ChatDotSquare: markRaw(ChatDotSquare),
  Cpu: markRaw(Cpu),
  EditPen: markRaw(EditPen),
  Histogram: markRaw(Histogram),
  Notebook: markRaw(Notebook),
  Calendar: markRaw(Calendar),
  ChatRound: markRaw(ChatRound),
  Star: markRaw(Star),
  FirstAidKit: markRaw(FirstAidKit),
}

const getIcon = (name: string) => iconMap[name] || Document

// 中层导航
const navGroups = [
  {
    title: '知识管理',
    items: [
      { path: '/assets/index', label: '数据资产', icon: 'Notebook' },
      { path: '/metrics/index', label: '指标管理', icon: 'Histogram' },
      { path: '/tables/index', label: '表管理', icon: 'Grid' },
    ]
  },
  {
    title: '工具',
    items: [
      { path: '/agents/index', label: 'Agent 管理', icon: 'Cpu' },
      { path: '/skill-dev/index', label: 'Skill 开发', icon: 'EditPen' },
      { path: '/memory/index', label: '我的记忆', icon: 'Star' },
    ]
  },
]

const activeNav = computed(() => {
  const path = route.path
  if (path.startsWith('/chat')) return 'chat'
  for (const g of navGroups) {
    for (const m of g.items) {
      if (path.startsWith(m.path.split('/').slice(0, 2).join('/'))) return m.path
    }
  }
  return ''
})

const handleFoldExpand = () => {
  collapse.value = !collapse.value
}

onMounted(() => {
  loadSessions()
  window.addEventListener('click', () => { menuTarget.value = null })
})

watch(() => route.path, (newPath) => {
  if (newPath.startsWith('/chat')) {
    loadSessions()
  }
})
</script>

<template>
  <div class="ai2bi-layout">
    <!-- Left sidebar -->
    <div class="ai2bi-sidebar" :class="collapse && 'collapsed'">
      <!-- Logo -->
      <div class="logo-area" @click="startNewChat">
        <span class="logo-icon">AI</span>
        <span v-if="!collapse" class="logo-text">AIBI</span>
      </div>

      <!-- Upper: 问数 (new chat + session list) -->
      <div class="sidebar-upper">
        <div class="new-chat-btn" @click="startNewChat">
          <el-icon size="14"><ChatRound /></el-icon>
          <span v-if="!collapse">新对话</span>
        </div>
        <div v-if="!collapse" class="session-toolbar">
          <span class="session-toolbar-label">{{ viewMode === 'archived' ? '归档会话' : '会话' }}</span>
          <el-icon class="session-toolbar-icon" :class="{ active: viewMode === 'archived' }" @click="toggleViewMode">
            <component :is="icon_folder" />
          </el-icon>
        </div>
        <div v-if="!collapse" class="session-list">
          <div v-for="s in sessions" :key="s.id"
               class="session-item-wrap">
            <div :class="['session-item', { active: route.query.start_chat == s.id }]"
                 @click="openSession(s.id)">
              <span class="session-brief">{{ s.brief || '新对话' }}</span>
              <el-icon class="session-more" size="13" @click.stop="openMenu($event, s)">
                <component :is="icon_more_outlined" />
              </el-icon>
            </div>
          </div>
          <div v-if="!sessions.length" class="session-empty">
            {{ viewMode === 'archived' ? '暂无归档会话' : '暂无会话' }}
          </div>
        </div>
      </div>

      <!-- Middle: grouped nav modules -->
      <div class="sidebar-nav">
        <div v-for="group in navGroups" :key="group.title" class="nav-group">
          <div v-if="!collapse" class="nav-group-title">{{ group.title }}</div>
          <div v-for="m in group.items" :key="m.path"
               :class="['nav-item', { active: activeNav === m.path }]"
               @click="router.push(m.path)">
            <el-icon size="16"><component :is="getIcon(m.icon)" /></el-icon>
            <span v-if="!collapse" class="nav-label">{{ m.label }}</span>
          </div>
        </div>
      </div>

      <!-- Bottom: user -->
      <div class="sidebar-bottom">
        <Person :collapse="collapse" :in-sysmenu="false"></Person>
        <div class="fold-btn" @click="handleFoldExpand">
          <el-icon size="18">
            <icon_side_expand_outlined v-if="collapse"></icon_side_expand_outlined>
            <icon_side_fold_outlined v-else></icon_side_fold_outlined>
          </el-icon>
        </div>
      </div>
    </div>

    <!-- Right content area -->
    <div class="ai2bi-main">
      <router-view :key="route.fullPath" />
    </div>

    <!-- 会话右键菜单 -->
    <div v-if="menuTarget" class="session-menu" :style="{ top: menuY + 'px', left: menuX + 'px' }">
      <div class="session-menu-item" @click="archiveSession(menuTarget)">
        <el-icon size="14"><component :is="icon_folder" /></el-icon>
        {{ viewMode === 'archived' ? '取消归档' : '归档' }}
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.ai2bi-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  background: #fff;
  overflow: hidden;
}

.ai2bi-sidebar {
  width: 240px;
  height: 100vh;
  background: #f7f8fa;
  border-right: 1px solid #ebedf0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.2s;

  &.collapsed {
    width: 64px;
    .logo-text, .nav-label, .new-chat-btn span:last-child, .session-list, .session-toolbar { display: none; }
    .logo-area { justify-content: center; }
    .new-chat-btn { justify-content: center; }
    .nav-item { justify-content: center; }
  }
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 16px 8px;
  cursor: pointer;
  flex-shrink: 0;
  .logo-icon {
    width: 32px; height: 32px;
    background: #1cba90;
    color: #fff;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 700;
    flex-shrink: 0;
  }
  .logo-text {
    font-size: 16px; font-weight: 600; color: #1f2329;
  }
}

.sidebar-upper {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0 8px;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 13px;
  color: #1f2329;
  cursor: pointer;
  margin: 4px 0 8px;
  &:hover { border-color: #1cba90; color: #1cba90; }
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 4px 6px;
  .session-toolbar-label {
    font-size: 12px;
    color: #909399;
  }
  .session-toolbar-icon {
    cursor: pointer;
    color: #c0c4cc;
    padding: 2px;
    &:hover { color: #1cba90; }
    &.active { color: #1cba90; }
  }
}

.session-item-wrap {
  position: relative;
}

.session-empty {
  padding: 20px 10px;
  text-align: center;
  font-size: 12px;
  color: #c0c4cc;
}

.session-item {
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  color: #646a73;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 4px;
  &:hover { background: #ebf0f5; }
  &.active { background: #e6f7ef; color: #1cba90; }
  .session-brief {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .session-more {
    display: none;
    color: #909399;
    flex-shrink: 0;
    &:hover { color: #1cba90; }
  }
  &:hover .session-more { display: block; }
}

.session-menu {
  position: fixed;
  z-index: 3000;
  background: #fff;
  border: 1px solid #ebedf0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 4px;
  min-width: 110px;
  .session-menu-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 13px;
    color: #4e5969;
    cursor: pointer;
    &:hover { background: #ebf0f5; color: #1cba90; }
  }
}

.sidebar-nav {
  flex-shrink: 0;
  padding: 8px 8px 4px;
  border-top: 1px solid #ebedf0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-group-title {
  padding: 4px 12px 2px;
  font-size: 10px;
  font-weight: 500;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #4e5969;
  &:hover { background: #ebf0f5; }
  &.active {
    background: #e6f7ef;
    color: #1cba90;
    font-weight: 500;
  }
  .nav-label { flex: 1; }
  .nav-badge {
    font-size: 9px;
    color: #c0c4cc;
    flex-shrink: 0;
  }
}

.sidebar-bottom {
  flex-shrink: 0;
  padding: 8px 12px;
  border-top: 1px solid #ebedf0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.fold-btn {
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  &:hover { background: #ebf0f5; }
}

.ai2bi-main {
  flex: 1;
  height: 100vh;
  overflow: hidden;
}
</style>
