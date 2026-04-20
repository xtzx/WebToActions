import { createBrowserRouter, RouterProvider } from 'react-router-dom';

import { AppShell } from '../components/layout/AppShell';
import { ActionDetailPage } from '../pages/actions/ActionDetailPage';
import { ActionListPage } from '../pages/actions/ActionListPage';
import { ExecutionCenterPage } from '../pages/execution/ExecutionCenterPage';
import { ExecutionDetailPage } from '../pages/execution/ExecutionDetailPage';
import { HomePage } from '../pages/HomePage';
import { ImportExportPage } from '../pages/importexport/ImportExportPage';
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
        element: <ActionListPage />
      },
      {
        path: 'actions/:actionId',
        element: <ActionDetailPage />
      },
      {
        path: 'execution',
        element: <ExecutionCenterPage />
      },
      {
        path: 'execution/:executionId',
        element: <ExecutionDetailPage />
      },
      {
        path: 'importexport',
        element: <ImportExportPage />
      }
    ]
  }
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
