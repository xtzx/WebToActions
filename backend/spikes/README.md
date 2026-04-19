# Browser Recording PoC

本目录只承载 `阶段 0` 的独立验证脚本，不依赖前端页面，也不把实验逻辑塞进正式后端模块。

当前 PoC 文件：

- `browser_recording_poc.py`：使用 `Playwright Python` 启动独立浏览器上下文，打开目标 URL，采集导航 / 请求 / 响应摘要，并把 cookie、`localStorage`、`sessionStorage` 摘要写入 JSON 文件。

## 浏览器启动策略

当前 PoC 支持三种模式：

- 默认模式：使用 `Playwright` 管理的 `Chromium`
- `--browser-channel chrome`：使用你本机已安装的 `Google Chrome`
- `--browser-path /path/to/browser`：使用自定义浏览器可执行文件

推荐顺序：

1. 默认使用 `Playwright` 管理的 `Chromium`，作为最稳定的验证基线
2. 需要贴近真实本机环境时，使用 `--browser-channel chrome`
3. 只有在确实找不到标准 channel 时，再使用 `--browser-path`

注意：

- 使用本机 `Chrome` 只表示“换浏览器程序”，**不等于自动复用你当前日常 Chrome 的用户资料和登录态**
- 当前 PoC 仍然默认创建新的隔离浏览器上下文 `browser.new_context()`

## 验证目标

这个 PoC 只覆盖当前 Spike 需要证明的最小链路：

- 使用 `browser.new_context()` 创建独立浏览器上下文；
- 打开指定 URL；
- 监听请求、响应和失败请求事件；
- 记录主框架导航轨迹；
- 读取 cookie / `localStorage` / `sessionStorage` 摘要；
- 将结果落盘到 `.webtoactions/spikes/recordings/`。

## 运行前准备

在仓库根目录执行：

```bash
python3 -m venv .venv
./.venv/bin/pip install -e "./backend[dev]"
./.venv/bin/playwright install chromium
```

如果你打算直接使用本机已安装的 `Chrome`，可以不先执行 `playwright install chromium`，改用 `--browser-channel chrome` 即可。

## 运行方式

### 1. 最小 headless 验证

```bash
./.venv/bin/python backend/spikes/browser_recording_poc.py "https://example.com"
```

### 2. 可视浏览器 + 手工触发最小动作闭环

```bash
./.venv/bin/python backend/spikes/browser_recording_poc.py \
  "https://example.com" \
  --headed \
  --hold-open-ms 15000
```

### 3. 使用本机已安装的 Chrome

```bash
./.venv/bin/python backend/spikes/browser_recording_poc.py \
  "https://example.com" \
  --browser-channel chrome \
  --headed
```

### 4. 使用自定义浏览器路径

```bash
./.venv/bin/python backend/spikes/browser_recording_poc.py \
  "https://example.com" \
  --browser-path "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headed
```

### 5. 常用可选参数

```bash
./.venv/bin/python backend/spikes/browser_recording_poc.py \
  "https://example.com" \
  --browser-channel chrome \
  --timeout-ms 45000 \
  --capture-wait-ms 5000 \
  --ignore-https-errors \
  --output-dir ".webtoactions/spikes/recordings"
```

- `--url`：位置参数的别名；
- `--headed`：显示浏览器窗口；
- `--browser-channel`：使用本机已安装浏览器 channel，例如 `chrome`
- `--browser-path`：使用自定义浏览器可执行文件路径；
- `--hold-open-ms`：在最终收口前额外保留页面，用于手工交互；
- `--capture-wait-ms`：页面加载后额外等待一段时间，让延迟请求收口；
- `--ignore-https-errors`：忽略自签名证书错误；
- `--output-dir`：覆盖默认输出目录。

## 输出内容概览

生成的 JSON 只保存摘要，不保存完整请求体、响应体或敏感值，主要包含：

- `browserContext`：浏览器引擎、是否 headless、隔离方式；
- `navigation`：初始导航响应、主框架导航事件、最终页面信息；
- `network`：请求数量、响应数量、失败数量、资源类型分布、状态码分组、每条请求的摘要；
- `sessionState.cookies`：cookie 数量、域名分布、属性摘要、value 字节数；
- `sessionState.localStorage`：`storage_state` 中各 origin 的 `localStorage` 摘要；
- `sessionState.sessionStorage`：最终页面 origin 的 `sessionStorage` 摘要；
- `sessionState.currentPage`：最终页面 URL、标题和当前页面存储快照。

## 当前边界

这个脚本是独立 PoC，不是正式录制器实现，因此明确不做：

- 不接入 `FastAPI` 或 `React`；
- 不保存完整请求体、响应体和二进制下载内容；
- 不做细粒度 `DOM` 事件轨迹；
- 不做动作建模、审核流或执行回放；
- 不保证覆盖跨 origin 的全部 `sessionStorage`，当前只读取最终页面 origin 的摘要。
