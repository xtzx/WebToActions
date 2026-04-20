# Stage 1 Engineering Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Spike 收口为正式工程骨架，完成后端配置入口、前端路由壳子、本地启动脚本和最小测试闭环。

**Architecture:** 后端继续使用 `FastAPI` 单应用工厂模式，将配置读取收口到 `backend/app/core/config.py`，并只暴露稳定的健康检查契约；前端引入 `React Router` 和统一 `AppShell`，首页保留健康检查，其他页面只做一级导航占位。运行脚本和仓库文档同步更新，使新的 `session` 可以直接在正式骨架上进入 `阶段 2`。

**Tech Stack:** `Python 3.11+`、`FastAPI`、`pydantic-settings`、`pytest`、`React`、`TypeScript`、`Vite`、`React Router`、`Vitest`、`React Testing Library`

---

## Preconditions

在执行任何任务前，先满足以下前置条件：

1. 运行 `python3.11 --version`，确认本机存在 `Python 3.11+`。
2. 如果 `python3.11` 不存在，**立即暂停并询问用户**，不要退回 `Python 3.10` 兼容路线。
3. 在仓库根目录创建虚拟环境：

```bash
python3.11 -m venv .venv
./.venv/bin/pip install --upgrade pip
```

4. 后端依赖安装在 `Task 1 / Step 2` 执行。
5. 前端新增依赖安装在 `Task 2 / Step 1` 执行。

## File Map

### Backend

- Modify: `backend/pyproject.toml` — 统一 `Python 3.11+` 基线并加入配置依赖
- Create: `backend/app/core/__init__.py` — 对外导出配置对象
- Create: `backend/app/core/config.py` — 环境变量和默认值读取
- Modify: `backend/app/main.py` — 正式应用工厂、CORS 与路由装配
- Modify: `backend/app/api/routes/health.py` — 正式骨架健康检查契约
- Create: `backend/app/session/__init__.py` — `session` 模块边界
- Create: `backend/app/recording/__init__.py` — `recording` 模块边界
- Create: `backend/app/review/__init__.py` — `review` 模块边界
- Create: `backend/app/action/__init__.py` — `action` 模块边界
- Create: `backend/app/execution/__init__.py` — `execution` 模块边界
- Create: `backend/app/importexport/__init__.py` — `importexport` 模块边界
- Create: `backend/app/browser/__init__.py` — `browser` 模块边界
- Create: `backend/app/infrastructure/__init__.py` — `infrastructure` 模块边界
- Create: `backend/tests/core/test_config.py` — 配置默认值测试
- Modify: `backend/tests/api/test_health.py` — 健康检查契约测试

### Frontend

- Modify: `frontend/package.json` — 路由与测试脚本
- Modify: `frontend/vite.config.ts` — `Vitest` 配置
- Modify: `frontend/tsconfig.json` — 前端测试类型声明
- Modify: `frontend/index.html` — 清理重复 HTML 文档
- Create: `frontend/src/test/setup.ts` — `jest-dom` 测试初始化
- Create: `frontend/src/types/navigation.ts` — 导航项类型
- Create: `frontend/src/router/navigation.ts` — 一级导航模型
- Create: `frontend/src/router/index.tsx` — 路由定义与 `RouterProvider`
- Create: `frontend/src/components/layout/AppShell.tsx` — 左侧导航 + 内容区骨架
- Create: `frontend/src/pages/SectionPlaceholderPage.tsx` — 非首页的统一占位页
- Modify: `frontend/src/pages/HomePage.tsx` — 首页概览 + 健康检查
- Modify: `frontend/src/services/health.ts` — 新健康检查响应类型
- Modify: `frontend/src/App.tsx` — 应用入口改为路由
- Create: `frontend/src/App.test.tsx` — 路由壳子与首页渲染测试
- Create: `frontend/src/features/.gitkeep` — 追踪 `features/` 目录

### Scripts and Docs

- Create: `scripts/dev/start_backend.sh` — 后端启动脚本
- Create: `scripts/dev/start_frontend.sh` — 前端启动脚本
- Modify: `README.md` — 仓库阶段、运行方式和下一阶段说明
- Modify: `backend/README.md` — 后端工程骨架说明
- Modify: `docs/技术文档/开发步骤拆解.md` — 将 `阶段 1` 从 `进行中` 改为 `已完成`
- Modify: `docs/superpowers/specs/2026-04-19-stage-1-engineering-skeleton-design.md` — 与最终落地状态保持一致

## Task 1: Formalize Backend Config and Health Contract

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/routes/health.py`
- Create: `backend/app/session/__init__.py`
- Create: `backend/app/recording/__init__.py`
- Create: `backend/app/review/__init__.py`
- Create: `backend/app/action/__init__.py`
- Create: `backend/app/execution/__init__.py`
- Create: `backend/app/importexport/__init__.py`
- Create: `backend/app/browser/__init__.py`
- Create: `backend/app/infrastructure/__init__.py`
- Test: `backend/tests/core/test_config.py`
- Test: `backend/tests/api/test_health.py`

- [ ] **Step 1: Raise the backend Python baseline and add config support**

Update `backend/pyproject.toml` to this content:

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "webtoactions-backend"
version = "0.1.0"
description = "Backend engineering skeleton for WebToActions"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "pydantic>=2",
  "pydantic-settings>=2",
  "playwright>=1.49.0",
  "uvicorn[standard]>=0.32.0",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.28.0",
  "pytest>=8.3.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.setuptools.packages.find]
include = ["app*"]
```

- [ ] **Step 2: Install backend dependencies into the repo virtualenv**

Run from the repo root:

```bash
./.venv/bin/pip install -e "./backend[dev]"
```

Expected: install completes successfully and exposes `pytest`, `fastapi`, `pydantic-settings`, and `uvicorn` inside `./.venv`.

- [ ] **Step 3: Write the failing config test**

Create `backend/tests/core/test_config.py`:

```python
from pathlib import Path

import pytest

from app.core.config import Settings


@pytest.fixture(autouse=True)
def clear_stage1_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "APP_NAME",
        "APP_ENV",
        "API_PREFIX",
        "WEBTOACTIONS_DATA_DIR",
        "FRONTEND_DEV_ORIGIN",
        "BROWSER_CHANNEL",
        "BROWSER_HEADLESS",
    ):
        monkeypatch.delenv(key, raising=False)


def test_settings_use_stage1_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "WebToActions Backend"
    assert settings.app_env == "development"
    assert settings.api_prefix == "/api"
    assert settings.frontend_dev_origin == "http://127.0.0.1:5173"
    assert settings.target_python == "3.11+"
    assert settings.webtoactions_data_dir == Path(".webtoactions")
    assert settings.browser_channel == "chromium"
    assert settings.browser_headless is False
```

- [ ] **Step 4: Run the config test to verify it fails**

Run from `backend/`:

```bash
../.venv/bin/python -m pytest tests/core/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError` because `app.core.config` does not exist yet.

- [ ] **Step 5: Implement the config module**

Create `backend/app/core/__init__.py`:

```python
"""Core configuration utilities for the backend skeleton."""

from app.core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
```

Create `backend/app/core/config.py`:

```python
from functools import lru_cache
from pathlib import Path
import sys

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = Field(default="WebToActions Backend", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")
    webtoactions_data_dir: Path = Field(
        default=Path(".webtoactions"),
        alias="WEBTOACTIONS_DATA_DIR",
    )
    frontend_dev_origin: str = Field(
        default="http://127.0.0.1:5173",
        alias="FRONTEND_DEV_ORIGIN",
    )
    browser_channel: str = Field(default="chromium", alias="BROWSER_CHANNEL")
    browser_headless: bool = Field(default=False, alias="BROWSER_HEADLESS")

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def target_python(self) -> str:
        return "3.11+"

    @property
    def runtime_python(self) -> str:
        return (
            f"{sys.version_info.major}."
            f"{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Run the config test to verify it passes**

Run from `backend/`:

```bash
../.venv/bin/python -m pytest tests/core/test_config.py -v
```

Expected: PASS with `1 passed`.

- [ ] **Step 7: Write the failing health contract test**

Replace `backend/tests/api/test_health.py` with:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_stage1_contract() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["phase"] == "stage1"
    assert payload["appName"] == "WebToActions Backend"
    assert payload["environment"] == "development"
    assert payload["apiPrefix"] == "/api"
    assert payload["targetPython"] == "3.11+"
    assert payload["dataDir"] == ".webtoactions"
    assert payload["browserChannel"] == "chromium"
    assert payload["browserHeadless"] is False
    assert isinstance(payload["runtimePython"], str)


def test_create_app_uses_configured_title() -> None:
    app = create_app()

    assert app.title == "WebToActions Backend"
```

- [ ] **Step 8: Run the health test to verify it fails**

Run from `backend/`:

```bash
../.venv/bin/python -m pytest tests/api/test_health.py -v
```

Expected: FAIL because the current endpoint still returns Spike-era fields such as `stage`.

- [ ] **Step 9: Implement the app factory, health route, and package boundaries**

Replace `backend/app/main.py` with:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_dev_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix=settings.api_prefix)
    return app


app = create_app()
```

Replace `backend/app/api/routes/health.py` with:

```python
from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter(tags=["system"])


@router.get("/health")
def get_health() -> dict[str, str | bool]:
    settings = get_settings()

    return {
        "status": "ok",
        "phase": "stage1",
        "appName": settings.app_name,
        "environment": settings.app_env,
        "apiPrefix": settings.api_prefix,
        "targetPython": settings.target_python,
        "runtimePython": settings.runtime_python,
        "dataDir": str(settings.webtoactions_data_dir),
        "browserChannel": settings.browser_channel,
        "browserHeadless": settings.browser_headless,
    }
```

Create the package boundary files from `backend/`:

```bash
mkdir -p app/session app/recording app/review app/action app/execution app/importexport app/browser app/infrastructure
for package in session recording review action execution importexport browser infrastructure; do
  printf '"""Stage 1 package boundary for %s features."""\n' "${package}" > "app/${package}/__init__.py"
done
```

- [ ] **Step 10: Run the backend test suite to verify it passes**

Run from `backend/`:

```bash
../.venv/bin/python -m pytest tests -v
```

Expected: PASS with the new config test and the updated health tests all green.

- [ ] **Step 11: Create a checkpoint commit only if the user explicitly requests one**

```bash
git add backend/pyproject.toml backend/app backend/tests
git commit -m "feat: formalize backend stage 1 skeleton"
```

## Task 2: Add Frontend Router, App Shell, and Test Harness

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/tsconfig.json`
- Modify: `frontend/index.html`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/types/navigation.ts`
- Create: `frontend/src/router/navigation.ts`
- Create: `frontend/src/router/index.tsx`
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/pages/SectionPlaceholderPage.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/services/health.ts`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/App.test.tsx`
- Create: `frontend/src/features/.gitkeep`

- [ ] **Step 1: Install frontend routing and test dependencies, then configure Vitest**

Run from `frontend/`:

```bash
npm install react-router-dom
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom
npm pkg set scripts.test="vitest"
npm pkg set scripts["test:run"]="vitest run"
```

Replace `frontend/vite.config.ts` with:

```typescript
/// <reference types="vitest/config" />

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 4173
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts'
  }
});
```

Replace `frontend/tsconfig.json` with:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowSyntheticDefaultImports": true,
    "forceConsistentCasingInFileNames": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "noEmit": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "strict": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"]
}
```

Create `frontend/src/test/setup.ts`:

```typescript
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 2: Write the failing app shell test**

Create `frontend/src/App.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';

import App from './App';

test('renders the stage 1 app shell and home dashboard', () => {
  window.history.pushState({}, '', '/');

  render(<App />);

  expect(screen.getByRole('navigation', { name: '主导航' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: '首页' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: '录制中心' })).toBeInTheDocument();
  expect(
    screen.getByRole('heading', { level: 1, name: 'WebToActions 管理台' })
  ).toBeInTheDocument();
  expect(
    screen.getByRole('button', { name: '检查后端健康状态' })
  ).toBeInTheDocument();
});
```

- [ ] **Step 3: Run the app shell test to verify it fails**

Run from `frontend/`:

```bash
npm run test:run -- src/App.test.tsx
```

Expected: FAIL because `App.tsx` still renders only the old `HomePage` and there is no `navigation` landmark.

- [ ] **Step 4: Implement the router, shell, placeholder pages, and updated home page**

Create `frontend/src/types/navigation.ts`:

```typescript
export interface NavigationItem {
  label: string;
  to: string;
  description: string;
}
```

Create `frontend/src/router/navigation.ts`:

```typescript
import type { NavigationItem } from '../types/navigation';

export const navigationItems: NavigationItem[] = [
  {
    label: '首页',
    to: '/',
    description: '查看当前工程骨架状态和健康检查入口。'
  },
  {
    label: '录制中心',
    to: '/recordings',
    description: '阶段 1 先保留入口，阶段 3 再接入真实录制流程。'
  },
  {
    label: '会话管理',
    to: '/sessions',
    description: '阶段 1 先保留入口，阶段 3 再接入会话管理能力。'
  },
  {
    label: '审核中心',
    to: '/review',
    description: '阶段 1 先保留入口，阶段 4 再接入审核页。'
  },
  {
    label: '动作库',
    to: '/actions',
    description: '阶段 1 先保留入口，阶段 5 再接入宏定义与详情页。'
  },
  {
    label: '执行中心',
    to: '/execution',
    description: '阶段 1 先保留入口，阶段 5 再接入执行日志和步骤视图。'
  },
  {
    label: '导入导出',
    to: '/importexport',
    description: '阶段 1 先保留入口，阶段 6 再接入资料包迁移能力。'
  }
];
```

Create `frontend/src/router/index.tsx`:

```typescript
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
            description="阶段 1 只建立正式导航入口；阶段 3 会把录制列表、录制详情和会话管理能力接进来。"
          />
        )
      },
      {
        path: 'sessions',
        element: (
          <SectionPlaceholderPage
            title="会话管理"
            description="阶段 1 只保留正式导航入口；阶段 3 会把浏览器会话、登录态摘要和关联录制接进来。"
          />
        )
      },
      {
        path: 'review',
        element: (
          <SectionPlaceholderPage
            title="审核中心"
            description="阶段 1 只保留正式导航入口；阶段 4 会把 MetadataDraft、审核版本和参数确认接进来。"
          />
        )
      },
      {
        path: 'actions',
        element: (
          <SectionPlaceholderPage
            title="动作库"
            description="阶段 1 只保留正式导航入口；阶段 5 会把 ActionMacro 列表、详情和参数定义接进来。"
          />
        )
      },
      {
        path: 'execution',
        element: (
          <SectionPlaceholderPage
            title="执行中心"
            description="阶段 1 只保留正式导航入口；阶段 5 会把执行日志、步骤状态和失败定位接进来。"
          />
        )
      },
      {
        path: 'importexport',
        element: (
          <SectionPlaceholderPage
            title="导入导出"
            description="阶段 1 只保留正式导航入口；阶段 6 会把资料包导入导出和运行模式接进来。"
          />
        )
      }
    ]
  }
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
```

Create `frontend/src/components/layout/AppShell.tsx`:

```typescript
import { NavLink, Outlet } from 'react-router-dom';

import { navigationItems } from '../../router/navigation';

const shellStyle = {
  minHeight: '100vh',
  display: 'grid',
  gridTemplateColumns: '240px 1fr',
  background: '#f5f7fb',
  color: '#162033',
  fontFamily:
    'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
} as const;

const sidebarStyle = {
  borderRight: '1px solid #d8e0ee',
  background: '#ffffff',
  padding: '24px 20px'
} as const;

const brandStyle = {
  margin: '0 0 8px',
  fontSize: '20px'
} as const;

const subtitleStyle = {
  margin: '0 0 20px',
  fontSize: '14px',
  lineHeight: 1.6,
  color: '#475467'
} as const;

const navListStyle = {
  listStyle: 'none',
  margin: 0,
  padding: 0,
  display: 'grid',
  gap: '8px'
} as const;

const linkBaseStyle = {
  display: 'block',
  borderRadius: '10px',
  padding: '10px 12px',
  textDecoration: 'none',
  color: '#344054',
  fontWeight: 600
} as const;

const activeLinkStyle = {
  background: '#e8f0ff',
  color: '#2247a5'
} as const;

const contentStyle = {
  padding: '32px'
} as const;

export function AppShell() {
  return (
    <div style={shellStyle}>
      <aside style={sidebarStyle}>
        <h1 style={brandStyle}>WebToActions</h1>
        <p style={subtitleStyle}>
          阶段 1 先收口正式工程骨架，后续阶段再逐步接入录制、审核、执行和导入导出能力。
        </p>
        <nav aria-label="主导航">
          <ul style={navListStyle}>
            {navigationItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  style={({ isActive }) =>
                    isActive
                      ? { ...linkBaseStyle, ...activeLinkStyle }
                      : linkBaseStyle
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      <main style={contentStyle}>
        <Outlet />
      </main>
    </div>
  );
}
```

Create `frontend/src/pages/SectionPlaceholderPage.tsx`:

```typescript
type SectionPlaceholderPageProps = {
  title: string;
  description: string;
};

const panelStyle = {
  maxWidth: '760px',
  border: '1px solid #d8e0ee',
  borderRadius: '16px',
  background: '#ffffff',
  padding: '24px',
  boxShadow: '0 12px 40px rgba(15, 23, 42, 0.06)'
} as const;

export function SectionPlaceholderPage({
  title,
  description
}: SectionPlaceholderPageProps) {
  return (
    <section style={panelStyle}>
      <h1 style={{ marginTop: 0 }}>{title}</h1>
      <p style={{ margin: 0, lineHeight: 1.7, color: '#475467' }}>{description}</p>
    </section>
  );
}
```

Replace `frontend/src/services/health.ts` with:

```typescript
export interface HealthResponse {
  status: string;
  phase: string;
  appName: string;
  environment: string;
  apiPrefix: string;
  targetPython: string;
  runtimePython: string;
  dataDir: string;
  browserChannel: string;
  browserHeadless: boolean;
}

const HEALTH_ENDPOINT = '/api/health';

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(HEALTH_ENDPOINT, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error(
      `Health check failed: ${response.status} ${response.statusText}`
    );
  }

  return (await response.json()) as HealthResponse;
}
```

Replace `frontend/src/pages/HomePage.tsx` with:

```typescript
import { useState, type CSSProperties } from 'react';

import { fetchHealth, type HealthResponse } from '../services/health';

type RequestState = 'idle' | 'loading' | 'success' | 'error';

const pageStyle: CSSProperties = {
  display: 'grid',
  gap: '20px'
};

const panelStyle: CSSProperties = {
  background: '#ffffff',
  border: '1px solid #d8e0ee',
  borderRadius: '16px',
  padding: '24px',
  boxShadow: '0 12px 40px rgba(15, 23, 42, 0.06)'
};

const badgeStyle: CSSProperties = {
  display: 'inline-block',
  padding: '6px 10px',
  borderRadius: '999px',
  background: '#e8f0ff',
  color: '#2247a5',
  fontSize: '12px',
  fontWeight: 700,
  letterSpacing: '0.04em',
  textTransform: 'uppercase'
};

const metaRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '12px',
  marginTop: '16px'
};

const metaItemStyle: CSSProperties = {
  padding: '10px 12px',
  borderRadius: '12px',
  background: '#eef2f8',
  fontSize: '14px'
};

const actionRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: '12px',
  marginTop: '16px'
};

const buttonStyle: CSSProperties = {
  border: 0,
  borderRadius: '10px',
  padding: '12px 16px',
  background: '#2247a5',
  color: '#ffffff',
  fontSize: '14px',
  fontWeight: 600,
  cursor: 'pointer'
};

const outputStyle: CSSProperties = {
  marginTop: '16px',
  padding: '16px',
  borderRadius: '12px',
  background: '#0f172a',
  color: '#e2e8f0',
  overflowX: 'auto',
  fontSize: '14px',
  lineHeight: 1.5
};

const placeholderStyle: CSSProperties = {
  marginTop: '16px',
  padding: '16px',
  borderRadius: '12px',
  border: '1px dashed #b8c4d9',
  background: '#fafcff',
  color: '#667085'
};

function getStatusLabel(state: RequestState, health: HealthResponse | null) {
  if (state === 'loading') {
    return '正在检查后端健康状态...';
  }

  if (state === 'success' && health) {
    return `后端已响应，当前阶段为 ${health.phase}，目标 Python 基线为 ${health.targetPython}。`;
  }

  if (state === 'error') {
    return '后端健康检查失败。';
  }

  return '尚未执行健康检查。';
}

export function HomePage() {
  const [requestState, setRequestState] = useState<RequestState>('idle');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const statusLabel = getStatusLabel(requestState, health);

  async function handleHealthCheck() {
    setRequestState('loading');
    setErrorMessage(null);

    try {
      const payload = await fetchHealth();
      setHealth(payload);
      setRequestState('success');
    } catch (error) {
      setHealth(null);
      setRequestState('error');
      setErrorMessage(
        error instanceof Error ? error.message : 'Unknown health check error.'
      );
    }
  }

  return (
    <div style={pageStyle}>
      <section style={panelStyle}>
        <span style={badgeStyle}>Stage 1 Skeleton</span>
        <h1 style={{ margin: '16px 0 12px' }}>WebToActions 管理台</h1>
        <p style={{ margin: 0, lineHeight: 1.7, color: '#475467' }}>
          当前阶段先把已经验证通过的 Spike 收口成正式工程骨架：统一配置、路由、导航、启动方式和最小测试基线。
        </p>
        <div style={metaRowStyle}>
          <span style={metaItemStyle}>后端入口：FastAPI app factory</span>
          <span style={metaItemStyle}>前端入口：React Router</span>
          <span style={metaItemStyle}>下一阶段：领域模型与存储骨架</span>
        </div>
      </section>

      <section style={panelStyle}>
        <h2 style={{ marginTop: 0 }}>后端健康检查</h2>
        <p style={{ margin: 0, lineHeight: 1.7, color: '#475467' }}>
          前端通过 <code>/api/health</code> 验证当前正式工程骨架是否联通。开发模式下由
          <code>Vite</code> 代理到 <code>http://127.0.0.1:8000</code>。
        </p>
        <div style={actionRowStyle}>
          <button
            type="button"
            style={buttonStyle}
            onClick={() => void handleHealthCheck()}
            disabled={requestState === 'loading'}
          >
            {requestState === 'loading' ? '检查中...' : '检查后端健康状态'}
          </button>
          <span>{statusLabel}</span>
        </div>

        {health ? (
          <pre style={outputStyle}>{JSON.stringify(health, null, 2)}</pre>
        ) : (
          <div style={placeholderStyle}>
            健康检查结果会在这里显示，用于验证后端配置读取和正式应用入口都已生效。
          </div>
        )}

        {errorMessage ? (
          <div style={{ marginTop: '16px', color: '#b42318' }}>{errorMessage}</div>
        ) : null}
      </section>
    </div>
  );
}
```

Replace `frontend/src/App.tsx` with:

```typescript
import { AppRouter } from './router';

function App() {
  return <AppRouter />;
}

export default App;
```

Replace `frontend/index.html` with:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>WebToActions</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create the tracked `features/` placeholder:

```bash
mkdir -p src/features
touch src/features/.gitkeep
```

- [ ] **Step 5: Run the app shell test to verify it passes**

Run from `frontend/`:

```bash
npm run test:run -- src/App.test.tsx
```

Expected: PASS with `1 passed`.

- [ ] **Step 6: Run full frontend verification**

Run from `frontend/`:

```bash
npm run test:run
npm run build
```

Expected: all frontend tests pass and the build completes successfully.

- [ ] **Step 7: Create a checkpoint commit only if the user explicitly requests one**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tsconfig.json frontend/index.html frontend/src
git commit -m "feat: add stage 1 frontend app shell"
```

## Task 3: Add Stable Dev Start Scripts

**Files:**
- Create: `scripts/dev/start_backend.sh`
- Create: `scripts/dev/start_frontend.sh`

- [ ] **Step 1: Create the backend start script**

Create `scripts/dev/start_backend.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.11)"
else
  echo "Python 3.11+ not found. Create .venv or install python3.11 first." >&2
  exit 1
fi

cd "${BACKEND_DIR}"
exec "${PYTHON_BIN}" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- [ ] **Step 2: Create the frontend start script**

Create `scripts/dev/start_frontend.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"

cd "${FRONTEND_DIR}"
exec npm run dev -- --host 127.0.0.1 --port 5173
```

- [ ] **Step 3: Verify both scripts are valid shell and executable**

Run from the repo root:

```bash
chmod +x scripts/dev/start_backend.sh scripts/dev/start_frontend.sh
bash -n scripts/dev/start_backend.sh
bash -n scripts/dev/start_frontend.sh
```

Expected: no output and exit code `0`.

- [ ] **Step 4: Create a checkpoint commit only if the user explicitly requests one**

```bash
git add scripts/dev/start_backend.sh scripts/dev/start_frontend.sh
git commit -m "chore: add stage 1 dev start scripts"
```

## Task 4: Verify the Phase and Sync the Docs

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `docs/技术文档/开发步骤拆解.md`
- Modify: `docs/superpowers/specs/2026-04-19-stage-1-engineering-skeleton-design.md`

- [ ] **Step 1: Run the full verification suite before touching completion docs**

Run from the repo root:

```bash
./.venv/bin/python -m pytest backend/tests -v
cd frontend && npm run test:run && npm run build
```

Expected: backend tests pass, frontend tests pass, and frontend build succeeds.

- [ ] **Step 2: Verify the backend start script and health endpoint**

In terminal A, run from the repo root:

```bash
./scripts/dev/start_backend.sh
```

In terminal B, run from the repo root:

```bash
curl http://127.0.0.1:8000/api/health
```

Expected JSON:

```json
{
  "status": "ok",
  "phase": "stage1",
  "appName": "WebToActions Backend",
  "environment": "development",
  "apiPrefix": "/api",
  "targetPython": "3.11+",
  "runtimePython": "3.11.x",
  "dataDir": ".webtoactions",
  "browserChannel": "chromium",
  "browserHeadless": false
}
```

- [ ] **Step 3: Verify the frontend start script and manual shell rendering**

In terminal C, run from the repo root:

```bash
./scripts/dev/start_frontend.sh
```

Then open `http://127.0.0.1:5173` in a browser and confirm:

```text
1. 左侧出现“主导航”，包含首页、录制中心、会话管理、审核中心、动作库、执行中心、导入导出
2. 首页主标题为“WebToActions 管理台”
3. 点击“检查后端健康状态”后，页面出现 /api/health 返回的 JSON
```

- [ ] **Step 4: Update the repository-level documentation to mark Stage 1 complete**

Note: the content below is the target completion-state template to apply **after** Stage 1 verification passes. It does not describe the current repository state before Stage 1 is finished.

Replace `README.md` with:

````markdown
# WebToActions

`WebToActions` 是一个“浏览器执行优先、网络证据驱动、支持人工审核和动作抽象”的本地自动化工具。

## 文档入口

- 产品文档：[docs/产品文档/文档索引.md](docs/产品文档/文档索引.md)
- 技术文档：[docs/技术文档/文档索引.md](docs/技术文档/文档索引.md)
- 开发进度看板：[docs/技术文档/开发步骤拆解.md](docs/技术文档/开发步骤拆解.md)

## 当前技术路线

- 后端：`Python 3.11+`
- API：`FastAPI`
- 前端：`React + TypeScript + React Router`
- 浏览器控制：`Playwright Python`
- 本地存储：`SQLite + 文件对象区`
- 长任务状态：`SSE`

## 当前仓库阶段

当前已完成：

- 产品需求文档
- 技术方案设计
- 开发步骤拆解
- 首版实现计划
- 阶段 0：技术 Spike
- 阶段 1：工程骨架

下一步建议：

1. 进入 `docs/技术文档/开发步骤拆解.md` 中的 **阶段 2：领域模型与存储骨架**
2. 固化 `SQLite` 元数据层、对象模型和证据文件区边界
3. 在正式工程骨架基础上继续推进录制链路

## 本地开发

后端启动：

```bash
./scripts/dev/start_backend.sh
```

前端启动：

```bash
./scripts/dev/start_frontend.sh
```
````

Replace `backend/README.md` with:

````markdown
# WebToActions Backend

该目录承载 `WebToActions` 的正式后端工程骨架。

当前阶段已完成：

- `FastAPI` 正式应用入口
- 统一配置读取模块
- 稳定的 `/api/health` 契约
- 后续 `session / recording / review / action / execution / importexport / browser / infrastructure` 模块边界

本地开发启动：

```bash
../scripts/dev/start_backend.sh
```

后端测试：

```bash
../.venv/bin/python -m pytest tests -v
```
````

Replace the Stage 1 row in `docs/技术文档/开发步骤拆解.md` with:

```markdown
| 1 | 工程骨架 | `已完成` | 已完成 `Python 3.11+` 基线、FastAPI 正式入口、React 路由壳子、本地启动脚本与最小测试闭环 |
```

- [ ] **Step 5: Sync the long-lived docs and retire separate process logs**

Update `docs/superpowers/specs/2026-04-19-stage-1-engineering-skeleton-design.md` so that its “文档与阶段状态同步” section reflects the final repository convention:

```markdown
- `README.md` 维护仓库级概览和当前阶段摘要；
- `docs/技术文档/开发步骤拆解.md` 维护阶段状态、下一步和接力规则；
- `docs/superpowers/plans/2026-04-19-stage-1-engineering-skeleton.md` 维护阶段 1 的详细实施步骤与验证方式；
- 不再依赖 `task_plan.md`、`progress.md`、`findings.md` 这类独立过程文件。
```

Expected: after this update, the repository no longer requires separate session-tracking files to understand current status.

- [ ] **Step 6: Create a checkpoint commit only if the user explicitly requests one**

```bash
git add README.md backend/README.md docs/技术文档/开发步骤拆解.md docs/superpowers/specs/2026-04-19-stage-1-engineering-skeleton-design.md
git commit -m "docs: mark stage 1 engineering skeleton complete"
```
