<script lang="ts" setup>
import { computed } from 'vue'
import { ElMenu } from 'element-plus-secondary'
import { useRoute, useRouter } from 'vue-router'
import MenuItem from './MenuItem.vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
defineProps({
  collapse: Boolean,
})

const route = useRoute()
const activeMenu = computed(() => route.path)
const showSysmenu = computed(() => {
  return route.path.includes('/system')
})

const formatRoute = (arr: any, parentPath = '') => {
  return arr.map((element: any) => {
    let children: any = []
    const path = `${parentPath ? parentPath + '/' : ''}${element.path}`
    if (element.children?.length) {
      children = formatRoute(element.children, path)
    }
    return {
      ...element,
      path,
      children,
    }
  })
}

// AI2BI: 只展示问数 + 6 个 AI2BI 模块，隐藏 Dashboard/Assistant/原 SQLBot 配置
const ai2biMenuPaths = new Set([
  '/chat/index',
  '/assets/index',
  '/tables/index',
  '/metrics/index',
  '/skill-dev/index',
  '/memory/index',
])

const routerList = computed(() => {
  if (showSysmenu.value) {
    const [sysRouter] = formatRoute(
      router.getRoutes().filter((route: any) => route?.name === 'system')
    )
    return sysRouter?.children || []
  }
  // Flatten AI2BI routes: use child routes directly as top-level menu items
  const list = router.getRoutes().filter((route) => {
    return ai2biMenuPaths.has(route.path)
  })
  // Ensure meta is set on each route for menu rendering
  return list.map((route: any) => {
    // If meta exists and has title, use it; otherwise derive from route name
    if (!route.meta) route.meta = {}
    if (!route.meta.title && route.name) {
      const titleMap: Record<string, string> = {
        'chat': '问数',
        'assets': '数据资产',
        'tables': '表管理',
        'metrics': '指标管理',
        'skill-dev': 'Skill 开发',
        'memory': '我的记忆',
      }
      route.meta.title = titleMap[route.name as string] || route.name
    }
    // Ensure icon props exist
    const iconMap2: Record<string, { iconActive: string; iconDeActive: string }> = {
      'chat': { iconActive: 'chat', iconDeActive: 'noChat' },
      'assets': { iconActive: 'ds', iconDeActive: 'noDs' },
      'tables': { iconActive: 'model', iconDeActive: 'noModel' },
      'metrics': { iconActive: 'workspace', iconDeActive: 'noWorkspace' },
      'skill-dev': { iconActive: 'set', iconDeActive: 'noSet' },
      'memory': { iconActive: 'log', iconDeActive: 'noLog' },
    }
    const icons = iconMap2[route.name as string]
    if (icons && !route.meta.iconActive) {
      route.meta.iconActive = icons.iconActive
      route.meta.iconDeActive = icons.iconDeActive
    }
    return route
  })
})
</script>

<template>
  <el-menu :default-active="activeMenu" class="el-menu-demo ed-menu-vertical" :collapse="collapse">
    <MenuItem v-for="menu in routerList" :key="menu.path" :menu="menu"></MenuItem>
  </el-menu>
</template>

<style lang="less">
.ed-menu-vertical {
  --ed-menu-item-height: 40px;
  --ed-menu-bg-color: transparent;
  --ed-menu-base-level-padding: 4px;
  border-right: none;
  .ed-menu-item {
    height: 40px !important;
    border-radius: 6px !important;
    margin-bottom: 2px;
    &.is-active {
      background-color: #fff !important;
      border-radius: 6px;
      font-weight: 500;
    }
  }

  .ed-sub-menu .ed-sub-menu__title {
    border-radius: 6px;
  }

  .ed-sub-menu.is-active:not(.is-opened) {
    .ed-sub-menu__title {
      background-color: #fff !important;
      color: var(--ed-color-primary) !important;
      font-weight: 500;
    }
  }

  .ed-sub-menu.is-active.is-opened {
    .ed-sub-menu__title {
      color: var(--ed-color-primary) !important;
      font-weight: 500;
    }
  }

  .ed-sub-menu .ed-icon {
    margin-right: 8px;
  }
}
.ed-popper.is-light:has(.ed-menu--popup) {
  border: 1px solid #dee0e3;
  border-radius: 6px;
  box-shadow: 0px 4px 8px 0px #1f23291a;
  background: #eff1f0;
  overflow: hidden;
}
.ed-menu--popup {
  padding: 8px;
  background: #eff1f0;

  .ed-menu-item {
    padding: 9px 16px;
    height: 40px !important;
    border-radius: 6px;
    &.is-active {
      background-color: #fff !important;
      font-weight: 500;
    }
  }
}
.ed-sub-menu {
  .subTitleMenu {
    display: none;
  }
}

.ed-menu--popup-container .subTitleMenu {
  color: #646a73 !important;
  pointer-events: none;
}
</style>
