import { createBrowserRouter, RouterProvider } from 'react-router-dom';

import { AppShell } from '../components/layout/AppShell';
import { HomePage } from '../pages/HomePage';
import { SectionPlaceholderPage } from '../pages/SectionPlaceholderPage';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <HomePage />
      },
      {
        path: 'recordings',
        element: (
          <SectionPlaceholderPage
            title="录制中心"
            description="这里会承接录制相关页面与流程入口。"
          />
        )
      },
      {
        path: 'sessions',
        element: (
          <SectionPlaceholderPage
            title="会话管理"
            description="这里会承接会话列表、状态查看与后续管理入口。"
          />
        )
      },
      {
        path: 'review',
        element: (
          <SectionPlaceholderPage
            title="审核中心"
            description="这里会承接审核结果查看与问题处理入口。"
          />
        )
      },
      {
        path: 'actions',
        element: (
          <SectionPlaceholderPage
            title="动作库"
            description="这里会承接动作资产查看、维护与复用入口。"
          />
        )
      },
      {
        path: 'execution',
        element: (
          <SectionPlaceholderPage
            title="执行中心"
            description="这里会承接执行任务发起、结果查看与运行入口。"
          />
        )
      },
      {
        path: 'importexport',
        element: (
          <SectionPlaceholderPage
            title="导入导出"
            description="这里会承接数据迁移、导入导出与交换入口。"
          />
        )
      }
    ]
  }
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
