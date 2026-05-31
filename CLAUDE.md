# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 运行命令

```bash
# 生产模式启动（无控制台窗口）
双击 run.bat                       # 或双击桌面快捷方式

# 调试模式启动（带控制台，可看输出）
双击 run_debug.bat

# 创建桌面快捷方式
PowerShell -ExecutionPolicy Bypass -File create_shortcut.ps1

# 日志输出在 pet_debug.log
```

依赖安装：`pip install PySide6>=6.5.0 requests>=2.28.0` 或 `pip install -r requirements.txt`（可用清华镜像：`pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple`）

## 架构概览

窗口桌面宠物，Python 3.14，PySide6 + Qt，Windows 平台。

### 五层结构

| 层 | 文件 | 职责 |
|---|---|---|
| 入口 | `main.py` | QApplication 初始化、高 DPI 缩放 |
| 核心 GUI | `pet_window.py` | QWidget 无边框透明窗口、QMovie GIF 动画状态机、拖拽、音效、内嵌聊天、右键菜单、宠物管理 |
| 设计主题 | `ui_theme.py` | 颜色、字体、QSS 样式表、统一组件工厂函数 |
| 宠物配置 | `pet/pet_manager.py` | `PetConfig` 数据类、`discover_pets()` 扫描、current.json 读写 |
| 聊天 | `chat_window.py` | `ChatHistory`（JSON 持久化、压缩归档、清空）、`HistoryViewer`（气泡风格） |
| AI | `ollama_client.py` | 封装本地 Ollama HTTP API，同步阻塞调用，`model="qwen2.5:7b"` |

### 目录结构

```
feibi/
├── main.py                  # 入口
├── pet_window.py            # 主窗口
├── chat_window.py           # 聊天记录
├── ollama_client.py         # LLM 客户端
├── assets/                  # 原始素材（旧方式，保留不动）
├── sounds/                  # 原始音效（旧方式，保留不动）
└── pet/                     # 多宠物形象系统
    ├── pet_manager.py       # 配置发现与切换
    ├── current.json         # {"pet_id": "feibi"}
    ├── feibi/               # 菲比 ─── pet.json + GIFs + icon.png + sounds/
    ├── 骑拉帝纳/            # 每个宠物目录名 = pet_id
    └── 呆猫/
```

### `pet/` 目录约定

每个宠物是一个子目录，要求：
- `pet.json` — `{"name": "中文名", "prompt": "LLM 系统提示词", "gifs": {"idle": "idle.gif", "talk": "talk.gif", "sleep_start": "sleep_0.gif", "sleep_loop": "sleep_1.gif"}}`
- 4 个 GIF 文件（文件名需与 pet.json 中 gifs 字段一致），1 个 `icon.png`（可选，管理界面用）
- `sounds/` 子目录（可选），放 `.mp3` 或 `.wav`
- `discover_pets()` 每次扫描 `pet/` 下所有有 pet.json 的子目录

### PetWindow 状态机

4 个动画状态：`idle → talk`（打开聊天时）、`idle → sleep_start → sleep_loop`（22:00-08:00 自动/右键手动触发）

`_switch_state(new_state)` 包含状态去重：`new_state == self.state` 时跳过（sleep_start 除外）。**切换宠物时必须在调用前设 `self.state = None`，否则 idle→idle 会被跳过导致动画不更新。**

### 内嵌聊天流程

```
双击/右键"打开对话" → _show_chat() → state=talk, 显示输入框
输入文字回车 → _send_chat() → 切 thinking → 后台线程调 Ollama
→ 回调 _on_reply() → 切 reply, 显示回复 → 单击或回车回到 input
```

### 图像渲染关键点

- `QMovie` 原生播放 GIF，无需手动帧提取，支持 `setScaledSize()` 直接缩放
- 窗口通过 `WA_TranslucentBackground` 实现逐像素透明，不再需要颜色键抠图
- `DISPLAY_SCALE = 0.4`（默认），所有 GIF 缩放到 40%
- `QImageReader` 预读 GIF 原始尺寸，然后 `QMovie.setScaledSize()` 按比例缩放
- 切换宠物后自动重设 movie 文件名并播放

### 音效播放

通过 PowerShell + `PresentationCore.MediaPlayer` 播放，`subprocess.Popen` 异步（daemon 线程）。路径用 `file:///` URI 传给 PowerShell。

### 关键数据文件

| 文件 | 格式 |
|---|---|
| `pet/current.json` | `{"pet_id": "feibi"}` — 跨会话记住当前宠物 |
| `chat_history.json` | `[{role, content, time}, ...]` |
| `chat_archive.txt` | 压缩时归档旧记录（`ChatHistory.compress(keep=100)`） |
| `pet_debug.log` | 所有 `log()` 调用输出到此，调试时首先查这个 |

### 常见的坑

- `pet.json` 的 `gifs` 为空 `{}` 会导致该宠物无任何动画，界面一片空白。`_ensure_working_pet()` 启动时检测到此情况会回退到第一个有 `idle` GIF 的宠物。切换时 `_switch_to_pet` 也会阻止切换到无 GIF 的宠物并弹警告。
- `QMenu` 右键菜单中 lambda 捕获循环变量必须用默认参数：`lambda checked, p=pid: ...`。
- 窗口使用 `FramelessWindowHint` + `WA_TranslucentBackground`，鼠标事件通过 `mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent` 重写实现拖拽。
- 安装依赖若遇网络超时，使用清华镜像：`pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple`
