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
