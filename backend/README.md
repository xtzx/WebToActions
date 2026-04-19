# WebToActions Backend

该目录承载 `WebToActions` 的正式后端工程，以及已完成到阶段 4 的元数据审核能力。

当前阶段已完成：

- `FastAPI` 正式应用入口
- 统一配置读取模块
- 稳定的 `/api/health` 契约
- `session / recording / review / action / execution / importexport / browser / infrastructure` 模块边界
- 领域模型、状态机与版本链不变量
- `SQLite + Alembic` 元数据索引基线
- `.webtoactions/` 文件对象区 bootstrap
- 最小 `Recording` 聚合仓储与应用启动初始化
- 浏览器会话管理与隔离 `Profile` 目录
- 开始录制 / 结束录制 / 录制详情 API
- 请求响应、页面阶段、会话状态、文件传输摘要采集
- 录制状态 `SSE` 推送
- `MetadataDraft` 确定性分析、审核上下文 API 与审核状态 `SSE`
- `ReviewedMetadata` 版本保存与噪音请求标注
- 阶段 4 健康契约（`phase=stage4`）

本地开发启动：

```bash
../scripts/dev/start_backend.sh
```

后端测试：

```bash
../.venv/bin/python -m pytest tests -v
```
