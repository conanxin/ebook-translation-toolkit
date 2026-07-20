# EPUB 渲染规范

本规范定义项目结构化章节 JSON 与 Markdown 派生内容在生成标准 EPUB 3 时必须满足的条件。所有 EPUB 输出由中央工具包统一实现，项目侧只允许通过 `.ebook-translation/project.yaml` 控制开关和元数据。

## 1. 包结构

EPUB 必须使用 ZIP 容器并满足下列最低要求：

- 第一个 ZIP 条目必须是 `mimetype`，且未压缩（`store`）。
- `mimetype` 内容严格为 `application/epub+zip`。
- `META-INF/container.xml` 必须指向 `EPUB/package.opf`。
- `EPUB/package.opf` 必须声明 EPUB 3 命名空间和元数据。
- `EPUB/nav.xhtml` 必须包含 `toc` / `page-list` / `landmarks` 三个 `<nav epub:type="...">`。
- `EPUB/toc.ncx` 至少包含 `<docTitle>` 和按阅读顺序排列的 `<navPoint>`。
- 正文 XHTML 必须位于 `EPUB/text/chapter-XX.xhtml`。
- 资源文件（图片、CSS）必须位于 `EPUB/images/` 和 `EPUB/styles/`。
- 不允许出现绝对路径、父目录穿越或 URL 形式条目。

## 2. 文档语义

- 章节 XHTML 必须以 `<!doctype html>` 形式声明 XHTML 命名空间并以 `xml:lang="zh-CN"`。
- 章节标题使用 `<h1>`，并明确包含中英文双语。
- 原书印刷页码锚点使用 `<span epub:type="pagebreak" role="doc-pagebreak" id="chXX-page-YY" data-pdf-page="N"></span>`。
- 正文段落保持 `<p>` 标签，原文跨页段落不能拆分。
- 注释引用使用 `<a epub:type="noteref" role="doc-noteref" id="chXX-fnref-NN" href="#chXX-fn-NN">N</a>`。
- 注释正文使用 `<aside epub:type="footnote" role="doc-footnote" id="chXX-fn-NN">`。
- 注释返回链接使用 `<a epub:type="backlink" role="doc-backlink" href="#chXX-fnref-NN">返回</a>`。

## 3. 排版规则

- 字体栈必须使用系统字体，不嵌入字体文件。
- 行距、缩进、字号均使用相对单位，不得设置固定页面尺寸。
- 中文版不使用视觉斜体，CSS 中所有 `em`/`i` 与 `font-style: italic` 强制归一化为 normal。
- 图注紧随图片，跨页段落保持单个 XHTML 段落。
- 长英文单词或 URL 必须使用 `overflow-wrap: anywhere` 或 `word-break` 允许换行。
- 不设置硬编码背景色与字体色；支持 `prefers-color-scheme`。
- 不在 EPUB 内部使用脚本或外部网络资源。

## 4. 图片

- 正文图片必须维持原始 MIME 类型，不重新压缩。
- 每张图片对应一个 `<img>` 标签，并附带可访问 `alt` 文本与 `<figcaption>` 图注。
- 同一图片在 EPUB 中只能出现一次。
- 封面图片标记 `properties="cover-image"`。

## 5. 元数据

- `dc:title`（中文主标题）。
- `dc:title id="original-title"` 标记英文原题，配合 `<meta refines="#original-title" property="title-type">original</meta>`。
- `dc:creator` 标记作者，配合 `role="aut"`。
- `dc:language` 必须为 `zh-CN`。
- `dc:identifier` 使用 `urn:uuid:<stable>`。
- `<meta property="dcterms:modified">` 使用 ISO8601 Z 格式。
- 不写入未经证实的出版社、ISBN、版权声明。

## 6. 注释编号

- 各章编号以原文为准，不能跨章累加。
- 每条注释最多一个 noteref 引用，并提供一条返回链接。

## 7. 确定性构建

- ZIP 条目时间戳固定为 `1980-01-01 00:00:00`。
- 书籍 UUID 持久保存在 `.ebook-translation/epub-identifier.txt`，重新构建不重新生成。
- 两次连续构建在内容不变的情况下 SHA-256 必须一致。

## 8. 校验

- 工具包内置校验器必须检查 mimetype、container.xml、OPF 元数据、spine、nav、NCX、所有 XHTML 的可解析性。
- 工具包内置校验器必须统计章节、图片、注释数量。
- 当本机存在外部 EPUBCheck / Calibre CLI 时，必须执行并将结果写入报告。
- 当外部工具不可用时，工具包内部校验仍可作为 PASS 依据，但需在报告中明确标注外部工具状态。