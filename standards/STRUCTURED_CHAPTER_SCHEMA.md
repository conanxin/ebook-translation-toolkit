# 结构化章节唯一事实来源

每章至少有 `chapter-XX-source.json` 与 `chapter-XX-zh.json`。顶层包含 `book`、`chapter`、`blocks`、`images`、`footnotes`、`terms`、`page_anchors`。

正文段落使用稳定 `p-001` ID；跨页仍是一个 block。block 同时保存英文、中文、PDF/印刷页码范围、段内页码锚点、段后图片、注释引用、样式语义和阅读顺序。图片以 `after_block_id` 与完整段落绑定。注释引用保存编号及字符偏移。HTML 和 Markdown 都只能从翻译 JSON 渲染，禁止另存独立正文副本。

多章节项目中，第二章以后统一写入 `intermediate/chapters/chapter-XX-source.json` 与 `chapter-XX-zh.json`；第一章旧路径可以为兼容既有已验证项目而保留。译文中的 `[[PAGE:pdf|printed]]` 与 `[[FN:n]]` 是结构化渲染标记：必须分别与 block 的 `page_anchors` 和 `footnote_refs` 一一对应，渲染时转换为 HTML 段内锚点／注释按钮或 Markdown 页码注释／标准脚注，不得泄漏到成品。

全书续跑状态保存在 `reports/BOOK_TRANSLATION_PROGRESS.json`。已达到 `OBSIDIAN_SYNCED` 且 QA 为 `PASS` 的章节是冻结完成态，恢复执行时必须跳过。
