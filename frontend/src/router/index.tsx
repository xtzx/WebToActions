import { createBrowserRouter, RouterProvider } from 'react-router-dom';

import { AppShell } from '../components/layout/AppShell';
import { HomePage } from '../pages/HomePage';
import { RecordingDetailPage } from '../pages/recordings/RecordingDetailPage';
import { RecordingListPage } from '../pages/recordings/RecordingListPage';
import { NewRecordingPage } from '../pages/recordings/NewRecordingPage';
import { ReviewPage } from '../pages/review/ReviewPage';
import { SectionPlaceholderPage } from '../pages/SectionPlaceholderPage';
import { SessionListPage } from '../pages/sessions/SessionListPage';

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
        element: <RecordingListPage />
      },
      {
        path: 'recordings/new',
        element: <NewRecordingPage />
      },
      {
        path: 'recordings/:recordingId',
        element: <RecordingDetailPage />
      },
      {
        path: 'sessions',
        element: <SessionListPage />
      },
      {
        path: 'review',
        element: (
          <SectionPlaceholderPage
            title="审核中心"
            description="请从录制详情进入具体录制的审核页。"
          />
        )
      },
      {
        path: 'review/:recordingId',
        element: <ReviewPage />
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
