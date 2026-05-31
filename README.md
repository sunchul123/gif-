<div align="center">
  <img src="icon.png" width="80" alt="宠物图标">
  <h1 align="center">桌面宠物 · Desktop Pet</h1>
  <p align="center">
    <strong>将gif转换为简单桌宠的工具</strong>
    <br>
    Windows 平台 · 无边框透明 · AI 对话 · 多宠物系统
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.14-blue?logo=python">
    <img src="https://img.shields.io/badge/PySide6-6.11-green?logo=qt">
    <img src="https://img.shields.io/badge/license-MIT-orange">
  </p>
</div>

---
## 声明
- 本项目是一个将gif转换为简单桌宠的工具（ 其实只是一个 GIF 播放器:) ）
- 作者所有测试的宠物素材都是从网上偷的，不再上传，请自行下载（推荐配合EmoteLab使用）
- 本人只是一个非科班大一学生，项目完全由ai生成，只是想试一下Vibe Coding和GitHub，自用
---

## 📦 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
# 国内用户推荐使用清华镜像:
pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

### 启动

| 方式 | 命令 |
|------|------|
| 🚀 生产模式（无控制台） | 双击 `run.bat` |
| 🐛 调试模式 | 双击 `run_debug.bat` |
| ⚡ 桌面快捷方式 | 双击 `create_shortcut.vbs` |

---

## 🏗 项目架构

```
feibi/
├── main.py                  # 入口: QApplication + 高 DPI 缩放
├── pet_window.py            # 核心: 无边框透明窗口 + GIF 动画状态机
├── manager_window.py        # 管理器: 多标签设置对话框
├── chat_window.py           # 聊天: 气泡历史查看器 + JSON 持久化
├── widgets.py               # 工具: 待做任务、Claude 启动器
├── ui_theme.py              # 主题: 颜色、字体、QSS 样式系统
├── ollama_client.py         # AI: Ollama / OpenAI API 客户端
├── config_manager.py        # 配置: config.json 读写 + 宠物导入
│
├── pet/                     # 🐾 多宠物系统
│   ├── pet_manager.py       #     配置发现、切换、PetConfig
│   ├── current.json         #     当前宠物 ID
│   ├── feibi/               #     菲比 ─── pet.json + GIFs + icon.png
│   ├── 呆猫/                #     呆猫
│   └── 骑拉帝纳/            #     骑拉帝纳
│
├── run.bat                  # 生产模式启动脚本
├── run_debug.bat            # 调试模式启动脚本
├── run_hidden.ps1           # PowerShell 后台启动
├── create_shortcut.vbs      # 生成桌面快捷方式
├── requirements.txt         # 依赖: PySide6, requests
└── pet_debug.log            # 运行时日志
```

---

## 🎨 五层架构

| 层 | 文件 | 职责 |
|----|------|------|
| 🚪 **入口** | `main.py` | QApplication 初始化、高 DPI 缩放、全局 QSS |
| 🖼 **核心 GUI** | `pet_window.py` | QWidget 无边框透明窗口、QMovie GIF 动画、拖拽、音效、内嵌聊天、右键菜单 |
| ⚙️ **管理** | `manager_window.py` / `chat_window.py` | 多标签设置、气泡聊天记录、待做任务、CC 启动器 |
| 🎭 **主题** | `ui_theme.py` | 颜色调色板、字体、QSS 样式表、组件工厂函数 |
| 🧩 **数据** | `pet/pet_manager.py` / `config_manager.py` | 宠物发现与切换、JSON 配置持久化 |
| 🤖 **AI** | `ollama_client.py` | Ollama / OpenAI 兼容 API 客户端 |

---

## 🐾 宠物系统

### 目录约定

每个宠物是一个子目录，结构如下:

```
pet/宠物名/
├── pet.json         # 配置: name, prompt, gifs, custom_actions
├── idle.gif         # 待机动画
├── talk.gif         # 对话动画
├── thinking.gif     # 思考动画 (可选)
├── sleep_0.gif      # 入睡过渡
├── sleep_1.gif      # 睡眠循环
├── icon.png         # 管理器图标 (可选)
└── sounds/          # 音效目录 (可选)
```

### pet.json 示例

```json
{
  "name": "菲比",
  "prompt": "你是桌面宠物菲比。用简短活泼的语气回答。",
  "gifs": {
    "idle": "idle.gif",
    "talk": "talk.gif",
    "thinking": "thinking.gif",
    "sleep_start": "sleep_0.gif",
    "sleep_loop": "sleep_1.gif"
  },
  "custom_actions": {
    "跳舞": { "gif": "dance.gif", "loop": true }
  }
}
```

---

## 🔄 状态机

```
idle ──双击/菜单──→ talk ──发送消息──→ thinking ──收到回复──→ reply ──单击/回车──→ input
  │                                                                              │
  └──←──←──←──←──←──←──←──←──←──←──←──←──←──←──←──←──←──←──←──←──←──←──←───┘
  │
  └──22:00-08:00──→ sleep_start ──→ sleep_loop (循环)
```

---

## 💬 内嵌聊天

- **打开**: 双击宠物 / 右键 → "打开对话"
- **发送**: Enter 键（Shift+Enter 换行）
- **回复**: 收到后显示在输入框，单击或 Enter 回到输入模式
- **AI**: 本地 Ollama / 远程 OpenAI 兼容 API

---

## ⚙️ 管理器功能

| 标签页 | 功能 |
|--------|------|
| 素材导入 | 从文件夹导入 GIF，自动识别动作类型 |
| 动作配置 | 管理每个动作的 GIF 文件绑定 |
| 参数设置 | 缩放、不透明度、置顶、初始位置 |
| AI 设置 | 服务商、Base URL、模型、API Key |
| 宠物管理 | 浏览、切换、删除宠物 |

---

## 📋 待做任务

- 浮动在宠物上方的轻量任务看板
- 创建 / 完成 / 删除任务
- 自动持久化到 `todo_list.json`
- 任务超出自动伸长

---

## ⚡ Claude 集成

- 右键菜单一键启动 Claude 桌面端（自动检测 AppX 安装）
- 浮窗启动器

---

## 🎨 主题系统

`ui_theme.py` 统一管理:

- **颜色**: 亮灰色调色板（支持一键切换深色/浅色）
- **字体**: Segoe UI Variable Display + CJK 回退
- **QSS**: 预置 Button、Input、ComboBox、ScrollBar、Slider、Tab、CheckBox、Menu 样式
- **HiDPI**: 自动检测系统缩放，`PassThrough` 策略

---

## 📝 日志

所有运行日志输出到 `pet_debug.log`，调试时优先查看。

