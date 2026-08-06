<template>
  <div class="ai2bi-data-dev">
    <div class="placeholder-card">
      <div class="icon-wrap">
        <el-icon :size="48" color="#1cba90"><DocumentAdd /></el-icon>
      </div>
      <h2>数据开发</h2>
      <p>SQL 建模、表浏览、AI 辅助开发环境</p>
      <div class="hint">
        <el-icon :size="16"><Clock /></el-icon>
        <span>即将开发：SQL 编辑器 + 表浏览 + AI 辅助建模</span>
      </div>
      <div class="features">
        <div class="feature-item">
          <el-icon :size="20"><EditPen /></el-icon>
          <div>
            <div class="feature-title">SQL 编辑器</div>
            <div class="feature-desc">支持语法高亮、自动补全、SQL 格式化</div>
          </div>
        </div>
        <div class="feature-item">
          <el-icon :size="20"><Grid /></el-icon>
          <div>
            <div class="feature-title">表浏览</div>
            <div class="feature-desc">可视化表结构和字段注释浏览</div>
          </div>
        </div>
        <div class="feature-item">
          <el-icon :size="20"><Cpu /></el-icon>
          <div>
            <div class="feature-title">AI 辅助建模</div>
            <div class="feature-desc">AI 辅助生成表定义和 ETL 脚本</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { DocumentAdd, Clock, EditPen, Grid, Cpu } from '@element-plus/icons-vue'
</script>

<style scoped>
.ai2bi-data-dev {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: #f5f7fa;
}
.placeholder-card {
  text-align: center;
  padding: 48px 64px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  max-width: 520px;
}
.icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  border-radius: 16px;
  background: #e6f7ef;
  margin: 0 auto 20px;
}
h2 {
  font-size: 20px;
  color: #1f2329;
  margin: 0 0 8px;
  font-weight: 600;
}
p {
  color: #646a73;
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 20px;
}
.hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #8f959e;
  font-size: 13px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.features {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 24px;
  text-align: left;
}
.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background: #fafbfc;
  border: 1px solid #e8e9eb;
  border-radius: 8px;
}
.feature-item .el-icon { color: #1cba90; margin-top: 2px; }
.feature-title { font-size: 14px; font-weight: 500; color: #1f2329; }
.feature-desc { font-size: 12px; color: #8f959e; margin-top: 2px; }
</style>
