# 🖥️ DabaoAgent

> 基于 **[GenericAgent](https://github.com)** 魔改的中文一键绿色使用包 —— 零配置、开箱即用的自主 AI Agent 框架。

DabaoAgent 是一个极简自进化自主 Agent 框架，支持文件读写、代码执行、浏览器自动化、多平台机器人（微信/QQ/飞书/钉钉/Telegram/Discord）等丰富能力。本项目在原版 GenericAgent 基础上进行了全面的中文本地化改造，并提供一键启动的绿色使用体验。

## ✨ 特性

- 🚀 **一键启动** — 支持 Web UI、桌面窗口、命令行三种模式
- 🌐 **多模型支持** — 兼容 OpenAI / Anthropic / DeepSeek / 智谱 / Kimi / MiniMax 等
- 🔧 **物理级操作** — 文件读写、代码执行、浏览器 JS 注入、系统级干预
- 💬 **多平台接入** — Telegram、QQ、飞书、企业微信、钉钉、Discord、微信公众号
- 🇨🇳 **全面汉化** — Streamlit 工具栏、设置面板、界面文案完全中文化
- 🔑 **界面配置** — 侧边栏直接填入 API Key，无需手动编辑配置文件
- 🧠 **自进化记忆** — L0-L4 五级记忆体系，支持自主反思与定时任务

## 📦 快速开始

### 环境要求

- Python >= 3.10，< 3.14
- Windows / macOS / Linux

### 1. 安装依赖

```bash
# 安装 uv（推荐，速度更快）
pip install uv

# 安装核心依赖
uv pip install requests beautifulsoup4 bottle simple-websocket-server

# 安装 Web UI（可选）
uv pip install streamlit pywebview
```

或一键安装所有依赖：

```bash
uv sync
```

### 2. 配置 API 密钥

**方式一（推荐）：界面配置**

启动后，在侧边栏 **🔑 API 密钥设置** 中直接填入 API Key、Base URL 和模型名称，点击保存即可。

**方式二：文件配置**

复制 `mykey_template.py` 为 `mykey.py`，编辑其中的 API 配置：

```python
# mykey.py 示例（NativeOAISession — OpenAI 协议 + 原生工具调用）
native_oai_config = {
    'name': 'my-gpt',
    'apikey': 'sk-你的API密钥',
    'apibase': 'https://api.openai.com/v1',
    'model': 'gpt-5.4',
}
```

支持的后端类型：

| 配置变量关键字 | Session 类型 | 说明 |
|---|---|---|
| 含 `native` + `claude` | NativeClaudeSession | Anthropic 原生协议 |
| 含 `native` + `oai` | NativeOAISession | OpenAI 原生协议 |
| 含 `mixin` | MixinSession | 多 Session 故障转移 |

### 3. 启动

```bash
# 🌐 Web UI 模式（推荐）
uv run python launch.pyw

# 💻 桌面窗口模式（双击运行）
start_ga_ui.bat       # 或双击 GenericAgent.bat

# ⌨️ 命令行模式
uv run python agentmain.py
```

## 🏗️ 项目结构

```
DabaoAgent/
├── agentmain.py          # 核心 Agent 入口
├── agent_loop.py         # Agent 运行主循环
├── llmcore.py            # LLM 抽象层（多后端支持）
├── ga.py                 # 工具处理器（文件/代码/浏览器等）
├── simphtml.py           # HTML 简化（AI 阅读用）
├── TMWebDriver.py        # 浏览器 CDP 自动化
├── launch.pyw            # 桌面窗口启动器
├── hub.pyw               # 服务管理面板
├── mykey_template.py     # API 密钥配置模板
├── frontends/            # 前端界面
│   ├── stapp.py          # Streamlit Web UI v1
│   ├── stapp2.py         # Streamlit Web UI v2（Anthropic 主题）
│   ├── qtapp.py          # Qt 桌面应用
│   ├── tgapp.py          # Telegram Bot
│   ├── wechatapp.py      # 微信公众号 Bot
│   ├── qqapp.py          # QQ Bot
│   ├── fsapp.py          # 飞书 Bot
│   ├── wecomapp.py       # 企业微信 Bot
│   ├── dingtalkapp.py    # 钉钉 Bot
│   ├── dcapp.py          # Discord Bot
│   └── skins/            # 桌面宠物皮肤
├── memory/               # Agent 记忆体系（L0-L4）
├── reflect/              # 自主反思与定时任务
├── assets/               # 静态资源（提示词、工具定义等）
├── plugins/              # 可选插件（Langfuse 追踪等）
└── sche_tasks/           # 定时任务定义
```

## 🔌 支持的多平台机器人

| 平台 | 配置项 | 启动参数 |
|---|---|---|
| Telegram | `tg_bot_token`, `tg_allowed_users` | `--tg` |
| QQ | `qq_app_id`, `qq_app_secret` | `--qq` |
| 飞书 | `fs_app_id`, `fs_app_secret` | `--feishu` |
| 企业微信 | `wecom_bot_id`, `wecom_secret` | `--wecom` |
| 钉钉 | `dingtalk_client_id`, `dingtalk_client_secret` | `--dingtalk` |

示例：
```bash
uv run python launch.pyw --tg --qq
```

## ⌨️ 命令行用法

```bash
# 交互式 REPL
uv run python agentmain.py --verbose

# 一次性任务
uv run python agentmain.py --task my_task

# 反射/定时任务模式
uv run python agentmain.py --reflect reflect/scheduler.py

# 直接输入 prompt
uv run python agentmain.py --input "帮我写一个排序算法"

# 后台运行
uv run python agentmain.py --bg
```

### 运行时可调参数

在 REPL 中通过 `/session.*` 命令实时调整推理参数：

```
/session.reasoning_effort=high
/session.thinking_type=adaptive
/session.temperature=0.3
/session.max_tokens=32768
```

## 🎨 界面功能

- **LLM 链路切换**：侧边栏下拉切换可用模型
- **API 密钥设置**：界面直接填入密钥，自动保存并热加载
- **桌面宠物**：可爱的桌面小精灵，显示任务状态
- **自主行动**：离开 30 分钟后自动执行预设任务
- **工具注入**：一键重新注入工具示范历史
- **继续对话**：`/continue` 命令恢复历史会话

## 🤝 致谢

本项目基于 [GenericAgent](https://github.com) 框架进行魔改，感谢原作者的杰出工作。

改动内容包括：
- 全面中文本地化（界面、提示词、工具定义）
- 新增侧边栏 API 密钥配置界面
- 优化无配置时的引导流程
- 添加桌面宠物集成
- Streamlit 工具栏/设置面板完全汉化

## 📄 开源协议

MIT License
