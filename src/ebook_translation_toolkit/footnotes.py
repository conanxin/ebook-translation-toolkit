from __future__ import annotations

from html import escape

from .models import Footnote, FootnoteRef
from .utils import consecutive


def validate_footnotes(footnotes: list[Footnote], references: list[FootnoteRef]) -> list[str]:
    errors: list[str] = []
    numbers = [item.number for item in footnotes]
    reference_numbers = [item.number for item in references]
    if not consecutive(numbers):
        errors.append("footnote definitions are not consecutive from 1")
    if sorted(reference_numbers) != numbers:
        errors.append("footnote references and definitions do not match one-to-one")
    return errors


def html_trigger(number: int) -> str:
    return (
        f'<sup class="footnote-ref"><button type="button" class="footnote-trigger" '
        f'data-footnote="{number}" aria-expanded="false" '
        f'aria-controls="footnote-popover" aria-label="查看注释 {number}">{number}</button></sup>'
    )


def html_template(note: Footnote) -> str:
    text = escape(note.translated_text or note.source_text)
    return f'<template id="footnote-template-{note.number}"><p>{text}</p></template>'
