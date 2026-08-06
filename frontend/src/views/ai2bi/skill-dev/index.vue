<template>
  <div class="skill-dev">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">Skill 开发</h1>
        <p class="page-subtitle">编写和管理 Skill 文件，支持 Markdown 编辑和实时测试对话</p>
      </div>
      <div class="header-right">
        <el-button size="default" :icon="DocumentAdd" @click="newSkillDialog = true">
          新建 Skill
        </el-button>
      </div>
    </div>

    <div class="layout-body">
      <!-- Left: file tree -->
      <div class="file-tree-panel">
        <div class="panel-header">
          <el-icon :size="14"><Folder /></el-icon>
          <span>文件列表</span>
        </div>
        <div class="panel-toolbar">
          <el-input
            v-model="treeSearch"
            placeholder="搜索文件..."
            size="small"
            clearable
            :prefix-icon="Search"
          />
        </div>
        <div class="tree-body">
          <template v-for="node in filteredFileTree" :key="node.path">
            <FileTreeNode
              :node="node"
              :depth="0"
              :selected="currentFile"
              @select="selectFile"
            />
          </template>
          <el-empty v-if="!filteredFileTree.length" description="无文件" />
        </div>
      </div>

      <!-- Right: editor + test -->
      <div class="right-panel">
        <template v-if="currentFile">
          <!-- Editor toolbar -->
          <div class="editor-toolbar">
            <div class="toolbar-left">
              <el-icon :size="14" class="file-icon"><Document /></el-icon>
              <span class="file-path">{{ currentFile }}</span>
              <el-tag v-if="dirty" size="small" type="warning" effect="light">未保存</el-tag>
            </div>
            <div class="toolbar-right">
              <el-button size="small" text :icon="Reading" @click="editing = false">
                预览
              </el-button>
              <el-button size="small" text :icon="EditPen" @click="editing = true">
                编辑
              </el-button>
              <el-button size="small" type="success" :icon="Check" @click="saveFile" :disabled="!dirty">
                保存
              </el-button>
            </div>
          </div>

          <!-- Editor area -->
          <div class="editor-area">
            <div v-if="editing" class="edit-mode">
              <textarea
                ref="editRef"
                v-model="fileContent"
                class="doc-textarea"
                @input="dirty = true"
                spellcheck="false"
              />
            </div>
            <div v-else class="view-mode">
              <div class="doc-content" v-html="renderedMarkdown"></div>
            </div>
          </div>

          <!-- Test chat panel -->
          <div class="chat-panel">
            <div class="chat-header">
              <div class="chat-header-left">
                <el-icon :size="14"><ChatDotSquare /></el-icon>
                <span>测试对话</span>
                <el-tag v-if="selectedSkill" size="small" type="primary" effect="light" class="skill-tag">
                  @{{ getSkillName(selectedSkill) }}
                </el-tag>
              </div>
              <div class="chat-header-right">
                <el-select
                  v-model="selectedSkill"
                  size="small"
                  placeholder="@ 指定 Skill"
                  filterable
                  clearable
                  style="width: 160px"
                >
                  <el-option
                    v-for="sk in availableSkills"
                    :key="sk.path"
                    :label="'@' + sk.name"
                    :value="sk.path"
                  />
                </el-select>
                <el-button size="small" text :icon="Delete" @click="clearChat">
                  清空
                </el-button>
              </div>
            </div>
            <div class="chat-messages" ref="chatRef">
              <div
                v-for="(msg, i) in chatMsgs"
                :key="i"
                :class="['chat-msg', msg.role]"
              >
                <div class="msg-avatar">
                  <el-icon :size="14"><User v-if="msg.role === 'user'" /><ChatLineSquare v-else /></el-icon>
                </div>
                <div class="msg-body" v-html="msg.html || msg.text"></div>
              </div>
              <div v-if="chatLoading" class="chat-msg ai">
                <div class="msg-avatar loading">
                  <el-icon :size="14"><Loading /></el-icon>
                </div>
                <div class="msg-body">
                  <span class="loading-text">思考中...</span>
                </div>
              </div>
              <div v-if="!chatMsgs.length && !chatLoading" class="chat-empty">
                <el-icon :size="32"><ChatDotSquare /></el-icon>
                <p>输入问题测试当前 Skill</p>
                <p class="hint">例如：@card_trans 查7月卡消费金额</p>
              </div>
            </div>
            <div class="chat-input-bar">
              <el-input
                v-model="chatInput"
                placeholder="@skill 你的问题..."
                @keydown.enter.prevent="sendChat"
                :disabled="chatLoading"
              />
              <el-button
                type="primary"
                :icon="Promotion"
                @click="sendChat"
                :disabled="chatLoading || !chatInput.trim()"
              >
                发送
              </el-button>
            </div>
          </div>
        </template>

        <!-- Empty state -->
        <div v-else class="empty-state">
          <el-icon :size="48" class="empty-icon"><FolderOpened /></el-icon>
          <h3>选择左侧文件开始</h3>
          <p>点击文件列表中的文件，即可在编辑器中查看和编辑</p>
        </div>
      </div>
    </div>

    <!-- New skill dialog -->
    <el-dialog v-model="newSkillDialog" title="新建 Skill" width="400px">
      <el-input v-model="newSkillName" placeholder="如 card_retention" />
      <template #footer>
        <el-button @click="newSkillDialog = false">取消</el-button>
        <el-button type="primary" @click="createSkill">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import {
  ref, computed, onMounted, defineComponent, h, nextTick, watch
} from 'vue'
import {
  DocumentAdd, Folder, Document, EditPen, Check,
  Search, Reading, Delete, ChatDotSquare, ChatLineSquare,
  User, Loading, Promotion, FolderOpened
} from '@element-plus/icons-vue'
import { request } from '@/utils/request'
import { ElMessage } from 'element-plus-secondary'

// ── Markdown renderer ──
function renderMd(md: string): string {
  if (!md) return '<p style="color:#c0c4cc">空文件</p>'
  let html = md
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, _lang, code) => `<pre class="md-code"><code>${esc(code.trim())}</code></pre>`)
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="md-inline">$1</code>')
    .replace(/^\|(.+)\|$/gm, (m) => {
      const cells = m.split('|').filter(c => c.trim())
      if (cells.every(c => /^[\s-]+$/.test(c))) return ''
      return `<tr>${cells.map(c => `<td>${c.trim()}</td>`).join('')}</tr>`
    })
    .replace(/(<tr>[\s\S]*?<\/tr>\n?)+/g, '<table>$&</table>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>\n?)+/g, '<ul>$&</ul>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/\n/g, '<br>')
    .replace(/<br>(<h[1-4]>)/g, '$1').replace(/(<\/h[1-4]>)<br>/g, '$1')
    .replace(/<br>(<table>)/g, '$1').replace(/(<\/table>)<br>/g, '$1')
    .replace(/<br>(<ul>)/g, '$1').replace(/(<\/ul>)<br>/g, '$1')
    .replace(/<br>(<pre)/g, '$1').replace(/(<\/pre>)<br>/g, '$1')
    .replace(/<br>(<blockquote>)/g, '$1').replace(/(<\/blockquote>)<br>/g, '$1')
  return html
}
function esc(s: string) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') }

// ── State ──
const fileTree = ref<any[]>([])
const treeSearch = ref('')
const currentFile = ref('')
const fileContent = ref('')
const dirty = ref(false)
const editing = ref(false)
const editRef = ref<HTMLTextAreaElement>()
const newSkillDialog = ref(false)
const newSkillName = ref('')

const renderedMarkdown = computed(() => renderMd(fileContent.value))

watch(editing, (val) => {
  if (val) nextTick(() => editRef.value?.focus())
})

// File tree filter
const filteredFileTree = computed(() => {
  if (!treeSearch.value) return fileTree.value
  const q = treeSearch.value.toLowerCase()
  const filter = (nodes: any[]): any[] => {
    return nodes.map(n => {
      if (n.type === 'file') {
        return n.name.toLowerCase().includes(q) ? n : null
      }
      const filtered = filter(n.children || [])
      const valid = filtered.filter(Boolean)
      if (valid.length) return { ...n, children: valid, expanded: true }
      if (n.name.toLowerCase().includes(q)) return { ...n, children: n.children || [] }
      return null
    }).filter(Boolean)
  }
  return filter(fileTree.value)
})

// ── File tree ──
const FileTreeNode = defineComponent({
  name: 'FTN',
  props: { node: Object, depth: Number, selected: String },
  emits: ['select'],
  setup(props, { emit }) {
    const exp = ref(true)
    return () => {
      const n: any = props.node, ind = (props.depth || 0) * 16
      const sel = props.selected === n.path
      if (n.type === 'dir') return h('div', [
        h('div', {
          class: ['tn', 'dir', { sel }],
          style: { paddingLeft: ind + 'px' },
          onClick: () => { exp.value = !exp.value }
        }, [
          h('span', { class: 'ar' }, exp.value ? '▾' : '▸'),
          h('el-icon', { size: 14 }, [h('Folder')]),
          h('span', n.name)
        ]),
        exp.value && n.children?.map((c: any) => h(FileTreeNode, {
          node: c, depth: (props.depth || 0) + 1,
          selected: props.selected,
          onSelect: (p: string) => emit('select', p)
        }))
      ])
      return h('div', {
        class: ['tn', 'file', { sel }],
        style: { paddingLeft: (ind + 16) + 'px' },
        onClick: () => emit('select', n.path)
      }, [
        h('el-icon', { size: 14 }, [h('Document')]),
        h('span', n.name)
      ])
    }
  }
})

const loadTree = async () => { fileTree.value = await request.get('/ai2bi/skill-dev/files') || [] }

const selectFile = async (path: string) => {
  if (dirty.value && !confirm('有未保存修改，确认切换？')) return
  currentFile.value = path; dirty.value = false; editing.value = false
  const res: any = await request.get('/ai2bi/skill-dev/files/content', { params: { path } })
  fileContent.value = res?.content || ''
  loadAvailableSkills()
}

const saveFile = async () => {
  if (!currentFile.value) return
  await request.post('/ai2bi/skill-dev/files/content', { path: currentFile.value, content: fileContent.value })
  dirty.value = false
  ElMessage.success('已保存')
}

const createSkill = async () => {
  if (!newSkillName.value) return
  await request.post('/ai2bi/skill-dev/scaffold', newSkillName.value)
  ElMessage.success('已创建'); newSkillDialog.value = false; newSkillName.value = ''
  await loadTree()
}

// ── Test chat ──
const availableSkills = ref<any[]>([])
const selectedSkill = ref('')
const chatMsgs = ref<any[]>([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatRef = ref<HTMLElement>()

const getSkillName = (path: string) => {
  const sk = availableSkills.value.find(s => s.path === path)
  return sk?.name || path
}

const loadAvailableSkills = async () => {
  const tree = await request.get('/ai2bi/skill-dev/files')
  const skills: any[] = []
  const walk = (nodes: any[]) => {
    for (const n of nodes) {
      if (n.type === 'file' && n.name.endsWith('.md') && n.path.startsWith('skills/')) {
        const parts = n.path.split('/')
        const name = parts[parts.length - 2] || parts[parts.length - 1].replace('.md', '')
        skills.push({ name, path: n.path })
      }
      if (n.children) walk(n.children)
    }
  }
  walk(tree || [])
  availableSkills.value = skills
}

const sendChat = async () => {
  const q = chatInput.value.trim()
  if (!q || chatLoading.value) return

  let skill = selectedSkill.value
  let question = q
  const atMatch = q.match(/^@(\S+)\s+(.*)/)
  if (atMatch) {
    const skillName = atMatch[1]
    question = atMatch[2]
    const found = availableSkills.value.find(s => s.name === skillName)
    if (found) skill = found.path
  }

  if (!skill && currentFile.value) {
    const filePath = currentFile.value
    if (filePath.startsWith('skills/') && filePath.endsWith('.md')) {
      skill = filePath
    }
  }

  chatMsgs.value.push({ role: 'user', text: q })
  chatInput.value = ''
  chatLoading.value = true
  await nextTick(); scrollChat()

  try {
    const startRes: any = await request.post('/chat/start', { datasource: 3, origin: 0 })
    const chatId = startRes?.id
    if (!chatId) throw new Error('无法创建测试会话')

    const resp = await request.fetchStream('/chat/question', {
      chat_id: chatId,
      question,
      skill_path: skill || undefined,
    })

    let aiText = '', aiHtml = ''
    chatMsgs.value.push({ role: 'ai', text: '', html: '' })
    const aiIdx = chatMsgs.value.length - 1

    const reader = resp.body?.getReader()
    const decoder = new TextDecoder()
    while (reader) {
      const { done, value } = await reader.read()
      if (done) break
      for (const line of decoder.decode(value).split('\n')) {
        if (!line.startsWith('data:')) continue
        try {
          const d = JSON.parse(line.slice(5))
          if (d.type === 'sql-result' && d.content) aiText += d.content
          else if (d.type === 'analysis' && d.content) aiText += d.content
          else if (d.type === 'knowledge_qa' && d.content) aiText += d.content
          else if (d.type === 'sql') aiHtml += `<pre class="chat-sql">${esc(d.content)}</pre>`
          else if (d.type === 'chart') aiHtml += `<div class="chat-chart">📊 ${d.content?.match(/"title":"(.*?)"/)?.[1] || '图表'}</div>`
          else if (d.type === 'info' && d.msg === 'guardrail_warning') aiHtml += `<div class="chat-warn">${d.content}</div>`
          else if (d.type === 'info' && d.msg === 'analysis_skipped') aiHtml += `<div class="chat-warn">⚠️ 分析跳过: ${esc(d.content || '')}</div>`
          else if (d.type === 'error') aiHtml += `<div class="chat-err">${d.content}</div>`
        } catch {}
      }
      chatMsgs.value[aiIdx].text = aiText
      chatMsgs.value[aiIdx].html = aiHtml || aiText
      await nextTick(); scrollChat()
    }
  } catch (e: any) {
    chatMsgs.value.push({ role: 'ai', text: `测试失败: ${e.message}`, html: '' })
  } finally {
    chatLoading.value = false
    await nextTick(); scrollChat()
  }
}

const clearChat = () => { chatMsgs.value = [] }
const scrollChat = () => { if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight }

onMounted(() => loadTree())
</script>

<style scoped>
.skill-dev {
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
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* File tree panel */
.file-tree-panel {
  width: 220px;
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
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2329;
}
.panel-toolbar {
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
}
.tree-body {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

/* Tree nodes */
:deep(.tn) {
  padding: 5px 12px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.15s;
  border-radius: 4px;
  margin: 1px 4px;
}
:deep(.tn:hover) { background: #f5f7fa; }
:deep(.tn.sel) { background: #e6f7ef; color: #1cba90; font-weight: 500; }
:deep(.tn.dir) { font-weight: 500; color: #1f2329; }
:deep(.tn.file) { color: #606266; }
:deep(.ar) { width: 14px; font-size: 10px; text-align: center; color: #8f959e; }

/* Right panel */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Editor toolbar */
.editor-toolbar {
  padding: 10px 20px;
  background: #fff;
  border-bottom: 1px solid #e8e9eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.toolbar-left .file-icon { color: #8f959e; }
.file-path {
  font-size: 13px;
  color: #606266;
  font-family: 'SF Mono', 'Consolas', monospace;
}
.toolbar-right { display: flex; align-items: center; gap: 4px; }

/* Editor area */
.editor-area {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.edit-mode { flex: 1; display: flex; flex-direction: column; }
.doc-textarea {
  width: 100%;
  flex: 1;
  border: none;
  outline: none;
  padding: 24px 32px;
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.8;
  resize: none;
  background: #fff;
  color: #1f2329;
}
.view-mode {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

/* Markdown styles */
:deep(.doc-content) h1 {
  font-size: 22px;
  font-weight: 700;
  margin: 20px 0 10px;
  border-bottom: 2px solid #1cba90;
  padding-bottom: 6px;
  color: #1f2329;
}
:deep(.doc-content) h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 18px 0 8px;
  color: #1f2329;
}
:deep(.doc-content) h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 14px 0 6px;
  color: #1f2329;
}
:deep(.doc-content) h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 12px 0 4px;
  color: #606266;
}
:deep(.doc-content) {
  font-size: 14px;
  line-height: 1.9;
  color: #333;
}
:deep(.doc-content) table {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}
:deep(.doc-content) td {
  border: 1px solid #e8e8e8;
  padding: 8px 12px;
  font-size: 13px;
}
:deep(.doc-content) tr:nth-child(even) { background: #fafbfc; }
:deep(.md-code) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 14px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 12px;
  margin: 10px 0;
  line-height: 1.6;
}
:deep(.md-inline) {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  font-family: 'Consolas', monospace;
  color: #1f2329;
}
:deep(.doc-content) ul { padding-left: 24px; margin: 8px 0; }
:deep(.doc-content) li { margin: 4px 0; }
:deep(.doc-content) blockquote {
  border-left: 3px solid #1cba90;
  padding-left: 14px;
  margin: 10px 0;
  color: #666;
  background: #f6fffa;
  border-radius: 0 4px 4px 0;
  padding: 8px 14px;
}

/* Chat panel */
.chat-panel {
  height: 280px;
  border-top: 1px solid #e8e9eb;
  display: flex;
  flex-direction: column;
  background: #fff;
  flex-shrink: 0;
}
.chat-header {
  padding: 8px 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fafbfc;
  flex-shrink: 0;
}
.chat-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}
.chat-header-left .el-icon { color: #1cba90; }
.chat-header-right { display: flex; align-items: center; gap: 8px; }
.skill-tag { margin-left: 4px; }

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px 16px;
}
.chat-msg {
  margin-bottom: 10px;
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e6f0ff;
  color: #409eff;
  flex-shrink: 0;
}
.chat-msg.ai .msg-avatar { background: #e6f7ef; color: #1cba90; }
.msg-avatar.loading { background: #fff6e6; color: #e6a23c; }
.msg-body {
  font-size: 13px;
  line-height: 1.6;
  flex: 1;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e8e9eb;
  color: rgba(31, 35, 41, 1);
}
.chat-msg.user .msg-body { background: #f0f7ff; border-color: #d9ecff; }
.loading-text {
  color: #8f959e;
  font-style: italic;
}

:deep(.chat-sql) {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 8px;
  border-radius: 4px;
  font-size: 11px;
  margin: 4px 0;
  line-height: 1.5;
  font-family: 'Consolas', monospace;
}
:deep(.chat-chart) {
  color: #1cba90;
  font-size: 12px;
  padding: 4px 0;
}
:deep(.chat-warn) { color: #e6a23c; font-size: 12px; }
:deep(.chat-err) { color: #f56c6c; font-size: 12px; }

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 0;
  color: #c0c4cc;
  text-align: center;
}
.chat-empty .el-icon { color: #e0e2e6; margin-bottom: 8px; }
.chat-empty p { margin: 2px 0; font-size: 13px; }
.chat-empty .hint { font-size: 12px; color: #c0c4cc; }

.chat-input-bar {
  padding: 8px 16px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  gap: 8px;
  background: #fafbfc;
  flex-shrink: 0;
}

/* Empty state */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  text-align: center;
}
.empty-icon { color: #e0e2e6; margin-bottom: 12px; }
.empty-state h3 { font-size: 16px; color: #8f959e; margin: 0 0 6px; }
.empty-state p { font-size: 13px; color: #c0c4cc; margin: 0; }
</style>
