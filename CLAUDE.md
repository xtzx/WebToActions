# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位与阶段

`WebToActions` 是"浏览器执行优先、网络证据驱动"的本地自动化工具。**当前处于阶段 1（工程骨架）**：阶段 0（技术 Spike）已验证过 FastAPI、Playwright 与前后端联调最小闭环，但正式的模块边界、路由壳子、启动脚本、测试框架还在补。

**第一手的阶段信息来自两处，先读它们再动手：**

1. `README.md` —— 当前阶段摘要、入口文档索引
2. `docs/技术文档/开发步骤拆解.md` —— 执行看板、推进顺序、接力规则
3. 当前阶段细节：`docs/superpowers/specs/2026-04-19-stage-1-engineering-skeleton-design.md` + `docs/superpowers/plans/2026-04-19-stage-1-engineering-skeleton.md`

## 常用命令

当前**没有**根级 Makefile / 启动脚本（阶段 1 计划新增 `scripts/dev/start_backend.sh` / `start_frontend.sh`，目前尚未落地），需要手工两终端启动。

### 后端

```bash
cd backend
pip install -e ".[dev]"                           # 含 pytest / httpx
uvicorn app.main:app --reload --port 8000         # 起服务
pytest tests/                                     # 全量测试
pytest tests/api/test_health.py                   # 单文件
pytest tests/api/test_health.py::test_health_ok   # 单用例
```

### 前端

```bash
cd frontend
npm install
npm run dev       # Vite dev server :5173，/api 代理到 127.0.0.1:8000
npm run build     # 构建到 dist/
npm run preview
```

### Spike 脚本（阶段 0 产物，仍可用）

```bash
python backend/spikes/browser_recording_poc.py https://example.com
python backend/spikes/browser_recording_poc.py --browser-channel chrome https://example.com
```

Spike 的录制结果落在 `.webtoactions/spikes/recordings/`。

## 当前可用 vs 占位

| 组件 | 状态 | 说明 |
|---|---|---|
| 后端 FastAPI 入口（`app.main:create_app`） | ✅ 可用 | 只有 `/api/health` 和 `/api/spike/context` 两条路由 |
| 前端 Vite 脚手架 + HomePage | ✅ 可用 | HomePage 通过代理调 `/api/health` 验证联调 |
| Playwright 浏览器录制 | ✅ 可用 | 只在 `backend/spikes/browser_recording_poc.py`，尚未进入 `app/browser/` |
| 业务模块骨架（`session` / `recording` / `review` / `action` / `execution` / `browser` / `infrastructure`） | ⬜ 占位 | 阶段 1 任务，尚未创建 |
| 配置系统（`app/core/config.py`） | ⬜ 占位 | 现在硬写在 `/api/spike/context`，阶段 1 会抽出来 |
| React Router / 多页面 | ⬜ 占位 | 阶段 1 引入，目前只有 HomePage |
| SQLite / SSE / 导入导出 | ⬜ 占位 | 阶段 2+ |
| 前端测试框架（Vitest） | ⬜ 占位 | 阶段 1 引入 |

**不要**把文档里描述的阶段 2 / 3 的结构（领域模型、SSE 长任务、导入导出）当成"已经有"的东西去改或去引用。只有 `backend/app/` 和 `frontend/src/` 下真实存在的代码才是当前基线。

## 仓库结构要点

```
backend/
├── app/
│   ├── main.py                     # FastAPI 应用工厂
│   ├── api/routes/health.py        # 当前仅此
│   └── __init__.py
├── spikes/browser_recording_poc.py # 阶段 0 Playwright 脚本
├── tests/api/test_health.py
└── pyproject.toml                  # fastapi / uvicorn / playwright；requires-python 要升到 3.11+

frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── pages/HomePage.tsx          # 当前唯一页面
│   └── services/health.ts          # 手写 TS 类型 HealthResponse
├── vite.config.ts                  # /api → http://127.0.0.1:8000
└── package.json                    # React 19 / Vite / TS

.webtoactions/                      # 运行时数据（已 .gitignore）
├── spikes/recordings/              # Spike 录制输出
└── app.db                          # 阶段 2 预留

docs/
├── 技术文档/开发步骤拆解.md        # 阶段看板（主执行文档）
├── 技术文档/开发规范.md             # 目录分层、Python 3.11+ 基线
├── 产品文档/
└── superpowers/
    ├── specs/                      # 对应阶段的设计文档
    └── plans/                      # 对应阶段的实施计划
```

## Python 版本陷阱

本机默认 `python3` 可能是 3.10；**正式工程基线是 3.11+**，`backend/.venv` 已固化为 3.11.11。新 session 首选：

```bash
source backend/.venv/bin/activate     # 或
python3.11 -m venv backend/.venv && source backend/.venv/bin/activate
```

`backend/pyproject.toml` 当前仍写 `requires-python>=3.10`，阶段 1 的计划里会改成 `>=3.11`。遇到语法/标准库兼容问题先查 Python 版本。

## 文档工作流与硬性禁令

- **唯一主执行文档**：`docs/技术文档/开发步骤拆解.md`。阶段状态、推进顺序、接力规则都以它为准。
- **不再维护**过程文件：`task_plan.md` / `progress.md` / `findings.md`。禁止新建，原有的也不要往里写内容，相关长期信息要回写到正式文档。
- **冲突仲裁**：代码事实 > 文档。如果文档说的东西代码里没有，以代码为准，然后回写文档修正它，而不是反过来。
- **阶段接力**：新 session 开始时先读"开发步骤拆解.md"的"进度计划（执行看板）"，继续第一个"进行中"或第一个"待开始"阶段；**不要**重做阶段 P 或阶段 0。
- **完成一阶段后**：同步更新 `开发步骤拆解.md` 的状态列 + `README.md` 的"当前阶段" + 对应的 specs/plans 文档。

## 约定补充

- 后端计划的目录分层（见 `docs/技术文档/开发规范.md`）：`api/routes/` 管路由形状，`core/` 管配置和核心工具，`session|recording|review|action|execution/` 是业务模块，`browser/` 是浏览器桥接，`spikes/` **只放实验性脚本**不要污染正式代码。
- 前后端接口契约目前是**手写 TS 类型**（`frontend/src/services/*.ts`）对应后端 Pydantic 模型；还没引 OpenAPI 代码生成。新加接口要两端一起更新类型。
- `.webtoactions/` 里可能藏本地运行时状态（录制、后续的 SQLite），改动 `.gitignore` 或清理时注意别误删本地数据。
- Vite 代理把 `/api/*` 送到 `127.0.0.1:8000`；前端起在 `:5173`。没起后端时前端页面会在联调位置报错，这是**预期**，不要包装成"fallback"。
