# CLAUDE.md

本文件用于约束 Claude Code 在 `music-toolkit` 仓库内的默认工作方式，减少无关上下文和 token 消耗。

## 工作范围

- 默认只把当前仓库视为工作范围，不要扫描父目录、家目录或其他项目。
- 如需联动飞书能力，若同级目录 `../feishu-toolkit` 存在则优先使用；不存在时不要全盘搜索，应先询问用户或使用 `FEISHU_TOOLKIT_PATH`。
- 除非用户明确要求，否则不要读取或分析以下目录：
  - `downloads/`
  - `.git/`
  - `.pytest_cache/`
  - `__pycache__/`
  - `.venv/`
- 除非用户明确要求排查配置或环境变量，否则不要读取：
  - `.env`
  - `.env.*`

## 优先读取顺序

当需要理解项目时，优先按以下顺序获取上下文：

1. `README.md`
2. `music_toolkit.py`
3. `tests/`
4. `skill/SKILL.md`（仅当任务涉及 CLI 用法、AI 集成、领域能力或跨仓联动时再读）

除非任务需要，不要做大范围全仓搜索。
- 若任务与配置相关，优先看 `.env.example` 和 `README.md` 中的环境变量说明。

## 命令与路径约定

- 运行命令时，默认假设当前目录就是 `music-toolkit` 根目录。
- 示例命令优先使用相对形式，例如：
  - `python3 music_toolkit.py search "晴天"`
  - `python3 music_toolkit.py download-playlist 9582035807 qq`
- 不要默认使用 `~/music-toolkit/...` 这类旧绝对路径写法。

## 修改原则

- 优先做最小改动，避免顺手重构无关代码。
- 修改文档或示例时，保持与当前工作区结构兼容。
- 若任务只涉及某个命令或函数，优先读取相关片段，不要把整个仓库重新读一遍。
