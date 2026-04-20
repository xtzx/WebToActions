# WebToActions Backend

该目录承载 `WebToActions` 的正式后端工程，当前已完成到阶段 7 的导入导出、运行模式与稳定性收口。

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
- `ActionMacro` 生成、执行入口、执行日志与执行状态 `SSE`
- `RECORDING` 单条链路资料包导出 / 导入
- 运行模式下前端静态资源挂载与 SPA fallback
- 失败路径测试与运行模式 smoke test
- 阶段 7 健康契约（`phase=stage7`）

说明：以下命令默认在**仓库根目录**执行；如果当前就在 `backend/` 目录，请先 `cd ..` 回到仓库根目录。

开发模式（前后端分离）：

```bash
./scripts/dev/start_backend.sh
```

运行模式（单进程）：

```bash
./scripts/run/start_local_app.sh
```

若 `8000` 端口被占用，可覆盖端口：

```bash
APP_PORT=8010 ./scripts/run/start_local_app.sh
```

后端测试：

```bash
cd backend && ../.venv/bin/python -m pytest tests -v
```

建议重点关注：

- `tests/importexport/test_importexport_flow.py`
- `tests/failure/test_failure_paths.py`
- `tests/smoke/test_smoke.py`
