#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def chrome_path() -> Path:
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Google Chrome is not installed")


def validate(html: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(chrome_path()))
        for width, height in ((1366, 768), (1920, 1080), (390, 844)):
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            console_errors: list[str] = []
            requests: list[str] = []
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("request", lambda request: requests.append(request.url))
            page.goto(html.resolve().as_uri(), wait_until="load")
            for image_index in range(page.locator("img").count()):
                image = page.locator("img").nth(image_index)
                image.scroll_into_view_if_needed()
                page.wait_for_function("element => element.complete && element.naturalWidth > 0", arg=image.element_handle())
            paged = page.evaluate("""() => ({
              width: document.documentElement.scrollWidth,
              viewport: innerWidth,
              images: [...document.images].map(i => ({complete:i.complete,naturalWidth:i.naturalWidth,right:i.getBoundingClientRect().right,left:i.getBoundingClientRect().left})),
              triggers: document.querySelectorAll('.footnote-trigger').length,
              templates: document.querySelectorAll('template[id^="footnote-template-"]').length,
              appendedNotes: document.querySelectorAll('ol.footnotes,.notes-page,section.footnotes').length
            })""")
            notes = []
            for index in range(7):
                trigger = page.locator(".footnote-trigger").nth(index)
                trigger.click()
                note = page.locator("#footnote-popover")
                box = note.bounding_box()
                notes.append({
                    "number": index + 1,
                    "visible": note.is_visible(),
                    "text_length": len(note.inner_text().strip()),
                    "expanded": trigger.get_attribute("aria-expanded"),
                    "hash": page.evaluate("location.hash"),
                    "within_viewport": bool(box and box["x"] >= -1 and box["y"] >= -1 and box["x"] + box["width"] <= width + 1 and box["y"] + min(box["height"], height) <= height + 1),
                })
                trigger.click()
                notes[-1]["second_click_closed"] = not note.is_visible()
            page.locator(".footnote-trigger").first.click()
            page.keyboard.press("Escape")
            escape_closed = not page.locator("#footnote-popover").is_visible()
            page.locator(".footnote-trigger").first.click()
            page.locator(".reader-toolbar strong").click()
            outside_closed = not page.locator("#footnote-popover").is_visible()
            page.locator("#reading-mode").click()
            continuous = page.evaluate("""() => ({
              active: document.body.classList.contains('continuous-mode'),
              width: document.documentElement.scrollWidth,
              viewport: innerWidth,
              pageMinHeight: getComputedStyle(document.querySelector('.page')).minHeight,
              imagesInside: [...document.images].every(i => { const r=i.getBoundingClientRect(); return r.left >= -1 && r.right <= innerWidth + 1; })
            })""")
            page.screenshot(path=str(output / f"viewport-{width}x{height}.png"), full_page=False)
            results.append({
                "viewport": f"{width}x{height}",
                "paged": paged,
                "notes": notes,
                "escape_closed": escape_closed,
                "outside_closed": outside_closed,
                "continuous": continuous,
                "console_errors": console_errors,
                "non_file_requests": [url for url in requests if not url.startswith("file:")],
            })
            context.close()
        browser.close()
    passed = all(
        item["paged"]["width"] <= item["paged"]["viewport"]
        and item["paged"]["triggers"] == 7
        and item["paged"]["templates"] == 7
        and item["paged"]["appendedNotes"] == 0
        and all(image["complete"] and image["naturalWidth"] > 0 and image["left"] >= -1 and image["right"] <= item["paged"]["viewport"] + 1 for image in item["paged"]["images"])
        and all(note["visible"] and note["text_length"] > 0 and note["expanded"] == "true" and note["hash"] == "" and note["within_viewport"] and note["second_click_closed"] for note in item["notes"])
        and item["escape_closed"] and item["outside_closed"]
        and item["continuous"]["active"] and item["continuous"]["width"] <= item["continuous"]["viewport"]
        and item["continuous"]["pageMinHeight"] == "0px" and item["continuous"]["imagesInside"]
        and not item["console_errors"] and not item["non_file_requests"]
        for item in results
    )
    report = {"status": "PASS" if passed else "FAIL", "html": str(html.resolve()), "results": results}
    (output / "browser-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.html, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 2)
