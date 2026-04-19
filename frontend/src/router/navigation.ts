import type { NavigationItem } from '../types/navigation';

export const navigationItems: NavigationItem[] = [
  {
    label: '首页',
    to: '/',
    description: '查看阶段 1 工程骨架与健康检查入口。'
  },
  {
    label: '录制中心',
    to: '/recordings',
    description: '保留录制流程的正式导航入口。'
  },
  {
    label: '会话管理',
    to: '/sessions',
    description: '保留会话视图与状态管理入口。'
  },
  {
    label: '审核中心',
    to: '/review',
    description: '保留审核流程与结果查看入口。'
  },
  {
    label: '动作库',
    to: '/actions',
    description: '保留动作定义与复用入口。'
  },
  {
    label: '执行中心',
    to: '/execution',
    description: '保留执行编排与运行入口。'
  },
  {
    label: '导入导出',
    to: '/importexport',
    description: '保留数据导入导出入口。'
  }
];
