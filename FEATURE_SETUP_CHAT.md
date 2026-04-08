# 新功能：交互式飞书群聊配置 (setup-chat)

## 功能概述

添加了 `setup-chat` 命令，让用户可以交互式选择飞书群聊，无需手动记忆和输入 Chat ID。

## 用户痛点

**之前的方式**：
```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
export FEISHU_DEFAULT_CHAT_ID="oc_xxx"  # 用户需要手动获取这个 ID
```

用户需要：
1. 打开飞书客户端
2. 找到群聊设置
3. 复制 Chat ID（长字符串，容易出错）
4. 手动设置环境变量

**现在的方式**：
```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"

python3 music_toolkit.py setup-chat
# 自动列出所有群聊，用户输入序号即可
```

## 功能特性

### 1. 自动获取群聊列表

使用 `feishu-toolkit` 的 `list_chats()` API，自动获取机器人已加入的所有群聊。

### 2. 友好的交互界面

```
🔍 正在获取群聊列表...

📋 找到 5 个群聊:

序号   群聊名称                                  Chat ID
────────────────────────────────────────────────────────────────────────────
1      音乐分享群                                oc_abc123...
2      测试群                                    oc_def456...
3      工作群                                    oc_ghi789...
4      家庭群                                    oc_jkl012...
5      朋友群                                    oc_mno345...

────────────────────────────────────────────────────────────────────────────

请选择群聊序号 (1-5, 或按 Ctrl+C 取消): 1

✅ 已选择: 音乐分享群
   Chat ID: oc_abc123...

💾 配置已保存到: ~/.config/music-toolkit/config.json

📝 请将以下内容添加到你的 shell 配置文件 (~/.bashrc 或 ~/.zshrc):
   export FEISHU_DEFAULT_CHAT_ID="oc_abc123..."

✨ 配置完成！现在可以使用飞书推送功能了。
```

### 3. 配置持久化

- 保存到 `~/.config/music-toolkit/config.json`
- 包含 `feishu_default_chat_id` 和 `feishu_default_chat_name`
- 提示用户将 Chat ID 添加到环境变量

### 4. 仅列出模式

```bash
python3 music_toolkit.py setup-chat --list-only
```

仅显示群聊列表，不保存配置。适合查看所有可用群聊。

### 5. 更换群聊

```bash
# 重新运行 setup-chat 即可选择新的群聊
python3 music_toolkit.py setup-chat
```

## 技术实现

### 1. CLI 参数定义

```python
# ── setup-chat ────────────────────────────────────────────────────────
p = sub.add_parser("setup-chat", help="交互式选择飞书群聊 (自动保存配置)")
p.add_argument("--list-only", action="store_true", help="仅列出群聊，不保存配置")
```

### 2. 核心函数

```python
def _setup_chat_interactive(list_only: bool = False) -> None:
    """
    交互式选择飞书群聊并保存配置。

    流程：
    1. 检查 FEISHU_APP_ID 和 FEISHU_APP_SECRET 环境变量
    2. 动态导入 feishu-toolkit
    3. 调用 FeishuClient.list_chats() 获取群聊列表
    4. 显示群聊列表
    5. 用户输入序号选择
    6. 保存配置到 ~/.config/music-toolkit/config.json
    7. 提示用户设置环境变量
    """
```

### 3. 错误处理

- **缺少环境变量**：提示用户设置 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`
- **feishu-toolkit 未安装**：提示用户克隆仓库
- **API 调用失败**：显示错误信息
- **未找到群聊**：提示用户检查应用权限和机器人是否已加入群聊
- **用户取消**：Ctrl+C 优雅退出

### 4. 依赖关系

```
music_toolkit.py
    │
    ├── setup-chat 命令
    │   └── _setup_chat_interactive()
    │       └── feishu-toolkit/feishu_toolkit.py
    │           └── FeishuClient.list_chats()
    │               └── GET /im/v1/chats
```

## 文档更新

### 1. Quick Start 章节

添加了"飞书群聊配置（推荐方式）"小节，详细说明 `setup-chat` 的使用方法。

### 2. 飞书推送集成章节

添加了"配置步骤（推荐方式）"，将 `setup-chat` 作为推荐的配置方式。

### 3. API 参考章节

在"飞书推送命令"中添加了 `setup-chat` 命令。

### 4. 常见场景速查表

在表格顶部添加了"配置飞书群聊"场景。

### 5. 环境变量说明

添加了推荐使用 `setup-chat` 配置的提示。

## 使用示例

### 场景 1: 首次配置

```bash
# 1. 设置飞书应用凭证
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"

# 2. 运行交互式配置
python3 music_toolkit.py setup-chat

# 3. 选择群聊（输入序号）
# 请选择群聊序号 (1-5, 或按 Ctrl+C 取消): 1

# 4. 将 Chat ID 添加到环境变量
echo 'export FEISHU_DEFAULT_CHAT_ID="oc_abc123..."' >> ~/.zshrc
source ~/.zshrc

# 5. 测试推送
python3 music_toolkit.py download-send 0039MnYb0qxYhV qq \
  --name "晴天" --artist "周杰伦"
```

### 场景 2: 查看所有群聊

```bash
python3 music_toolkit.py setup-chat --list-only
```

### 场景 3: 更换接收消息的群聊

```bash
# 重新运行 setup-chat
python3 music_toolkit.py setup-chat

# 选择新的群聊
# 请选择群聊序号 (1-5, 或按 Ctrl+C 取消): 3

# 更新环境变量
export FEISHU_DEFAULT_CHAT_ID="oc_new_chat_id..."
```

### 场景 4: OpenClaw 使用

当用户说"我想配置飞书推送"或"我不知道 Chat ID"时，OpenClaw 应该：

1. 引导用户设置 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`
2. 运行 `python3 music_toolkit.py setup-chat`
3. 提示用户选择群聊序号
4. 提示用户将 Chat ID 添加到环境变量

## 优势

### 1. 用户体验

- **无需手动查找 Chat ID**：自动列出所有可用群聊
- **可视化选择**：看到群聊名称，不会选错
- **一次配置，永久使用**：保存到配置文件和环境变量

### 2. 减少错误

- **避免复制粘贴错误**：不需要手动复制长字符串
- **验证群聊可用性**：只显示机器人已加入的群聊
- **友好的错误提示**：清晰的错误信息和解决方案

### 3. AI 友好

- **符合用户习惯**：用户只需提供 App ID 和 Secret
- **交互式引导**：OpenClaw 可以逐步引导用户完成配置
- **可重复执行**：更换群聊时重新运行即可

## 兼容性

- **向后兼容**：仍然支持直接设置 `FEISHU_DEFAULT_CHAT_ID` 环境变量
- **可选功能**：不使用飞书推送的用户不受影响
- **跨平台**：支持 macOS、Linux、Windows

## 测试建议

```bash
# 1. 测试正常流程
python3 music_toolkit.py setup-chat

# 2. 测试仅列出模式
python3 music_toolkit.py setup-chat --list-only

# 3. 测试缺少环境变量
unset FEISHU_APP_ID
python3 music_toolkit.py setup-chat
# 应该提示设置环境变量

# 4. 测试 feishu-toolkit 未安装
mv ../feishu-toolkit ../feishu-toolkit.bak
python3 music_toolkit.py setup-chat
# 应该提示克隆仓库
mv ../feishu-toolkit.bak ../feishu-toolkit

# 5. 测试配置文件保存
python3 music_toolkit.py setup-chat
cat ~/.config/music-toolkit/config.json
# 应该包含 feishu_default_chat_id 和 feishu_default_chat_name

# 6. 测试推送功能
python3 music_toolkit.py download-send 0039MnYb0qxYhV qq \
  --name "晴天" --artist "周杰伦"
# 应该成功发送到配置的群聊
```

## 未来改进

1. **自动检测配置**：如果已有配置，显示当前选择的群聊
2. **多群聊支持**：保存多个群聊配置，支持快速切换
3. **群聊搜索**：当群聊数量很多时，支持按名称搜索
4. **配置验证**：测试 Chat ID 是否有效（发送测试消息）
5. **GUI 界面**：提供图形界面选择群聊（可选）

## 总结

`setup-chat` 命令大大简化了飞书推送的配置流程，让用户无需手动查找和记忆 Chat ID。这个功能特别适合：

- 首次使用 music-toolkit 的用户
- 需要更换接收消息群聊的用户
- 使用 AI 助手（如 OpenClaw）配置工具的用户

通过交互式界面和清晰的提示，用户可以在几秒钟内完成配置，立即开始使用飞书推送功能。
