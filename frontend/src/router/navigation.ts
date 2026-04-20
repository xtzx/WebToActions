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
    description: '查看已生成动作宏，并进入参数化执行入口。'
  },
  {
    label: '执行中心',
    to: '/execution',
    description: '查看执行任务、执行日志与失败定位详情。'
  },
  {
    label: '导入导出',
    to: '/importexport',
    description: '导出单条录制资料包，或导入链路资料包恢复工作区。'
  }
];
