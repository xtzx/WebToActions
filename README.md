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
