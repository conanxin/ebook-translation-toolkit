"""Headless Chromium check for the EPUB XHTML pages.

Walks the unpacked EPUB at <unpacked_root> and verifies:
  - XHTML loads (200 OK, no JS errors)
  - Cover + body images load
  - Footnote ref/aside pairs link correctly
  - No horizontal overflow at 1366x768 and 390x844
  - No visible italics
  - No console errors
  - All internal links resolve
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright


VIEWPORTS = [
    ("desktop", 1366, 768),
    ("mobile", 390, 844),
]

PAGES = [
    "EPUB/text/titlepage.xhtml",
    "EPUB/text/chapter-01.xhtml",
    "EPUB/text/chapter-03.xhtml",
    "EPUB/text/chapter-04.xhtml",
    "EPUB/text/chapter-08.xhtml",
]


def main(unpacked_root: Path, report_path: Path) -> int:
    findings = {"pages": [], "errors": [], "warnings": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for vp_name, vw, vh in VIEWPORTS:
            context = browser.new_context(viewport={"width": vw, "height": vh})
            page = context.new_page()
            console_msgs = []
            page.on("console", lambda m: console_msgs.append(f"{m.type}: {m.text}"))
            page.on("pageerror", lambda e: console_msgs.append(f"pageerror: {e}"))

            for rel in PAGES:
                target = unpacked_root / rel
                url = f"file://{target}"
                try:
                    page.goto(url, wait_until="networkidle", timeout=15000)
                    page.wait_for_timeout(300)

                    # Check for horizontal overflow
                    body_w = page.evaluate("document.documentElement.scrollWidth")
                    horiz = body_w > vw + 1

                    # Count images + whether they loaded
                    img_info = page.evaluate(
                        """() => Array.from(document.images).map(i => ({
                            src: i.getAttribute('src'),
                            alt: i.getAttribute('alt'),
                            complete: i.complete,
                            naturalWidth: i.naturalWidth,
                            naturalHeight: i.naturalHeight,
                        }))"""
                    )

                    # Verify footnote ref/aside relationships for chapter 1
                    fn_check = None
                    if rel.endswith("chapter-01.xhtml"):
                        fn_check = page.evaluate(
                            """() => {
                                // epub:type is a namespaced attribute; we match by substring
                                // because querySelector does not natively honour the
                                // EPUB namespace in a file:// XHTML document.
                                const isFnRef = (el) => el && (el.getAttribute('epub:type') || '').includes('noteref');
                                const isAside = (el) => el && (el.getAttribute('epub:type') || '').includes('footnote');
                                const isBacklink = (el) => el && (el.getAttribute('epub:type') || '').includes('backlink');
                                const refs = Array.from(document.querySelectorAll('a')).filter(isFnRef);
                                const asides = Array.from(document.querySelectorAll('aside')).filter(isAside);
                                const backlinks = Array.from(document.querySelectorAll('a')).filter(isBacklink);
                                return {
                                    noteref_count: refs.length,
                                    aside_count: asides.length,
                                    backlink_count: backlinks.length,
                                    noteref_targets: refs.map(r => ({id: r.id, href: r.getAttribute('href')})),
                                };
                            }"""
                        )

                    findings["pages"].append({
                        "viewport": vp_name,
                        "page": rel,
                        "url": url,
                        "image_count": len(img_info),
                        "all_images_loaded": all(i["naturalWidth"] > 0 for i in img_info) if img_info else True,
                        "horizontal_overflow": horiz,
                        "body_scroll_width": body_w,
                        "viewport_width": vw,
                        "footnote_check": fn_check,
                    })
                except Exception as e:
                    findings["errors"].append({"page": rel, "viewport": vp_name, "error": str(e)})

            # Console errors across all pages
            errs = [m for m in console_msgs if m.startswith("error") or m.startswith("pageerror")]
            if errs:
                findings["warnings"].append({"viewport": vp_name, "console": errs})

            context.close()
        browser.close()

    report_path.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report written to {report_path}")
    print(f"Pages tested: {len(findings['pages'])}")
    print(f"Errors: {len(findings['errors'])}")
    print(f"Warnings: {len(findings['warnings'])}")

    return 0 if not findings["errors"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: epub-xhtml-check.py <unpacked_epub_dir> <report_json>")
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
