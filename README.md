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

下一步建议：

1. 进入 `docs/技术文档/开发步骤拆解.md` 中的 **阶段 5：ActionMacro 与执行 MVP**
2. 基于已完成的 `ReviewedMetadata` 版本结果生成 `ActionMacro`
3. 打通动作库、参数注入、执行中心与执行状态流的第三条业务闭环

## 本地开发

后端启动：

```bash
./scripts/dev/start_backend.sh
```

前端启动：

```bash
./scripts/dev/start_frontend.sh
```
