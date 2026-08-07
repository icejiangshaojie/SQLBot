<script setup lang="ts">
import { computed } from 'vue'
import type { BpOutput, TopicContract } from '@/types/analysis'

const props = withDefaults(
  defineProps<{
    bp?: BpOutput | null
    contract?: TopicContract | null
  }>(),
  {
    bp: null,
    contract: null,
  }
)

const hasContent = computed(
  () =>
    !!props.bp &&
    ((props.bp.executive_summary?.length ?? 0) > 0 ||
      (props.bp.findings?.length ?? 0) > 0 ||
      (props.bp.limitations?.length ?? 0) > 0)
)
</script>

<template>
  <div v-if="hasContent" class="topic-analysis">
    <!-- 摘要 -->
    <section v-if="bp?.executive_summary?.length" class="sec">
      <h4>摘要</h4>
      <ul>
        <li v-for="(s, i) in bp!.executive_summary" :key="i">{{ s.text }}</li>
      </ul>
    </section>

    <!-- 关键发现 -->
    <section v-if="bp?.findings?.length" class="sec">
      <h4>关键发现</h4>
      <ul>
        <li v-for="(f, i) in bp!.findings" :key="i">
          <span class="cat">{{ f.category }}</span> {{ f.text }}
        </li>
      </ul>
    </section>

    <!-- 数据限制 -->
    <section v-if="bp?.limitations?.length" class="sec limitation">
      <h4>数据限制</h4>
      <ul>
        <li v-for="(l, i) in bp!.limitations" :key="i">{{ l }}</li>
      </ul>
    </section>

    <!-- 下一步 -->
    <section v-if="bp?.next_questions?.length" class="sec">
      <h4>下一步</h4>
      <ul>
        <li v-for="(q, i) in bp!.next_questions" :key="i">{{ q }}</li>
      </ul>
    </section>
  </div>
</template>

<style scoped lang="less">
.topic-analysis {
  margin-top: 12px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 12px;
  border: 1px solid rgba(222, 224, 227, 1);

  .sec {
    margin-bottom: 12px;
    h4 {
      margin: 0 0 6px;
      font-size: 14px;
      color: #1d2129;
    }
    ul {
      margin: 0;
      padding-left: 18px;
      li { font-size: 14px; line-height: 22px; color: #4e5969; }
      .cat {
        display: inline-block;
        padding: 0 6px;
        margin-right: 6px;
        border-radius: 4px;
        background: #e8f3ff;
        color: #165dff;
        font-size: 12px;
      }
    }
  }
  .limitation {
    background: #fffbf0;
    border-left: 3px solid #e6a23c;
    padding: 6px 10px;
  }
}
</style>