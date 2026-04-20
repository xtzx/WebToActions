# WebToActions

`WebToActions` 是一个“浏览器执行优先、网络证据驱动、支持人工审核和动作抽象”的本地自动化工具。它的首版目标不是直接生成一个黑盒 RPA，而是先把“录制 -> 审核 -> 动作生成 -> 执行 -> 导入导出”的主闭环稳定落地。

## 当前已完成态

当前主线已经收口为**首版交付基线**，对应 `docs/技术文档/开发步骤拆解.md` 中的 `阶段 P - 阶段 7` 全部完成。

- 已完成产品与技术文档基线，包括需求文档、技术方案设计、开发步骤拆解与首版实现计划
- 已完成正式工程骨架、领域模型与本地存储骨架
- 已完成录制、审核、`ActionMacro` 生成与执行的主闭环
- 已完成 `RECORDING` 单条链路资料包导入导出
- 已完成开发模式与单进程运行模式
- 已完成失败路径测试、运行模式 smoke test、共享错误态/空态组件与人工冒烟清单

当前主线已通过：

- 后端全量测试：`pytest tests`
- 前端全量测试：`npm test`
- 前端构建：`npm run build`
- 单进程运行模式健康检查与 SPA fallback 验证

## 当前产品能力

- 会话管理：创建隔离浏览器会话、维护 `profile` 目录，并区分 `available / relogin_required / expired` 等状态
- 录制中心：启动录制、停止录制、查看录制详情，采集页面阶段、请求/响应索引、会话状态快照和文件传输摘要
- 审核中心：基于录制结果生成 `MetadataDraft`，支持人工审核、关键请求标注、噪音请求标注与审核版本保存
- 动作库与执行中心：从审核结果生成 `ActionMacro`，支持参数化执行、执行日志查看、失败定位与执行状态流
- 导入导出：支持导出/导入 `RECORDING` 资料包，覆盖录制聚合、审核结果、动作宏、执行记录和被引用证据文件
- 本地运行：支持前后端分离开发模式，以及后端挂载前端 `dist` 的单进程运行模式

## 交付清单

- 产品交付：首版交互闭环、管理台页面、受控浏览器录制与浏览器重放执行能力
- 工程交付：`FastAPI` 后端、`React` 管理台、`SQLite + Alembic`、文件对象区、启动脚本
- 文档交付：`README.md`、启动说明、手工冒烟清单、技术方案、开发规范、阶段拆解与产品文档
- 质量交付：后端全量测试、前端测试、构建验证、失败路径测试与运行模式 smoke test

## 怎么使用

典型业务使用路径如下：

1. 在“会话管理”创建一个新的浏览器会话
2. 在“录制中心”发起录制，完成真实页面操作后停止录制
3. 在“审核中心”查看自动分析结果并保存审核版本
4. 生成 `ActionMacro`，进入动作详情页查看步骤、参数和会话要求
5. 选择一个 `available` 会话执行动作，并在“执行中心”查看日志和结果
6. 如需迁移链路，可在“导入导出”页面导出或导入 `RECORDING` 资料包

如果只是本地启动使用当前产品：

```bash
./scripts/run/start_local_app.sh
```

如果 `8000` 端口被占用，可覆盖端口：

```bash
APP_PORT=18000 ./scripts/run/start_local_app.sh
```

## 架构设计

当前首版采用“管理台 + 本地服务 + 受控浏览器 + 本地存储”的架构：

- 前端管理台：`React + TypeScript + React Router`，按 `pages / features / services / types` 分层
- 本地服务：`FastAPI` 提供 `session / recording / review / action / execution / importexport / health` 等 API
- 应用层：按用例拆分为 `session / recording / review / action / execution / importexport` 模块，负责流程编排
- 浏览器桥接层：通过 `Playwright Python` 管理隔离浏览器上下文、录制采集和浏览器重放
- 存储层：`SQLite + Alembic` 保存元数据，`.webtoactions/` 文件对象区保存请求体、响应体、快照、日志等大对象
- 实时状态：录制、审核、执行等长任务状态统一使用 `SSE`

## 技术细节与当前边界

当前主线的技术路线：

- 后端：`Python 3.11+`、`FastAPI`、`Pydantic v2`、`SQLAlchemy 2`、`Alembic`
- 前端：`React`、`TypeScript`、`Vite`、`React Router`、`Vitest`
- 浏览器控制：`Playwright Python`
- 本地存储：`SQLite + 文件对象区`
- 运行模式：开发期前后端分离，运行期单进程挂载前端静态资源

当前边界也已明确：

- 仅支持 `RECORDING` 单条链路资料包，不支持更高层 `BusinessAction` 资料包
- 导入资料包时不迁移活跃登录态；导入后的会话只保留历史上下文，状态会标记为 `relogin_required`
- 首版以本地单机闭环为目标，不包含真实站点全自动 E2E、CI 集成和多人协作能力

## 文档入口

- 产品文档：[docs/产品文档/文档索引.md](docs/产品文档/文档索引.md)
- 技术文档：[docs/技术文档/文档索引.md](docs/技术文档/文档索引.md)
- 开发进度看板：[docs/技术文档/开发步骤拆解.md](docs/技术文档/开发步骤拆解.md)
- 本地启动说明：[docs/本地启动说明.md](docs/本地启动说明.md)
- 手工冒烟清单：[docs/技术文档/手工冒烟清单.md](docs/技术文档/手工冒烟清单.md)

## 本地开发

以下命令默认在**仓库根目录**执行。

首次初始化可参考 `docs/本地启动说明.md` 中的“首次初始化”章节。当前主线的最小本地环境基线为：

- `Python 3.11+`
- 根目录 `.venv`
- `frontend/` 已执行 `npm ci`

开发模式（前后端分离）：

```bash
./scripts/dev/start_backend.sh
./scripts/dev/start_frontend.sh
```

运行模式（单进程，本地一体化入口）：

```bash
./scripts/run/start_local_app.sh
```

常用验证命令：

```bash
cd backend && ../.venv/bin/python -m pytest tests -v
cd frontend && npm test
cd frontend && npm run build
```

## 后续迭代方向

当前阶段计划已经完成；如果继续迭代，建议优先从以下方向中选择：

1. 进入真实浏览器站点的全自动 E2E 与 CI 集成
2. 继续推进 `BusinessAction` 抽象与更高层的业务编排
3. 补更完整的导入冲突处理策略与跨版本兼容策略
