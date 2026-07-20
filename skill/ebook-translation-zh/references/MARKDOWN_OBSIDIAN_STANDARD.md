# Markdown 与 Obsidian 规范

- 与 HTML 使用同一翻译 JSON 和相同 block_id 顺序。
- UTF-8、可解析 YAML、正确标题层级和标准脚注。
- 段内页码注释不得制造空段或拆段。
- 图片位于完整段落之后，项目版使用可移植相对路径；Vault 版使用章节目录内 `assets/文件名`。
- 普通正文不得用星号或下划线产生斜体。
- 同步器只写配置的翻译目录，拒绝 `.obsidian` 和路径逃逸；同步后核对 Markdown 与资产哈希。
- Windows PowerShell 入口默认不传递中文 `-OutputName`；工具包在 Python 内根据章节 JSON 生成规范的 Unicode 中文文件名，避免原生参数编码损坏。
