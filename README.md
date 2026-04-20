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
- 阶段 2：领域模型与存储骨架
- 阶段 3：录制链路 MVP
- 阶段 4：元数据审核 MVP
- 阶段 5：`ActionMacro` 与执行 MVP
- 阶段 6：导入导出与运行模式
- 阶段 7：稳定性与收尾

当前收口结果：

- 已支持 `RECORDING` 单条链路资料包导出 / 导入，覆盖录制、审核结果、动作宏、执行记录与被引用证据文件
- 已支持单进程运行模式：后端挂载前端 `dist`，并提供 SPA fallback
- 已补失败路径测试、运行模式 smoke test、共享错误态 / 空态组件，以及人工冒烟清单

如继续迭代，下一步建议：

1. 进入真实浏览器站点的全自动 E2E 与 CI 集成
2. 继续推进 `BusinessAction` 抽象与更高层的业务编排
3. 补更完整的导入冲突处理策略与跨版本兼容策略

## 本地开发

以下命令默认在**仓库根目录**执行。

首次初始化可参考 `docs/本地启动说明.md` 中的“首次初始化”章节。

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
cd frontend && npm run test:run
cd frontend && npm run build
```

更多说明：

- 启动方式与端口覆盖说明见 `docs/本地启动说明.md`
- 手工走查步骤见 `docs/技术文档/手工冒烟清单.md`
- 阶段状态与验收口径见 `docs/技术文档/开发步骤拆解.md`
