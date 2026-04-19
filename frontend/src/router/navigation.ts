import type { NavigationItem } from '../types/navigation';

export const navigationItems: NavigationItem[] = [
  {
    label: '首页',
    to: '/',
    description: '查看当前阶段概览与后端健康检查入口。'
  },
  {
    label: '录制中心',
    to: '/recordings',
    description: '查看录制列表、创建录制并进入录制详情。'
  },
  {
    label: '会话管理',
    to: '/sessions',
    description: '查看浏览器会话、登录站点摘要与创建新会话。'
  },
  {
    label: '审核中心',
    to: '/review',
    description: '从录制详情进入审核页，查看分析结果并保存审核版本。'
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
